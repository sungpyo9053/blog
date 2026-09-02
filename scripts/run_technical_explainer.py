#!/usr/bin/env python3
"""Publish one search-backed, example-led Hunt News technical explainer."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1]
if str(BOOTSTRAP_ROOT) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_ROOT))

from publisher.config import load_env_file
from scripts.daily_briefing import DailyBriefingError, load_daily_briefing
from scripts.run_daily_pipeline import (
    ANALYTICS_REPORT,
    CONTENT_TYPE_GUIDES,
    LOG_DIR,
    PROJECT_ROOT,
    RUNS_DIR,
    ContentQualityRejection,
    PipelineError,
    PipelineLock,
    Stage,
    has_successful_publish,
    make_topic_context,
    read_publish_result,
    resolve_codex,
    run_stage,
    run_topic_pipeline,
)
from scripts.search_signal_providers import (
    DEFAULT_GOOGLE_TRENDS_CACHE,
    SearchSignalError,
    load_google_trends_cache,
)

KST = timezone(timedelta(hours=9))
INPUT_VERSION = "technical-explainer-input.v1"
PLAN_VERSION = "technical-explainer-plan.v1"
EXPLAINER_CATEGORY = "기술 해설"
EXPLAINER_CATEGORY_SLUG = "technical-explainer"
LOCK_FILE = LOG_DIR / "technical-explainer.lock"
LOOKBACK_DAYS = 7
MIN_DAILY_BRIEFINGS = 3
MIN_EVIDENCE_URLS = 2
ALLOWED_CONTENT_TYPES = {
    "tutorial_troubleshooting",
    "concept_architecture",
    "system_design_case",
    "ai_ml_experiment",
}
ALLOWED_STRUCTURE_MODES = {
    "problem_first",
    "decision_memo",
    "experiment_diary",
    "code_walkthrough",
}
ALLOWED_DEMAND_SOURCES = {"google_trends", "search_console", "both"}
ALLOWED_VERIFICATION_MODES = {"direct", "controlled_comparison", "not_directly_tested"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _atomic_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        temporary = Path(handle.name)
    temporary.replace(path)
    return path


def _briefing_date(payload: dict[str, Any]) -> date | None:
    try:
        return datetime.fromisoformat(str(payload["generated_at"])).astimezone(KST).date()
    except (KeyError, TypeError, ValueError):
        return None


def _safe_daily_payload(path: Path) -> dict[str, Any] | None:
    try:
        return load_daily_briefing(path)
    except (DailyBriefingError, OSError, ValueError, TypeError):
        return None


def _analytics_search_console_excerpt(path: Path, *, generated_at: datetime) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    generated_match = re.search(r"^- generated_at: `([^`]+)`", text, re.MULTILINE)
    if not generated_match:
        return ""
    try:
        report_generated_at = datetime.fromisoformat(generated_match.group(1)).astimezone(UTC)
    except ValueError:
        return ""
    age = generated_at.astimezone(UTC) - report_generated_at
    if age < -timedelta(minutes=5) or age > timedelta(days=14):
        return ""
    marker = "## Search Console 유입"
    if marker not in text:
        return ""
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    return section.strip()[:12000]


def collect_explainer_input(
    runs_dir: Path,
    *,
    run_date: date,
    generated_at: datetime,
    trends_path: Path = DEFAULT_GOOGLE_TRENDS_CACHE,
    analytics_path: Path = ANALYTICS_REPORT,
) -> dict[str, Any]:
    """Freeze recent briefings plus observed demand without inventing popularity."""
    window_start = run_date - timedelta(days=LOOKBACK_DAYS - 1)
    selected: dict[date, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(runs_dir.glob("*/daily-briefing-analysis.json")):
        payload = _safe_daily_payload(path)
        if not payload:
            continue
        day = _briefing_date(payload)
        if day is None or not window_start <= day <= run_date:
            continue
        current = selected.get(day)
        if current is None or str(payload.get("generated_at", "")) > str(current[1].get("generated_at", "")):
            selected[day] = (path, payload)

    days: list[dict[str, Any]] = []
    evidence_urls: set[str] = set()
    candidate_urls: set[str] = set()
    for day in sorted(selected):
        path, payload = selected[day]
        rows = []
        for row in payload.get("must_read", []):
            url = str(row.get("source_url", ""))
            if not url.startswith("https://"):
                continue
            candidate_urls.add(url)
            evidence_urls.add(url)
            rows.append(
                {
                    "title": str(row.get("title", "")),
                    "korean_title": str(row.get("korean_title", "")),
                    "category": str(row.get("category", "")),
                    "source": str(row.get("source", "")),
                    "source_url": url,
                    "why_it_matters": str(row.get("why_it_matters", "")),
                }
            )
        for section in ("core_signals", "insight_cards", "themes", "developer_insights"):
            for row in payload.get(section, []):
                evidence_urls.update(
                    str(url)
                    for url in row.get("evidence_urls", [])
                    if str(url).startswith("https://")
                )
        days.append(
            {
                "date": day.isoformat(),
                "source_path": str(path),
                "headline": payload.get("headline", ""),
                "summary": payload.get("summary", ""),
                "keywords": payload.get("keywords", []),
                "core_signals": payload.get("core_signals", []),
                "insight_cards": payload.get("insight_cards", []),
                "must_read": rows,
            }
        )

    try:
        trends_payload = load_google_trends_cache(trends_path)
        checked_at = datetime.fromisoformat(str(trends_payload.get("checked_at", ""))).astimezone(UTC)
        cache_age = generated_at.astimezone(UTC) - checked_at
        if cache_age < -timedelta(minutes=5) or cache_age > timedelta(hours=6):
            trends_payload = {}
    except (SearchSignalError, TypeError, ValueError):
        trends_payload = {}
    trend_rows = trends_payload.get("rows", [])
    if not isinstance(trend_rows, list):
        trend_rows = []
    trend_rows = [row for row in trend_rows[:100] if isinstance(row, dict)]
    search_console_excerpt = _analytics_search_console_excerpt(
        analytics_path, generated_at=generated_at
    )
    payload = {
        "contract_version": INPUT_VERSION,
        "generated_at": generated_at.astimezone(KST).isoformat(),
        "run_date": run_date.isoformat(),
        "window_start": window_start.isoformat(),
        "window_end": run_date.isoformat(),
        "daily_briefing_count": len(days),
        "days": days,
        "candidate_source_urls": sorted(candidate_urls),
        "evidence_urls": sorted(evidence_urls),
        "demand_signals": {
            "google_trends_checked_at": trends_payload.get("checked_at", ""),
            "google_trends": trend_rows,
            "search_console_excerpt": search_console_excerpt,
        },
    }
    hash_material = {key: value for key, value in payload.items() if key != "generated_at"}
    payload["source_snapshot_hash"] = hashlib.sha256(
        _canonical_json(hash_material).encode("utf-8")
    ).hexdigest()
    return payload


def validate_explainer_input(payload: dict[str, Any]) -> None:
    if payload.get("contract_version") != INPUT_VERSION:
        raise PipelineError("기술 해설 입력 계약 버전이 올바르지 않습니다.")
    if int(payload.get("daily_briefing_count", 0)) < MIN_DAILY_BRIEFINGS:
        raise PipelineError(f"기술 해설에는 최근 브리핑이 최소 {MIN_DAILY_BRIEFINGS}개 필요합니다.")
    if len(set(payload.get("evidence_urls", []))) < MIN_EVIDENCE_URLS:
        raise PipelineError("기술 해설 근거 URL이 부족합니다.")
    signals = payload.get("demand_signals", {})
    if not signals.get("google_trends") and not str(signals.get("search_console_excerpt", "")).strip():
        raise PipelineError("관측된 검색 수요가 없어 기술 해설을 발행하지 않습니다.")


def validate_explainer_plan(path: Path, *, input_payload: dict[str, Any], run_date: date) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError("technical-explainer-plan.json을 읽을 수 없습니다.") from exc
    expected = {
        "contract_version": PLAN_VERSION,
        "run_date": run_date.isoformat(),
        "source_snapshot_hash": input_payload.get("source_snapshot_hash"),
        "category": EXPLAINER_CATEGORY,
    }
    for key, value in expected.items():
        if plan.get(key) != value:
            raise PipelineError(f"기술 해설 계획 {key} 불일치")
    required = {
        "title", "content_type", "structure_mode", "tags", "primary_keyword",
        "secondary_keywords", "target_reader", "reason", "search_intent",
        "research_focus", "demand_signal_source", "demand_signal_basis",
        "candidate_source_url", "reader_outcome", "hands_on_example",
        "failure_or_limit", "verification_mode", "original_artifact",
        "counterexample", "original_value_plan", "evidence_plan",
        "duplicate_check", "internal_link_candidates", "topic_cluster",
        "pillar_candidate", "problem_origin", "editorial_thesis", "chosen_focus",
        "rejected_angle", "recommended_images", "sources", "evidence_urls",
    }
    missing = sorted(key for key in required if not plan.get(key))
    if missing:
        raise PipelineError("기술 해설 계획 필드 누락: " + ", ".join(missing))
    if plan["content_type"] not in ALLOWED_CONTENT_TYPES or plan["content_type"] not in CONTENT_TYPE_GUIDES:
        raise PipelineError("기술 해설 content_type이 허용되지 않습니다.")
    if plan["structure_mode"] not in ALLOWED_STRUCTURE_MODES:
        raise PipelineError("기술 해설 structure_mode가 허용되지 않습니다.")
    if plan["demand_signal_source"] not in ALLOWED_DEMAND_SOURCES:
        raise PipelineError("기술 해설 검색 수요 출처가 허용되지 않습니다.")
    if plan["verification_mode"] not in ALLOWED_VERIFICATION_MODES:
        raise PipelineError("기술 해설 검증 모드가 허용되지 않습니다.")
    signals = input_payload.get("demand_signals", {})
    if plan["demand_signal_source"] in {"google_trends", "both"} and not signals.get("google_trends"):
        raise PipelineError("기술 해설 계획이 존재하지 않는 Google Trends 신호를 인용합니다.")
    if plan["demand_signal_source"] in {"search_console", "both"} and not str(signals.get("search_console_excerpt", "")).strip():
        raise PipelineError("기술 해설 계획이 존재하지 않는 Search Console 신호를 인용합니다.")
    tags = plan.get("tags")
    if not isinstance(tags, list) or not 3 <= len(set(map(str, tags))) <= 4:
        raise PipelineError("기술 해설 tags는 고유한 3~4개여야 합니다.")
    primary_keyword = str(plan["primary_keyword"]).strip()
    if primary_keyword.casefold() not in str(plan["title"]).casefold():
        raise PipelineError("기술 해설 제목에 primary_keyword가 포함되어야 합니다.")
    demand_text = _canonical_json(signals).casefold()
    demand_tokens = {
        token.casefold()
        for token in re.findall(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣._+-]*", primary_keyword)
        if len(token) >= 2
    }
    matched_tokens = {token for token in demand_tokens if token in demand_text}
    required_matches = 1 if len(demand_tokens) == 1 else 2
    if not demand_tokens or len(matched_tokens) < required_matches:
        raise PipelineError("기술 해설 primary_keyword와 관측 검색 신호가 연결되지 않습니다.")
    candidate_urls = set(input_payload.get("candidate_source_urls", []))
    if plan["candidate_source_url"] not in candidate_urls:
        raise PipelineError("기술 해설 대표 원문이 입력 후보에 없습니다.")
    evidence = plan.get("evidence_urls")
    allowed_evidence = set(input_payload.get("evidence_urls", []))
    if not isinstance(evidence, list) or len(set(evidence)) < MIN_EVIDENCE_URLS:
        raise PipelineError("기술 해설 계획의 고유 근거 URL이 부족합니다.")
    if any(url not in allowed_evidence for url in evidence):
        raise PipelineError("기술 해설 계획에 입력 스냅샷 밖의 근거 URL이 있습니다.")
    return plan


def explainer_plan_stage(*, run_id: str, input_path: Path, plan_path: Path, run_date: date) -> Stage:
    return Stage(
        "Technical Explainer Planner Agent",
        PROJECT_ROOT / "agents/technical-explainer-agent.md",
        (
            f"run_id는 {run_id!r}입니다. 입력 {str(input_path)!r}을 읽고 실제 검색 수요와 "
            f"연결되는 독립 기술 해설 한 건의 계획을 {str(plan_path)!r}에 JSON으로 저장하세요. "
            f"run_date는 {run_date.isoformat()!r}, category는 {EXPLAINER_CATEGORY!r}로 고정합니다. "
            "공개 Hunt News의 기존 글을 확인해 duplicate_check를 기록하고, 예제로 설명할 수 "
            "없거나 검색 신호가 주제와 연결되지 않으면 파일을 만들지 마세요. 입력 밖의 URL을 "
            "evidence_urls에 넣거나 다른 파일과 외부 시스템을 변경하지 마세요."
        ),
    )


def category_exists(base_url: str, *, timeout: float = 10.0) -> bool:
    endpoint = urllib.parse.urljoin(
        base_url.rstrip("/") + "/",
        "wp-json/wp/v2/categories?slug=" + urllib.parse.quote(EXPLAINER_CATEGORY_SLUG),
    )
    request = urllib.request.Request(endpoint, headers={"User-Agent": "HuntNewsExplainer/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            rows = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return any(str(row.get("name", "")) == EXPLAINER_CATEGORY for row in rows if isinstance(row, dict))


def _logger(run_date: date) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"technical-explainer-{run_date.isoformat()}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(LOG_DIR / f"technical-explainer-{run_date.isoformat()}.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", help="대상 날짜(YYYY-MM-DD), 기본은 KST 오늘")
    parser.add_argument("--dry-run", action="store_true", help="입력 스냅샷만 검증하고 외부 호출 안 함")
    parser.add_argument("--timeout", type=int, default=3600)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    load_env_file(PROJECT_ROOT / ".env")
    now = datetime.now(UTC).astimezone(KST)
    run_date = date.fromisoformat(args.run_date) if args.run_date else now.date()
    run_id = f"technical-explainer-{run_date.isoformat()}"
    run_directory = RUNS_DIR / run_id
    run_directory.mkdir(parents=True, exist_ok=True)
    input_path = run_directory / "technical-explainer-input.json"
    plan_path = run_directory / "technical-explainer-plan.json"
    logger = _logger(run_date)
    lock = PipelineLock(LOCK_FILE)
    try:
        lock.acquire()
        input_payload = collect_explainer_input(
            RUNS_DIR, run_date=run_date, generated_at=now
        )
        validate_explainer_input(input_payload)
        _atomic_json(input_path, input_payload)
        logger.info(
            "technical_explainer event=input_ready date=%s briefings=%d evidence=%d hash=%s",
            run_date, input_payload["daily_briefing_count"],
            len(input_payload["evidence_urls"]), input_payload["source_snapshot_hash"],
        )
        if args.dry_run:
            print(
                f"technical_explainer status=DRY_RUN input={input_path} "
                f"daily_briefings={input_payload['daily_briefing_count']}"
            )
            return 0
        public_site_url = os.environ.get("PUBLIC_SITE_URL", "https://huntlab.app/")
        if not category_exists(public_site_url):
            raise PipelineError(
                f"사전 생성된 카테고리 {EXPLAINER_CATEGORY!r}({EXPLAINER_CATEGORY_SLUG})가 없습니다."
            )
        codex = resolve_codex()
        if not plan_path.is_file():
            run_stage(
                codex,
                explainer_plan_stage(
                    run_id=run_id, input_path=input_path, plan_path=plan_path, run_date=run_date
                ),
                logger,
                timeout_seconds=args.timeout,
            )
        plan = validate_explainer_plan(plan_path, input_payload=input_payload, run_date=run_date)
        context = make_topic_context(
            run_id,
            str(plan["title"]),
            category=EXPLAINER_CATEGORY,
            tags=tuple(str(tag) for tag in plan["tags"]),
            reason=str(plan["reason"]),
            research_focus=(
                f"기술 해설 입력 스냅샷 {input_path}과 계획 근거만 사용한다. "
                f"독자가 따라갈 예시는 {plan['hands_on_example']}. "
                f"실패 또는 비추천 조건은 {plan['failure_or_limit']}. "
                f"검증 모드는 {plan['verification_mode']}. "
                f"독자에게 남길 고유 산출물은 {plan['original_artifact']}. "
                f"결론이 성립하지 않는 반례는 {plan['counterexample']}. "
                + str(plan["research_focus"])
            ),
            content_type=str(plan["content_type"]),
        )
        if has_successful_publish(context):
            result = read_publish_result(context)
        else:
            try:
                result = run_topic_pipeline(
                    codex, context, plan, logger, timeout_seconds=args.timeout,
                    resume=context.directory.exists(), publish_lock=threading.Lock(),
                    humanize_lock=threading.Lock(),
                )
            except ContentQualityRejection as exc:
                raise PipelineError(f"기술 해설 품질 검토 거절: {exc}") from exc
        logger.info(
            "technical_explainer event=end failed=false date=%s post_id=%s url=%s",
            run_date, result.get("post_id"), result.get("url"),
        )
        print(
            f"technical_explainer status=COMPLETE post_id={result.get('post_id')} "
            f"url={result.get('url')}"
        )
        return 0
    except (PipelineError, OSError, ValueError) as exc:
        logger.exception("technical_explainer event=end failed=true error=%s", exc)
        print(f"technical_explainer status=FAILED error={exc}", file=sys.stderr)
        return 1
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
