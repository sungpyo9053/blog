#!/usr/bin/env python3
"""Publish one evidence-backed weekly Hunt News retrospective."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
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

KST = timezone(timedelta(hours=9))
CONTRACT_VERSION = "weekly-review-input.v1"
PLAN_VERSION = "weekly-review-plan.v1"
WEEKLY_CATEGORY = "주간 기술 회고"
WEEKLY_CATEGORY_SLUG = "weekly-tech-review"
LOCK_FILE = LOG_DIR / "weekly-review.lock"
MIN_DAILY_BRIEFINGS = 5
MIN_EVIDENCE_URLS = 5


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


def week_bounds(today: date) -> tuple[date, date]:
    """Return the Monday-Sunday window containing ``today``."""
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


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


def collect_weekly_input(
    runs_dir: Path,
    *,
    week_start: date,
    week_end: date,
    generated_at: datetime,
) -> dict[str, Any]:
    """Freeze valid daily briefing analyses for one calendar week."""
    selected: dict[date, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(runs_dir.glob("*/daily-briefing-analysis.json")):
        payload = _safe_daily_payload(path)
        if not payload:
            continue
        briefing_day = _briefing_date(payload)
        if briefing_day is None or not week_start <= briefing_day <= week_end:
            continue
        current = selected.get(briefing_day)
        if current is None or str(payload.get("generated_at", "")) > str(current[1].get("generated_at", "")):
            selected[briefing_day] = (path, payload)

    days: list[dict[str, Any]] = []
    evidence_urls: set[str] = set()
    for briefing_day in sorted(selected):
        path, payload = selected[briefing_day]
        for section in (
            "core_signals",
            "matrix",
            "timeline",
            "insight_cards",
            "themes",
            "developer_insights",
            "watchlist",
        ):
            for row in payload.get(section, []):
                evidence_urls.update(str(url) for url in row.get("evidence_urls", []) if str(url).startswith("https://"))
        for row in payload.get("must_read", []):
            url = str(row.get("source_url", ""))
            if url.startswith("https://"):
                evidence_urls.add(url)
        days.append(
            {
                "date": briefing_day.isoformat(),
                "source_path": str(path),
                "generated_at": payload["generated_at"],
                "headline": payload["headline"],
                "summary": payload["summary"],
                "core_signals": payload["core_signals"],
                "themes": payload["themes"],
                "developer_insights": payload["developer_insights"],
                "watchlist": payload["watchlist"],
                "must_read": payload["must_read"],
            }
        )

    payload = {
        "contract_version": CONTRACT_VERSION,
        "generated_at": generated_at.astimezone(KST).isoformat(),
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "daily_briefing_count": len(days),
        "days": days,
        "evidence_urls": sorted(evidence_urls),
    }
    # Execution time is audit metadata, not source identity.  Keeping it out of
    # the digest makes retries over the same frozen daily inputs reproducible.
    hash_material = {key: value for key, value in payload.items() if key != "generated_at"}
    payload["source_snapshot_hash"] = hashlib.sha256(
        _canonical_json(hash_material).encode("utf-8")
    ).hexdigest()
    return payload


def validate_weekly_input(payload: dict[str, Any]) -> None:
    if payload.get("contract_version") != CONTRACT_VERSION:
        raise PipelineError("주간 회고 입력 계약 버전이 올바르지 않습니다.")
    if int(payload.get("daily_briefing_count", 0)) < MIN_DAILY_BRIEFINGS:
        raise PipelineError(
            f"주간 회고에는 유효한 일일 브리핑이 최소 {MIN_DAILY_BRIEFINGS}개 필요합니다."
        )
    if len(payload.get("evidence_urls", [])) < MIN_EVIDENCE_URLS:
        raise PipelineError("주간 회고 근거 URL이 부족합니다.")


def validate_weekly_plan(
    path: Path, *, input_payload: dict[str, Any], week_start: date, week_end: date
) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError("weekly-plan.json을 읽을 수 없습니다.") from exc
    if not isinstance(plan, dict) or plan.get("contract_version") != PLAN_VERSION:
        raise PipelineError("주간 회고 계획 계약이 올바르지 않습니다.")
    expected = {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "source_snapshot_hash": input_payload.get("source_snapshot_hash"),
        "category": WEEKLY_CATEGORY,
        "content_type": "concept_architecture",
        "structure_mode": "impact_timeline",
    }
    for key, value in expected.items():
        if plan.get(key) != value:
            raise PipelineError(f"주간 회고 계획 {key} 불일치")
    required = {
        "title", "tags", "primary_keyword", "secondary_keywords", "target_reader",
        "reason", "search_intent", "research_focus", "demand_signal_source",
        "observed_problem_phrase", "user_action", "original_value_plan",
        "evidence_plan", "duplicate_check", "internal_link_candidates",
        "topic_cluster", "pillar_candidate", "problem_origin", "editorial_thesis",
        "chosen_focus", "rejected_angle", "recommended_images", "sources",
        "evidence_urls",
    }
    missing = sorted(key for key in required if not plan.get(key))
    if missing:
        raise PipelineError("주간 회고 계획 필드 누락: " + ", ".join(missing))
    tags = plan.get("tags")
    if not isinstance(tags, list) or not 3 <= len(set(map(str, tags))) <= 4:
        raise PipelineError("주간 회고 tags는 고유한 3~4개여야 합니다.")
    primary_keyword = str(plan["primary_keyword"]).strip()
    if primary_keyword.casefold() not in str(plan["title"]).casefold():
        raise PipelineError("주간 회고 제목에 primary_keyword가 포함되어야 합니다.")
    if "주간" not in str(plan["title"]):
        raise PipelineError("주간 회고 제목에 주간 식별 문구가 없습니다.")
    if plan.get("problem_origin") not in {"official_change", "observed_search_question"}:
        raise PipelineError("주간 회고 problem_origin이 허용된 값이 아닙니다.")
    allowed = set(input_payload.get("evidence_urls", []))
    evidence = plan.get("evidence_urls")
    if not isinstance(evidence, list) or len(set(evidence)) < MIN_EVIDENCE_URLS:
        raise PipelineError("주간 회고 계획의 고유 근거 URL이 부족합니다.")
    if any(url not in allowed for url in evidence):
        raise PipelineError("주간 회고 계획에 입력 스냅샷 밖의 근거 URL이 있습니다.")
    return plan


def weekly_plan_stage(
    *, run_id: str, input_path: Path, plan_path: Path, week_start: date, week_end: date
) -> Stage:
    return Stage(
        "Weekly Review Planner Agent",
        PROJECT_ROOT / "agents/weekly-review-agent.md",
        (
            f"run_id는 {run_id!r}입니다. 주간 입력 {str(input_path)!r}을 읽고 "
            f"{week_start.isoformat()}부터 {week_end.isoformat()}까지를 회고하는 계획을 "
            f"{str(plan_path)!r}에 JSON으로 저장하세요. Analytics 리포트 "
            f"{str(PROJECT_ROOT / 'output/analytics/latest.md')!r}는 데이터 지연을 명시한 "
            "보조 검색 관심 신호로만 사용하세요. 공개 Hunt News에서 같은 주차·검색 의도의 "
            "기존 글을 확인하고 duplicate_check에 결과를 기록하세요. 카테고리는 '주간 기술 회고', "
            "content_type은 concept_architecture, structure_mode는 impact_timeline으로 고정하세요. "
            "입력 스냅샷에 없는 URL을 evidence_urls에 넣지 마세요. 다른 파일과 외부 시스템은 변경하지 마세요."
        ),
    )


def category_exists(base_url: str, *, timeout: float = 10.0) -> bool:
    endpoint = urllib.parse.urljoin(
        base_url.rstrip("/") + "/",
        "wp-json/wp/v2/categories?slug=" + urllib.parse.quote(WEEKLY_CATEGORY_SLUG),
    )
    request = urllib.request.Request(endpoint, headers={"User-Agent": "HuntNewsWeeklyReview/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            rows = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return any(str(row.get("name", "")) == WEEKLY_CATEGORY for row in rows if isinstance(row, dict))


def _logger(week_start: date) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"weekly-review-{week_start.isoformat()}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(
            LOG_DIR / f"weekly-review-{week_start.isoformat()}.log", encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week-end", help="대상 주의 일요일(YYYY-MM-DD), 기본은 오늘이 속한 주")
    parser.add_argument("--dry-run", action="store_true", help="입력 스냅샷만 검증하고 외부 호출 안 함")
    parser.add_argument("--timeout", type=int, default=3600)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    load_env_file(PROJECT_ROOT / ".env")
    now = datetime.now(UTC).astimezone(KST)
    if args.week_end:
        week_end = date.fromisoformat(args.week_end)
        week_start = week_end - timedelta(days=6)
    else:
        week_start, week_end = week_bounds(now.date())
    if week_end.weekday() != 6:
        raise SystemExit("--week-end는 일요일이어야 합니다.")
    run_id = f"weekly-{week_start.isoformat()}-{week_end.isoformat()}"
    run_directory = RUNS_DIR / run_id
    run_directory.mkdir(parents=True, exist_ok=True)
    input_path = run_directory / "weekly-input.json"
    plan_path = run_directory / "weekly-plan.json"
    logger = _logger(week_start)
    lock = PipelineLock(LOCK_FILE)
    try:
        lock.acquire()
        weekly_input = collect_weekly_input(
            RUNS_DIR, week_start=week_start, week_end=week_end, generated_at=now
        )
        validate_weekly_input(weekly_input)
        _atomic_json(input_path, weekly_input)
        logger.info(
            "weekly_review event=input_ready week=%s..%s daily_briefings=%d evidence=%d hash=%s",
            week_start, week_end, weekly_input["daily_briefing_count"],
            len(weekly_input["evidence_urls"]), weekly_input["source_snapshot_hash"],
        )
        if args.dry_run:
            print(
                f"weekly_review status=DRY_RUN input={input_path} "
                f"daily_briefings={weekly_input['daily_briefing_count']}"
            )
            return 0
        public_site_url = os.environ.get("PUBLIC_SITE_URL", "https://huntlab.app/")
        if not category_exists(public_site_url):
            raise PipelineError(
                f"사전 생성된 카테고리 {WEEKLY_CATEGORY!r}({WEEKLY_CATEGORY_SLUG})가 없습니다."
            )
        codex = resolve_codex()
        if not plan_path.is_file():
            run_stage(
                codex,
                weekly_plan_stage(
                    run_id=run_id, input_path=input_path, plan_path=plan_path,
                    week_start=week_start, week_end=week_end,
                ),
                logger,
                timeout_seconds=args.timeout,
            )
        plan = validate_weekly_plan(
            plan_path, input_payload=weekly_input, week_start=week_start, week_end=week_end
        )
        context = make_topic_context(
            run_id,
            str(plan["title"]),
            category=WEEKLY_CATEGORY,
            tags=tuple(str(tag) for tag in plan["tags"]),
            reason=str(plan["reason"]),
            research_focus=(
                f"주간 입력 스냅샷 {input_path}과 계획 근거만 사용한다. "
                + str(plan["research_focus"])
            ),
            content_type="concept_architecture",
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
                raise PipelineError(f"주간 회고 품질 검토 거절: {exc}") from exc
        logger.info(
            "weekly_review event=end failed=false week=%s..%s post_id=%s url=%s",
            week_start, week_end, result.get("post_id"), result.get("url"),
        )
        print(
            f"weekly_review status=COMPLETE post_id={result.get('post_id')} "
            f"url={result.get('url')}"
        )
        return 0
    except (PipelineError, OSError, ValueError) as exc:
        logger.exception("weekly_review event=failed reason=%s", exc)
        print(f"weekly_review status=FAILED reason={type(exc).__name__}")
        return 1
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
