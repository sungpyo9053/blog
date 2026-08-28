#!/usr/bin/env python3
"""Run the Hunt News daily TOP2 pipeline with fail-fast logging."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import threading
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from publisher.frontmatter import FrontmatterError, load_document
from publisher.config import ConfigurationError, WordPressConfig
from publisher.wordpress import WordPressClient, WordPressError
from scripts.briefing_manifest import (
    atomic_write_manifest,
    build_briefing_manifest,
    collect_run_publications,
)
from scripts.daily_briefing import DailyBriefingError, load_daily_briefing
from scripts.manage_whereispost_cache import (
    DEFAULT_CACHE as DEFAULT_WHEREISPOST_CACHE,
    DEFAULT_MAX_AGE_DAYS as DEFAULT_WHEREISPOST_MAX_AGE_DAYS,
)
from scripts.news_worthiness import (
    build_shadow_diff,
    make_shadow_input_snapshot,
    write_shadow_diff,
)
from scripts.search_signal_providers import (
    DEFAULT_EDITORIAL_SOURCE_CACHE,
    DEFAULT_GOOGLE_TRENDS_CACHE,
    SearchSignalError,
    load_editorial_source_cache,
    load_google_trends_cache,
    load_whereispost_shadow,
)


OUTPUT_DIR = PROJECT_ROOT / "output"
RUNS_DIR = OUTPUT_DIR / "runs"
ANALYTICS_REPORT = OUTPUT_DIR / "analytics" / "latest.md"
HUMANIZE_EXPERIMENT_STATE = OUTPUT_DIR / "humanize-experiment-state.json"
LOG_DIR = PROJECT_ROOT / "logs"
LOCK_FILE = LOG_DIR / "daily-pipeline.lock"
TOP2_PATTERN = re.compile(r"(?m)^\s*[12]\.\s+(.+?)\s*$")
ACTIVE_EDITOR_CATEGORIES = {
    "AI/ML 핵심",
    "개발 트렌드",
    "AI 공식 블로그",
    "국내 IT",
    "국내 시사",
}
ACTIVE_CATEGORY_SLUGS = {
    "ai-ml-core": "AI/ML 핵심",
    "development-trends": "개발 트렌드",
    "ai-official-blogs": "AI 공식 블로그",
    "korea-it": "국내 IT",
    "korea-current-affairs": "국내 시사",
}
LEGACY_EDITOR_CATEGORIES = {
    "생활", "경제", "부동산", "사회", "정치", "문화·엔터", "IT",
    "Tech",
    "AI",
    "Economy",
    "Society",
    "Politics",
    "Hot Issue",
    "Build Log",
    "ML Algorithms",
    "Harness Engineering",
    "System Architecture",
}
EDITOR_CATEGORIES = ACTIVE_EDITOR_CATEGORIES | LEGACY_EDITOR_CATEGORIES
CONTENT_TYPE_GUIDES = {
    "tutorial_troubleshooting": PROJECT_ROOT / "guides/content-types/tutorial-troubleshooting.md",
    "concept_architecture": PROJECT_ROOT / "guides/content-types/concept-architecture.md",
    "system_design_case": PROJECT_ROOT / "guides/content-types/system-design-case.md",
    "ai_ml_experiment": PROJECT_ROOT / "guides/content-types/ai-ml-experiment.md",
    "build_log_operations": PROJECT_ROOT / "guides/content-types/build-log-operations.md",
    "current_affairs_policy": PROJECT_ROOT / "guides/content-types/current-affairs-policy.md",
    "life_impact_explainer": PROJECT_ROOT / "guides/content-types/life-impact-explainer.md",
}
LEGACY_CONTENT_TYPE_BY_CATEGORY = {
    "AI/ML 핵심": "concept_architecture",
    "개발 트렌드": "tutorial_troubleshooting",
    "AI 공식 블로그": "concept_architecture",
    "국내 IT": "current_affairs_policy",
    "국내 시사": "current_affairs_policy",
    "Tech": "tutorial_troubleshooting",
    "AI": "ai_ml_experiment",
    "ML Algorithms": "ai_ml_experiment",
    "Harness Engineering": "concept_architecture",
    "System Architecture": "concept_architecture",
    "Build Log": "build_log_operations",
    "Economy": "current_affairs_policy",
    "Society": "current_affairs_policy",
    "Politics": "current_affairs_policy",
    "Hot Issue": "current_affairs_policy",
    "생활": "life_impact_explainer",
    "경제": "life_impact_explainer",
    "부동산": "life_impact_explainer",
    "사회": "life_impact_explainer",
    "정치": "life_impact_explainer",
    "문화·엔터": "life_impact_explainer",
    "IT": "tutorial_troubleshooting",
}
MAX_REVIEW_REPAIR_ATTEMPTS = 1
RECENT_STYLE_LIMIT = 5
REVIEW_STATUS_PATTERN = re.compile(
    r"(?im)^\s*(?:-\s*)?(?:status|decision|verdict)\s*:\s*`?(APPROVED|REJECTED)`?\s*$"
    r"|^\s*(APPROVED|REJECTED)\s*$"
)


class PipelineError(RuntimeError):
    """Raised when a stage cannot safely continue."""


class ContentQualityRejection(PipelineError):
    """A candidate failed an evidence or Reviewer gate and may be replaced safely."""


def parse_whereispost_total_searches(value: str, title: str) -> int:
    normalized = value.replace(",", "").strip()
    if not re.fullmatch(r"\d+", normalized):
        raise PipelineError(
            f"{title}: whereispost_total_searches는 0 이상의 정수여야 합니다."
        )
    return int(normalized)


def parse_google_trends_approx_traffic(value: str, title: str) -> int:
    normalized = value.replace(",", "").strip()
    if not re.fullmatch(r"\d+", normalized):
        raise PipelineError(
            f"{title}: google_trends_approx_traffic은 0 이상의 정수여야 합니다."
        )
    return int(normalized)


@dataclass(frozen=True)
class Stage:
    name: str
    agent_file: Path | None
    prompt: str


@dataclass(frozen=True)
class TopicContext:
    title: str
    run_id: str
    topic_id: str
    directory: Path
    category: str = "Tech"
    tags: tuple[str, ...] = ()
    reason: str = ""
    research_focus: str = ""
    content_type: str = "tutorial_troubleshooting"

    @property
    def source_id(self) -> str:
        return f"huntlab:{self.run_id}:{self.topic_id}"


class PipelineLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    @staticmethod
    def _pid_is_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "started_at": datetime.now(UTC).isoformat(),
        }
        for _ in range(2):
            try:
                descriptor = os.open(
                    self.path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                try:
                    current = json.loads(self.path.read_text(encoding="utf-8"))
                    current_pid = int(current.get("pid", 0))
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    current_pid = 0
                if self._pid_is_alive(current_pid):
                    raise PipelineError(
                        f"Daily Pipeline이 이미 실행 중입니다(pid={current_pid})."
                    )
                self.path.unlink(missing_ok=True)
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream)
            self.acquired = True
            return
        raise PipelineError("오래된 Pipeline lock을 정리하지 못했습니다.")

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            current = json.loads(self.path.read_text(encoding="utf-8"))
            if int(current.get("pid", 0)) == os.getpid():
                self.path.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        self.acquired = False


def configure_logger(run_date: date) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("huntlab.daily")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    file_handler = logging.FileHandler(
        LOG_DIR / f"{run_date.isoformat()}.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    return logger


def resolve_codex() -> str:
    executable = os.environ.get("CODEX_BIN") or shutil.which("codex")
    if not executable:
        raise PipelineError(
            "Codex CLI를 찾을 수 없습니다. CODEX_BIN을 설정하세요."
        )
    return executable


def build_codex_command(codex: str, prompt: str) -> list[str]:
    return [
        codex,
        "--ask-for-approval",
        "never",
        "--sandbox",
        "danger-full-access",
        "--search",
        "exec",
        "--ephemeral",
        "--color",
        "never",
        "--cd",
        str(PROJECT_ROOT),
        prompt,
    ]


def redact_log_text(value: str) -> str:
    value = re.sub(
        r"(?i)(WORDPRESS_(?:APP_PASSWORD|USERNAME|URL)\s*[=:]\s*)\S+",
        r"\1[REDACTED]",
        value,
    )
    return re.sub(
        r"\b(?:[A-Za-z0-9]{4}\s+){5}[A-Za-z0-9]{4}\b",
        "[REDACTED_APPLICATION_PASSWORD]",
        value,
    )


def stage_instruction(stage: Stage) -> str:
    instruction = stage.prompt
    if stage.agent_file is not None:
        instruction = (
            f"먼저 {stage.agent_file.relative_to(PROJECT_ROOT)}를 처음부터 끝까지 "
            f"읽고 그 정책을 따르세요.\n\n{stage.prompt}"
        )
    return (
        "비대화식 Cron 실행입니다. 사용자 승인이나 입력을 요청하거나 기다리지 "
        "마세요. 현재 승인 정책에서 허용되지 않는 작업이 필요하면 즉시 실패하고 "
        "이유를 반환하세요. .env의 값과 WordPress 인증정보를 직접 출력하거나 "
        "최종 응답에 포함하지 마세요. Publisher 이외 단계는 외부 시스템을 "
        "변경하지 마세요. 프로젝트 루트 밖의 파일을 생성·수정·삭제하지 말고, "
        "Git commit/push와 시스템 설정 변경을 수행하지 마세요.\n\n" + instruction
    )


def run_stage(
    codex: str,
    stage: Stage,
    logger: logging.Logger,
    *,
    timeout_seconds: int,
    topic: str = "-",
) -> str:
    started = time.monotonic()
    logger.info("topic=%r agent=%s event=start", topic, stage.name)
    command = build_codex_command(codex, stage_instruction(stage))
    child_env = os.environ.copy()
    child_env.update(
        {
            "HOME": str(Path.home()),
            "CODEX_HOME": os.environ.get(
                "CODEX_HOME",
                str(Path.home() / ".codex"),
            ),
            "PATH": os.pathsep.join(
                [
                    str(Path(codex).parent),
                    str(PROJECT_ROOT / ".venv/bin"),
                    "/opt/homebrew/bin",
                    "/usr/local/bin",
                    "/usr/bin",
                    "/bin",
                    "/usr/sbin",
                    "/sbin",
                ]
            ),
        }
    )
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
            env=child_env,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        logger.error(
            "topic=%r agent=%s event=failed duration_seconds=%.3f reason=timeout",
            topic,
            stage.name,
            elapsed,
        )
        raise PipelineError(f"{stage.name} 시간 제한 초과") from exc

    elapsed = time.monotonic() - started
    if result.stdout:
        for line in result.stdout.rstrip().splitlines():
            logger.info(
                "topic=%r agent=%s output=%s",
                topic,
                stage.name,
                redact_log_text(line),
            )
    if result.returncode != 0:
        logger.error(
            "topic=%r agent=%s event=failed duration_seconds=%.3f exit_code=%d",
            topic,
            stage.name,
            elapsed,
            result.returncode,
        )
        raise PipelineError(
            f"{stage.name} 실패(exit_code={result.returncode})"
        )
    logger.info(
        "topic=%r agent=%s event=end duration_seconds=%.3f failed=false",
        topic,
        stage.name,
        elapsed,
    )
    return result.stdout or ""


def parse_top2(path: Path) -> list[str]:
    return [item["title"] for item in parse_topic_plan(path)]


def parse_topic_plan_document(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PipelineError(f"Topic Planner가 {path}를 생성하지 않았습니다.")
    text = path.read_text(encoding="utf-8")
    marker = re.search(r"(?m)^## TOP2\s*$", text)
    if marker is None:
        raise PipelineError(f"{path}에 TOP2 섹션이 없습니다.")
    topics = [match.strip() for match in TOP2_PATTERN.findall(text[marker.end() :])]
    if len(topics) != 2 or len(set(topics)) != 2:
        raise PipelineError("TOP2에는 서로 다른 주제 두 개가 정확히 있어야 합니다.")
    candidate_matches = list(
        re.finditer(
            r"(?ms)^##\s+(\d+)\.\s+(.+?)\s*$\n(.*?)(?=^##\s+(?:\d+\.|TOP10|TOP2)\s|\Z)",
            text[: marker.start()],
        )
    )
    if len(candidate_matches) < 35:
        raise PipelineError("Topic Candidates가 35개 미만입니다.")

    required_fields = {
        "title",
        "category",
        "tags",
        "score",
        "score_breakdown",
        "reason",
        "evergreen",
        "search_intent",
        "research_focus",
        "recommended_images",
        "duplicate_check",
        "internal_link_candidates",
        "topic_cluster",
        "pillar_candidate",
        "problem_origin",
        "editorial_thesis",
        "chosen_focus",
        "rejected_angle",
        "structure_mode",
    }
    candidates: dict[str, dict[str, Any]] = {}
    for match in candidate_matches:
        fields = {
            key.strip(): value.strip()
            for key, value in re.findall(
                r"(?m)^-\s+([a-z_]+):\s*(.+?)\s*$",
                match.group(3),
            )
        }
        missing = sorted(required_fields - fields.keys())
        if missing:
            raise PipelineError(
                f"Topic Candidate {match.group(1)} 필드 누락: {', '.join(missing)}"
            )
        title = fields["title"]
        if title != match.group(2).strip():
            raise PipelineError(f"Topic Candidate 제목 불일치: {title}")
        category = fields["category"]
        if category not in EDITOR_CATEGORIES:
            raise PipelineError(f"허용되지 않은 카테고리: {category}")
        content_type = fields.get("content_type") or LEGACY_CONTENT_TYPE_BY_CATEGORY[
            category
        ]
        if content_type not in CONTENT_TYPE_GUIDES:
            raise PipelineError(f"{title}: 허용되지 않은 content_type: {content_type}")
        if content_type == "life_impact_explainer":
            impact_fields = {
                "affected_reader",
                "life_impact",
                "effective_date",
                "reader_action",
                "whereispost_status",
                "whereispost_metrics",
            }
            missing_impact = sorted(impact_fields - fields.keys())
            if missing_impact:
                raise PipelineError(
                    f"{title}: 생활 영향 필드 누락: {', '.join(missing_impact)}"
                )
        tags = tuple(
            dict.fromkeys(tag.strip() for tag in fields["tags"].split(",") if tag.strip())
        )
        if not 3 <= len(tags) <= 4:
            raise PipelineError(f"{title}: tags는 재사용 가능한 3~4개여야 합니다.")
        if fields["problem_origin"] not in {
            "real_project",
            "public_codebase",
            "observed_search_question",
            "controlled_lab",
            "official_change",
        }:
            raise PipelineError(f"{title}: 허용되지 않은 problem_origin")
        if fields["structure_mode"] not in {
            "problem_first",
            "decision_memo",
            "experiment_diary",
            "code_walkthrough",
            "field_note",
            "impact_timeline",
            "household_case",
            "before_after",
            "eligibility_check",
        }:
            raise PipelineError(f"{title}: 허용되지 않은 structure_mode")
        candidates[title] = {
            **fields,
            "content_type": content_type,
            "tags": tags,
        }
        if "google_trends_approx_traffic" in fields:
            candidates[title]["google_trends_approx_traffic"] = (
                parse_google_trends_approx_traffic(
                    fields["google_trends_approx_traffic"], title
                )
            )
        if "whereispost_total_searches" in fields:
            candidates[title]["whereispost_total_searches"] = (
                parse_whereispost_total_searches(
                    fields["whereispost_total_searches"], title
                )
            )

    top10_marker = re.search(r"(?m)^## TOP10\s*$", text)
    if top10_marker is None or top10_marker.start() > marker.start():
        raise PipelineError(f"{path}에 TOP10 섹션이 없습니다.")
    top10 = [
        item.strip()
        for item in re.findall(
            r"(?m)^\s*(?:[1-9]|10)\.\s+(.+?)\s*$",
            text[top10_marker.end() : marker.start()],
        )
    ]
    if len(top10) != 10 or len(set(top10)) != 10:
        raise PipelineError("TOP10에는 서로 다른 후보 10개가 정확히 있어야 합니다.")
    if any(title not in candidates for title in top10):
        raise PipelineError("TOP10 제목이 Topic Candidates와 일치하지 않습니다.")
    if any(title not in top10 for title in topics):
        raise PipelineError("TOP2는 TOP10에 포함되어야 합니다.")
    for title in topics:
        primary_keyword = candidates[title].get("primary_keyword", "").strip()
        if not primary_keyword:
            raise PipelineError(f"{title}: TOP2 primary_keyword가 없습니다.")
        if primary_keyword.casefold() not in title.casefold():
            raise PipelineError(
                f"{title}: TOP2 제목에 primary_keyword가 포함되어야 합니다: "
                f"{primary_keyword}"
            )
    tracks = [candidates[title].get("selection_track", "").strip() for title in topics]
    if any(tracks):
        if set(tracks) != {"public_signal", "huntlab_core"}:
            raise PipelineError(
                "TOP2 selection_track은 public_signal 1개와 huntlab_core 1개여야 합니다."
            )
    return {
        "candidates": list(candidates.values()),
        "top10": [candidates[title] for title in top10],
        "top2": [candidates[title] for title in topics],
    }


def parse_topic_plan(path: Path) -> list[dict[str, Any]]:
    return parse_topic_plan_document(path)["top2"]


def run_news_worthiness_shadow(
    run_directory: Path,
    document: dict[str, Any],
    logger: logging.Logger,
) -> Path | None:
    """Write Shadow comparison data without changing or blocking legacy TOP2."""
    output_path = run_directory / "news-worthiness-shadow.json"
    legacy_snapshot = tuple(str(item.get("title", "")) for item in document.get("top2", []))
    try:
        candidate_snapshot, legacy_snapshot = make_shadow_input_snapshot(
            document["candidates"], document["top2"]
        )
        payload = build_shadow_diff(candidate_snapshot, legacy_snapshot)
        write_shadow_diff(output_path, payload)
    except Exception as exc:  # Shadow is a read-only observer and must fail open.
        error_path = run_directory / "news-worthiness-shadow-error.json"
        error_payload = {
            "selection_mode": "shadow",
            "status": "failed",
            "continuing": True,
            "error_type": type(exc).__name__,
            "legacy_top2": list(legacy_snapshot),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        try:
            write_shadow_diff(error_path, error_payload)
        except Exception as artifact_exc:
            logger.warning(
                "shadow_ranking event=error_artifact_failed continuing=true "
                "path=%s reason_type=%s",
                error_path,
                type(artifact_exc).__name__,
            )
        logger.warning(
            "shadow_ranking event=failed continuing=true run_directory=%s "
            "reason_type=%s error_artifact=%s",
            run_directory,
            type(exc).__name__,
            error_path,
        )
        return None
    logger.info(
        "shadow_ranking event=end failed=false mode=shadow legacy_top2=%r "
        "shadow_top2=%r overlap_count=%d artifact=%s",
        payload["legacy_top2"],
        payload["shadow_top2"],
        payload["overlap_count"],
        output_path,
    )
    return output_path


def make_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid.uuid4().hex[:10]}"


def make_topic_id(title: str) -> str:
    normalized = " ".join(title.split()).casefold()
    return f"topic-{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]}"


def make_topic_context(
    run_id: str,
    title: str,
    *,
    category: str = "Tech",
    tags: tuple[str, ...] = (),
    reason: str = "",
    research_focus: str = "",
    content_type: str = "tutorial_troubleshooting",
) -> TopicContext:
    if content_type not in CONTENT_TYPE_GUIDES:
        raise PipelineError(f"허용되지 않은 content_type: {content_type}")
    topic_id = make_topic_id(title)
    directory = RUNS_DIR / run_id / topic_id
    return TopicContext(
        title=title,
        run_id=run_id,
        topic_id=topic_id,
        directory=directory,
        category=category,
        tags=tags,
        reason=reason,
        research_focus=research_focus,
        content_type=content_type,
    )


def assert_owned_path(context: TopicContext, path: Path) -> None:
    expected_root = context.directory.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(expected_root):
        raise PipelineError(
            f"{context.topic_id}: 주제 디렉터리 밖의 경로를 거부했습니다: {resolved}"
        )


def write_planner_context(context: TopicContext, plan: dict[str, Any]) -> Path:
    """Persist the selected Planner evidence inside the topic's isolation boundary."""
    path = context.directory / "planner-context.json"
    assert_owned_path(context, path)
    duplicate_check = str(plan.get("duplicate_check", "")).strip()
    if not duplicate_check:
        raise PipelineError(f"{context.topic_id}: Planner 중복 검사 근거가 없습니다.")
    editorial_fields = {
        key: str(plan.get(key, "")).strip()
        for key in (
            "problem_origin",
            "editorial_thesis",
            "chosen_focus",
            "rejected_angle",
            "structure_mode",
        )
    }
    missing_editorial = [key for key, value in editorial_fields.items() if not value]
    if missing_editorial:
        raise PipelineError(
            f"{context.topic_id}: Planner 편집 방향 누락: "
            + ", ".join(missing_editorial)
        )
    payload = {
        "run_id": context.run_id,
        "topic_id": context.topic_id,
        "title": context.title,
        "category": context.category,
        "content_type": context.content_type,
        "tags": list(context.tags),
        "primary_keyword": plan.get("primary_keyword", ""),
        "secondary_keywords": plan.get("secondary_keywords", ""),
        "target_reader": plan.get("target_reader", ""),
        "demand_signal_source": plan.get("demand_signal_source", ""),
        "observed_problem_phrase": plan.get("observed_problem_phrase", ""),
        "user_action": plan.get("user_action", ""),
        "reason": context.reason,
        "search_intent": plan.get("search_intent", ""),
        "research_focus": context.research_focus,
        "original_value_plan": plan.get("original_value_plan", ""),
        "evidence_plan": plan.get("evidence_plan", ""),
        "duplicate_check": duplicate_check,
        "internal_link_candidates": plan.get("internal_link_candidates", ""),
        "topic_cluster": plan.get("topic_cluster", ""),
        "pillar_candidate": plan.get("pillar_candidate", ""),
        "sources": plan.get("sources", ""),
        "existing_post_id": plan.get("existing_post_id", ""),
        "existing_slug": plan.get("existing_slug", ""),
        **editorial_fields,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _plain_paragraphs(markdown: str) -> list[str]:
    """Extract prose shape without turning previous articles into fact input."""
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", markdown):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or lines[0].startswith(
            ("#", "- ", "* ", ">", "```", "![", "|")
        ):
            continue
        text = " ".join(lines)
        text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"[`*_]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            paragraphs.append(text[:500])
    return paragraphs


def write_recent_style_context(context: TopicContext) -> Path:
    """Snapshot recent article shapes for repetition checks, never fact reuse."""
    path = context.directory / "recent-style-context.json"
    assert_owned_path(context, path)
    candidates: list[tuple[float, Path]] = []
    if RUNS_DIR.is_dir():
        for publish_path in RUNS_DIR.glob("*/*/publish.md"):
            if publish_path.parent.resolve() == context.directory.resolve():
                continue
            try:
                candidates.append((publish_path.stat().st_mtime, publish_path))
            except OSError:
                continue
    snapshots: list[dict[str, Any]] = []
    for _, publish_path in sorted(candidates, reverse=True):
        if len(snapshots) >= RECENT_STYLE_LIMIT:
            break
        try:
            document = load_document(publish_path)
        except FrontmatterError:
            continue
        paragraphs = _plain_paragraphs(document.markdown)
        headings = [
            re.sub(r"[`*_]", "", heading).strip()
            for heading in re.findall(r"(?m)^##\s+(.+?)\s*$", document.markdown)
        ]
        planner_path = publish_path.parent / "planner-context.json"
        structure_mode = ""
        if planner_path.is_file():
            try:
                planner = json.loads(planner_path.read_text(encoding="utf-8"))
                structure_mode = str(planner.get("structure_mode", "")).strip()
            except (OSError, json.JSONDecodeError):
                pass
        snapshots.append(
            {
                "title": str(document.metadata.get("title", "")).strip(),
                "structure_mode": structure_mode,
                "opening_paragraphs": paragraphs[:2],
                "h2_headings": headings,
                "closing_paragraph": paragraphs[-1] if paragraphs else "",
            }
        )
    payload = {
        "purpose": "style_repetition_check_only",
        "fact_reuse_allowed": False,
        "recent_count": len(snapshots),
        "articles": snapshots,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def topic_stages(context: TopicContext) -> list[Stage]:
    topic = context.title
    topic_dir = context.directory
    content_type_guide = CONTENT_TYPE_GUIDES[context.content_type]
    recent_style_context = topic_dir / "recent-style-context.json"
    common = (
        f"run_id={context.run_id!r}, topic_id={context.topic_id!r}, "
        f"topic_title={topic!r}입니다. 주제별 콘텐츠 입력과 산출물은 "
        f"{str(topic_dir)!r} 아래로 제한합니다. Agent 정책과 Guide는 프로젝트의 "
        "agents/ 및 guides/에서 읽어야 하며 주제별 콘텐츠 입력으로 간주하지 "
        "않습니다. output의 다른 실행이나 다른 주제 디렉터리를 입력 후보로 "
        "검색하거나 재사용하지 마세요. "
    )
    editorial = (
        f"Editor 지정값은 category={context.category!r}, "
        f"content_type={context.content_type!r}, "
        f"tags={list(context.tags)!r}, reason={context.reason!r}, "
        f"research_focus={context.research_focus!r}입니다. 이 값을 그대로 활용하고 "
        "카테고리, 글 유형과 태그를 다른 값으로 바꾸지 마세요. "
    )
    content_guidance = (
        f"공통 문체는 {str(PROJECT_ROOT / 'guides/style-guide.md')!r}, 이 글에만 "
        f"적용할 유형별 규칙은 {str(content_type_guide)!r}에서 읽으세요. 다른 "
        "유형 가이드를 함께 섞지 마세요. "
    )
    common += editorial
    quick_view_writer = (
        "도입 직후에 정확히 `## 20초 핵심 요약`을 두고 `무엇`, `왜`, `어떻게`를 각각 한 개의 "
        "짧은 항목으로 작성하세요. 독자가 20초 안에 대상, 해결 이유와 본문에서 확인할 "
        "방법을 파악해야 하며 research.md에 없는 사실을 추가하거나 도입·결론을 반복하지 "
        "마세요. 이 H2는 문서 전체에 정확히 한 번만 두고, `왜`에는 실제 손실·오작동·선택 "
        "이유를 쓰세요. `문제 또는 판단 기준을 놓치지 않기 위해서`, `순서로 확인합니다` "
        "같은 범용 자동 문구는 금지합니다. WordPress의 기존 `한눈에 보기` 자동 목차는 별도 탐색 기능이므로 삭제하거나 "
        "대체하지 마세요. "
    )
    quick_view_review = (
        "도입 직후의 정확한 `## 20초 핵심 요약`에 근거가 확인되는 `무엇`, `왜`, `어떻게`가 각각 "
        "존재하고 20초 안에 이해할 수 있는지 검사하세요. 하나라도 빠지거나 본문에 없는 "
        "주장을 만들었으면 REJECT하세요. 같은 H2가 두 번이거나 `왜`가 UI 제목을 이유로 "
        "삼거나 범용 자동 문구를 사용해도 REJECT하세요. WordPress의 기존 `한눈에 보기` 자동 목차를 "
        "삭제하거나 대체하지 마세요. "
    )
    stages = [
        Stage(
            "Research Agent",
            PROJECT_ROOT / "agents/researcher.md",
            (
                common
                + content_guidance
                + f"Topic Planner의 TOP2 중 다음 주제만 조사하세요: {topic!r}. "
                f"선정 근거와 검색 의도는 {str(topic_dir / 'planner-context.json')!r}에서 "
                "읽고, 중복 검사 결과를 사실 근거로 확대 해석하지 마세요. "
                "Build Log라면 기존 작업 기록에서 evidence_origin, work_trigger, actual_sequence, "
                "friction_or_surprise, decision_log, unfinished_edge를 확인해 `## 작업 기록`에 "
                "남기세요. 글을 위해 새로 만든 테스트뿐이면 existing_work_record로 꾸미지 마세요. "
                f"다른 주제를 조사하지 말고 산출물을 "
                f"{str(topic_dir / 'research.md')!r}에 저장하세요. 문서 상단에 "
                "`- status: READY` 또는 `- status: INSUFFICIENT`를 정확히 하나 "
                "기록하고, 핵심 공식 원문이나 완료 조건이 부족하면 반드시 "
                "INSUFFICIENT로 판정하세요."
            ),
        ),
        Stage(
            "Writer Agent",
            PROJECT_ROOT / "agents/writer.md",
            (
                common
                + content_guidance
                + f"입력은 {str(topic_dir / 'research.md')!r} 하나입니다. "
                f"문체 중복 확인용 입력은 {str(recent_style_context)!r}입니다. 이 파일은 "
                "최근 글의 도입·H2·마무리·structure_mode 비교에만 사용하고 사실, 경험, "
                "수치나 표현을 현재 글로 가져오지 마세요. 최근 글과 같은 도입 방식, H2 "
                "진행, 결론 형태가 겹치면 현재 problem_origin과 structure_mode에 맞게 "
                "전개를 바꾸되 억지로 다른 사람을 연기하지 마세요. "
                f"Harness가 분석 리포트 경로 {str(ANALYTICS_REPORT)!r}를 명시적으로 제공합니다. "
                "파일이 있으면 검색 의도·CTA 제안만 참고하고 사실 근거는 research.md를 우선하세요. "
                + quick_view_writer
                + f"기존 Guide를 적용해 {str(topic_dir / 'draft.md')!r}를 작성하세요."
            ),
        ),
    ]
    if humanize_experiment_enabled():
        stages.append(
            Stage(
                "Humanize Experiment Agent",
                PROJECT_ROOT / "guides/humanize-experiment.md",
                (
                    common
                    + f"원문은 {str(topic_dir / 'draft.md')!r}입니다. 원문을 덮어쓰지 말고, "
                    f"자연화 실험본만 {str(topic_dir / 'humanized-draft.md')!r}에 저장하세요. "
                    "의미·사실·수치·버전·코드·로그·링크·인용·frontmatter를 변경하지 말고, "
                    "문장 리듬과 번역투 등 문체만 최소 수정하세요. 변경이 과하면 실험본을 "
                    "원문과 동일하게 복사하고 이유를 summary에 기록하세요. "
                    f"실험 메타데이터는 {str(topic_dir / 'humanize-summary.md')!r}에 저장하세요."
                ),
            )
        )
    stages.extend([
        Stage(
            "Image Maker Agent",
            PROJECT_ROOT / "agents/image-maker.md",
            (
                common
                + f"입력 {str(topic_dir / 'draft.md')!r}만 사용해 이미지 제작과 "
                "해당 draft.md의 마커 치환을 완료하세요. 이미지 캡처 런타임은 "
                f"{str(PROJECT_ROOT / '.venv/bin/python3')!r} 및 "
                f"{str(PROJECT_ROOT / '.venv/bin/playwright')!r}를 절대 경로로 사용하세요."
            ),
        ),
        Stage(
            "Assembler Agent",
            PROJECT_ROOT / "agents/assembler.md",
            (
                common
                + f"입력 {str(topic_dir / 'draft.md')!r}와 "
                f"{str(topic_dir / 'images')!r}만 사용해 "
                f"{str(topic_dir / 'final.md')!r}와 "
                f"{str(topic_dir / 'final.html')!r}을 생성하고 검증하세요."
            ),
        ),
        Stage(
            "Reviewer Agent",
            None,
            (
                common
                + f"{str(topic_dir / 'final.md')!r}를 "
                f"{str(topic_dir / 'research.md')!r}, "
                f"{str(topic_dir / 'planner-context.json')!r}, "
                f"{str(recent_style_context)!r}, "
                f"{str(PROJECT_ROOT / 'agents/reviewer.md')!r}, "
                f"{str(PROJECT_ROOT / 'guides/style-guide.md')!r}, "
                f"{str(content_type_guide)!r}, "
                f"{str(PROJECT_ROOT / 'guides/seo-guide.md')!r}, "
                f"{str(PROJECT_ROOT / 'guides/monetization-guide.md')!r}, "
                f"{str(PROJECT_ROOT / 'guides/publisher-guide.md')!r} "
                "기준으로 검토하세요. reviewer.md의 주제 유형별 고유 가치와 "
                "실증 근거 검사를 포함한 모든 필수 검사를 적용하세요. "
                "recent-style-context.json은 사이트 차원의 반복 검사에만 사용하세요. 최근 "
                "글과 도입 방식, H2 진행, 마무리 형태가 실질적으로 반복됐거나 다른 글의 "
                "경험을 현재 글의 경험처럼 옮겼으면 REJECT하세요. structure_mode가 같다는 "
                "이유만으로 거절하지 말고 실제 문서 구조와 문장 흐름을 판단하세요. "
                + quick_view_review
                + (
                    f"Humanize Experiment Agent가 생성한 {str(topic_dir / 'humanized-draft.md')!r}와 "
                    f"{str(topic_dir / 'humanize-summary.md')!r}가 있으면 원문 {str(topic_dir / 'draft.md')!r}과 "
                    "나란히 비교하세요. 자연화본을 채택해도 되는지는 사실·의미·근거 보존을 먼저 판단하고, "
                    "비교 결과를 review.md에 기록하세요. 이 실험본 때문에 자동 승인하지 마세요. "
                )
                + "정책 문서는 읽기만 하고 주제 디렉터리로 "
                "복사하지 마세요. "
                f"원문 의미를 바꾸지 않는 {str(topic_dir / 'publish.md')!r}를 "
                "준비하되 WordPress "
                "제목이 H1이 되도록 본문은 H2부터 시작하고 필요한 Frontmatter를 "
                "추가하세요. images/thumbnail.png가 존재하므로 featured_image는 "
                "'./images/thumbnail.png', featured_image_alt는 대표 이미지 내용을 "
                "설명하는 구체적인 문장으로 반드시 설정하세요. "
                f"Frontmatter title은 {topic!r}와 정확히 일치해야 하고, "
                f"run_id는 {context.run_id!r}, topic_id는 {context.topic_id!r}, "
                f"source_id는 {context.source_id!r}, category는 "
                f"{context.category!r}, tags는 {list(context.tags)!r}, "
                "publish_mode는 'publish'여야 "
                f"합니다. publish.md의 SHA-256, run_id, topic_id와 APPROVED 또는 "
                f"REJECTED를 {str(topic_dir / 'review.md')!r}에 기록하세요. "
                "planner-context.json의 기존 WordPress 제목·Draft 중복 검사 결과를 "
                "검토 기록에 근거로 반영하세요. "
                "planner-context.json에 existing_post_id와 existing_slug가 있으면 기존 공개 글의 "
                "안전한 갱신 요청입니다. 두 값을 publish.md Frontmatter에 각각 정수 "
                "existing_post_id와 문자열 slug로 정확히 넣고, 기존 글 제목과 slug가 모두 "
                "일치하지 않으면 REJECT하세요. "
                "현재 research.md와 기존 공개 글 목록에 관련 내부 링크 후보가 없으면 그 사실을 기록하고 억지로 링크를 만들지 마세요. "
                "REJECTED이면 0이 아닌 종료 상태로 끝내세요."
            ),
        ),
        Stage(
            "Publisher Agent",
            PROJECT_ROOT / "agents/publisher-agent.md",
            (
                common
                + f"{str(topic_dir / 'review.md')!r}가 "
                f"{str(topic_dir / 'publish.md')!r}의 정확한 해시, run_id, "
                "topic_id를 APPROVED했는지 확인하세요. "
                "APPROVED했는지 확인하세요. 승인된 경우에만 다음과 동등한 명령으로 "
                f"공개 글을 생성하세요: .venv/bin/python scripts/publish_wordpress.py "
                f"{str(topic_dir / 'publish.md')!r} --reviewer-approved --audit-log "
                f"{str(topic_dir / 'publisher-audit.jsonl')!r} --review-file "
                f"{str(topic_dir / 'review.md')!r} --expected-run-id "
                f"{context.run_id!r} --expected-topic-id {context.topic_id!r} "
                f"--expected-source-id {context.source_id!r} --expected-category "
                f"{context.category!r} 명령을 실행하세요. "
                "publish_mode가 publish가 아니면 실패하세요. schedule 변경은 수행하지 마세요. "
                "기존 공개 글 갱신은 Reviewer가 승인한 existing_post_id와 slug가 publish.md에 있고 "
                "Publisher 스크립트가 기존 제목과 slug의 정확한 일치를 확인한 경우에만 허용합니다. "
                ".env는 Publisher 스크립트만 "
                "읽게 하고 값을 직접 열거나 출력하지 마세요."
            ),
        ),
    ])
    return stages


def read_humanize_experiment_state() -> dict[str, Any]:
    try:
        payload = json.loads(HUMANIZE_EXPERIMENT_STATE.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def humanize_experiment_enabled(*, now: datetime | None = None) -> bool:
    """Return whether the humanizer is effectively ON at the current time.

    The explicit ON/OFF contract takes precedence. Legacy ``remaining`` state
    remains supported so an in-flight bounded experiment is not broken.
    """
    payload = read_humanize_experiment_state()
    mode = str(payload.get("mode", "shadow")).strip().lower()
    if payload.get("enabled") is False or mode == "off":
        return False

    if payload.get("enabled") is True or mode == "on":
        enabled_until = str(payload.get("enabled_until", "")).strip()
        if not enabled_until:
            return True
        try:
            cutoff = datetime.fromisoformat(enabled_until)
        except ValueError:
            return False
        if cutoff.tzinfo is None:
            return False
        current = now or datetime.now().astimezone()
        if current.tzinfo is None:
            current = current.astimezone()
        return current <= cutoff

    try:
        return max(0, int(payload.get("remaining", 0))) > 0
    except (ValueError, TypeError):
        return False


def humanize_experiment_mode() -> str:
    return str(read_humanize_experiment_state().get("mode", "shadow")).lower()


def consume_humanize_experiment_slot(context: TopicContext) -> None:
    """Record a valid humanizer artifact and consume only legacy bounded slots."""
    payload = read_humanize_experiment_state()
    if not payload:
        raise PipelineError("Humanize 실험 상태 파일을 읽을 수 없습니다.")
    mode = str(payload.get("mode", "shadow")).strip().lower()
    if mode == "off" or payload.get("enabled") is False:
        return
    history = payload.get("history", [])
    if not isinstance(history, list):
        history = []
    history.append({"run_id": context.run_id, "topic_id": context.topic_id})
    payload["history"] = history
    if mode != "on" and payload.get("enabled") is not True:
        try:
            remaining = max(0, int(payload.get("remaining", 0)))
        except (ValueError, TypeError):
            remaining = 0
        if remaining <= 0:
            return
        payload["remaining"] = remaining - 1
    HUMANIZE_EXPERIMENT_STATE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def read_review_decision(context: TopicContext) -> str | None:
    """Read only the explicit Reviewer status, not incidental body mentions."""
    review_path = context.directory / "review.md"
    assert_owned_path(context, review_path)
    if not review_path.is_file():
        return None
    match = REVIEW_STATUS_PATTERN.search(review_path.read_text(encoding="utf-8"))
    if match is None:
        return None
    return next(value for value in match.groups() if value is not None).upper()


def review_repair_stages(
    context: TopicContext,
    *,
    attempt: int,
) -> list[Stage]:
    """Reuse the existing content agents for one bounded Reviewer repair pass."""
    review_path = context.directory / "review.md"
    repair_note = (
        f"\n\n이 단계는 Reviewer 거절 후 보정 시도 {attempt}/"
        f"{MAX_REVIEW_REPAIR_ATTEMPTS}입니다. 이전 검토 결과 "
        f"{str(review_path)!r}를 읽고 현재 Agent의 기존 책임 범위 안에서 거절 "
        "사유를 직접 해결하세요. 통과한 사실과 근거는 보존하고, 검증하지 않은 "
        "내용을 만들거나 Reviewer 기준을 우회하지 마세요. 명령·fixture·입력·출력·"
        "종료 상태가 필요한 경우 생략 부호, 의사 코드, '동일 함수' 같은 축약 표현 "
        "대신 재실행 가능한 실제 원문과 대응 증거를 남기세요. 현재 단계의 산출물을 "
        "덮어써서 다음 기존 Agent가 보정된 파일을 입력으로 사용하게 하세요."
    )
    return [
        Stage(stage.name, stage.agent_file, stage.prompt + repair_note)
        for stage in topic_stages(context)
        # The repair Writer edits the already-selected draft. Re-running the
        # humanizer would either be ignored by this repair loop or apply style
        # twice, so only the content and review agents participate here.
        if stage.name not in {"Humanize Experiment Agent", "Publisher Agent"}
    ]


def run_review_repair_cycle(
    codex: str,
    context: TopicContext,
    logger: logging.Logger,
    *,
    timeout_seconds: int,
) -> None:
    """Run one bounded repair cycle without weakening Reviewer approval."""
    if read_review_decision(context) != "REJECTED":
        return
    logger.info(
        "topic=%r run_id=%s topic_id=%s event=review_repair_start attempt=1",
        context.title,
        context.run_id,
        context.topic_id,
    )
    for stage in review_repair_stages(context, attempt=1):
        run_stage(
            codex,
            stage,
            logger,
            timeout_seconds=timeout_seconds,
            topic=context.title,
        )
        validate_stage_artifacts(context, stage.name)
    logger.info(
        "topic=%r run_id=%s topic_id=%s event=review_repair_end "
        "attempt=1 decision=%s",
        context.title,
        context.run_id,
        context.topic_id,
        read_review_decision(context) or "UNKNOWN",
    )


def validate_stage_artifacts(context: TopicContext, stage_name: str) -> None:
    required: dict[str, tuple[Path, ...]] = {
        "Research Agent": (context.directory / "research.md",),
        "Writer Agent": (context.directory / "draft.md",),
        "Humanize Experiment Agent": (
            context.directory / "draft.md",
            context.directory / "humanized-draft.md",
            context.directory / "humanize-summary.md",
        ),
        "Image Maker Agent": (
            context.directory / "draft.md",
            context.directory / "images/thumbnail.png",
        ),
        "Assembler Agent": (
            context.directory / "final.md",
            context.directory / "final.html",
        ),
        "Reviewer Agent": (
            context.directory / "publish.md",
            context.directory / "review.md",
        ),
        "Publisher Agent": (context.directory / "publisher-audit.jsonl",),
    }
    for path in required.get(stage_name, ()):
        assert_owned_path(context, path)
        if not path.is_file():
            raise PipelineError(
                f"{context.topic_id}: {stage_name} 필수 산출물 누락: {path}"
            )
    if stage_name == "Research Agent" and context.content_type == "build_log_operations":
        validate_build_log_research_contract(context)


def validate_research_readiness(context: TopicContext) -> None:
    """Stop insufficient research before Writer while supporting older artifacts."""
    path = context.directory / "research.md"
    assert_owned_path(context, path)
    text = path.read_text(encoding="utf-8")
    explicit = re.search(
        r"(?im)^\s*(?:[-*]\s*)?status\s*:\s*`?(READY|INSUFFICIENT)`?\s*$",
        text,
    )
    if explicit and explicit.group(1).upper() == "INSUFFICIENT":
        raise ContentQualityRejection(
            f"{context.topic_id}: Research가 INSUFFICIENT로 판정했습니다."
        )
    if explicit:
        return
    if re.search(
        r"(?im)^.*\bINSUFFICIENT\b.*(?:Writer|Publisher|넘길 수 없음).*$",
        text,
    ):
        raise ContentQualityRejection(
            f"{context.topic_id}: legacy Research가 INSUFFICIENT로 판정했습니다."
        )


def validate_build_log_research_contract(context: TopicContext) -> None:
    """Reject manufactured Build Logs before the Writer turns them into prose."""
    path = context.directory / "research.md"
    text = path.read_text(encoding="utf-8")
    section = re.search(
        r"(?ms)^## 작업 기록\s*$\n(.*?)(?=^##\s|\Z)",
        text,
    )
    if section is None:
        raise PipelineError(f"{context.topic_id}: Build Log 작업 기록이 없습니다.")
    fields = {
        key: value.strip().strip("`").strip()
        for key, value in re.findall(
            r"(?m)^-\s+([a-z_]+):\s*(.*?)\s*$",
            section.group(1),
        )
    }
    required_fields = {
        "evidence_origin",
        "work_trigger",
        "actual_sequence",
        "friction_or_surprise",
        "decision_log",
        "unfinished_edge",
    }
    missing = sorted(required_fields - fields.keys())
    if missing:
        raise PipelineError(
            f"{context.topic_id}: Build Log 작업 기록 필드 누락: "
            + ", ".join(missing)
        )
    if fields["evidence_origin"] != "existing_work_record":
        raise PipelineError(
            f"{context.topic_id}: Build Log는 existing_work_record 근거만 허용합니다."
        )
    placeholders = {"", "없음", "해당 없음", "none", "n/a", "insufficient"}
    empty = sorted(
        key
        for key in required_fields - {"evidence_origin"}
        if fields[key].strip().lower() in placeholders
    )
    if empty:
        raise PipelineError(
            f"{context.topic_id}: Build Log 실제 작업 흔적 부족: " + ", ".join(empty)
        )


def validate_publish_contract(context: TopicContext) -> str:
    publish_path = context.directory / "publish.md"
    review_path = context.directory / "review.md"
    assert_owned_path(context, publish_path)
    assert_owned_path(context, review_path)
    try:
        document = load_document(publish_path)
    except FrontmatterError as exc:
        raise PipelineError(f"{context.topic_id}: publish.md Frontmatter 오류") from exc

    metadata = document.metadata
    expected = {
        "title": context.title,
        "run_id": context.run_id,
        "topic_id": context.topic_id,
        "source_id": context.source_id,
        "publish_mode": "publish",
        "category": context.category,
    }
    for field, expected_value in expected.items():
        actual = metadata.get(field)
        if actual != expected_value:
            raise PipelineError(
                f"{context.topic_id}: publish.md {field} 불일치 "
                f"(expected={expected_value!r}, actual={actual!r})"
            )
    raw_tags = metadata.get("tags")
    actual_tags = tuple(
        dict.fromkeys(
            str(tag).strip()
            for tag in (raw_tags if isinstance(raw_tags, list) else [])
            if str(tag).strip()
        )
    )
    if actual_tags != context.tags:
        raise PipelineError(
            f"{context.topic_id}: publish.md tags 불일치 "
            f"(expected={list(context.tags)!r}, actual={list(actual_tags)!r})"
        )
    if metadata.get("featured_image") != "./images/thumbnail.png":
        raise PipelineError(
            f"{context.topic_id}: publish.md featured_image 누락 또는 경로 불일치"
        )
    featured_alt = metadata.get("featured_image_alt")
    if not isinstance(featured_alt, str) or not featured_alt.strip():
        raise PipelineError(f"{context.topic_id}: publish.md featured_image_alt 누락")
    thumbnail = context.directory / "images/thumbnail.png"
    if not thumbnail.is_file():
        raise PipelineError(f"{context.topic_id}: 대표 이미지 파일 누락: {thumbnail}")

    decision = read_review_decision(context)
    if decision == "REJECTED":
        raise ContentQualityRejection(
            f"{context.topic_id}: Reviewer가 발행을 거절했습니다."
        )
    if decision != "APPROVED":
        raise PipelineError(
            f"{context.topic_id}: Reviewer의 명시적 APPROVED 상태가 없습니다."
        )

    summaries = list(re.finditer(
        r"(?ms)^## 20초 핵심 요약\s*$\n(.*?)(?=^##\s|\Z)",
        document.markdown,
    ))
    if len(summaries) != 1:
        raise PipelineError(
            f"{context.topic_id}: `## 20초 핵심 요약`은 정확히 한 번이어야 합니다. "
            f"(actual={len(summaries)})"
        )
    summary = summaries[0]
    missing_summary_fields = [
        label
        for label in ("무엇", "왜", "어떻게")
        if not re.search(rf"(?m)(?:^|[*_\-\s]){label}(?:[*_\s]*[:：]|[*_]+)", summary.group(1))
    ]
    if missing_summary_fields:
        raise PipelineError(
            f"{context.topic_id}: 20초 핵심 요약 필드 누락: "
            + ", ".join(missing_summary_fields)
        )
    forbidden_summary_phrases = (
        "문제 또는 판단 기준을 놓치지 않기 위해서",
        "순서로 확인합니다",
    )
    found_forbidden = [
        phrase for phrase in forbidden_summary_phrases if phrase in summary.group(1)
    ]
    if found_forbidden:
        raise PipelineError(
            f"{context.topic_id}: 20초 핵심 요약 자동 생성 문구 금지: "
            + ", ".join(found_forbidden)
        )

    digest = hashlib.sha256(publish_path.read_bytes()).hexdigest()
    review = review_path.read_text(encoding="utf-8")
    required_tokens = (context.run_id, context.topic_id, digest)
    if not all(token in review for token in required_tokens):
        raise PipelineError(
            f"{context.topic_id}: Reviewer 승인·해시·run_id·topic_id 계약 불일치"
        )
    return digest


def read_publish_result(context: TopicContext) -> dict[str, Any]:
    audit_path = context.directory / "publisher-audit.jsonl"
    assert_owned_path(context, audit_path)
    if not audit_path.is_file():
        raise PipelineError(f"{context.topic_id}: Publisher 감사 로그가 없습니다.")
    events: list[dict[str, Any]] = []
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            event.get("event") in {"post_published", "post_updated"}
            and event.get("status") == "Success"
        ):
            events.append(event)
    if not events:
        raise PipelineError(
            f"{context.topic_id}: 성공한 Publish 또는 Update 기록이 없습니다."
        )
    event = events[-1]
    post_id = int(event["post_id"])
    return {
        "topic": context.title,
        "run_id": context.run_id,
        "topic_id": context.topic_id,
        "post_id": post_id,
        "url": event.get("published_url"),
        "image_count": int(event.get("featured_media_id") is not None)
        + len(event.get("body_media_ids") or []),
    }


def has_successful_publish(context: TopicContext) -> bool:
    try:
        read_publish_result(context)
    except PipelineError:
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hunt News TOP2 daily pipeline")
    parser.add_argument(
        "--keywords",
        default="",
        help="Topic Planner에 전달할 쉼표 구분 추가 키워드",
    )
    parser.add_argument(
        "--whereispost-observation",
        type=Path,
        help=(
            "공식 Keyword Master 화면에서 운영자가 직접 확인한 JSON. "
            "검증된 동일 키워드의 수요 근거로만 Planner에 전달"
        ),
    )
    parser.add_argument(
        "--use-google-trends-cache",
        action="store_true",
        help=(
            "시간별 Google Trends 한국 RSS 캐시를 주력 시의성 신호로 사용. "
            "캐시가 없거나 올바르지 않아도 파이프라인은 계속 진행"
        ),
    )
    parser.add_argument(
        "--use-editorial-source-cache",
        action="store_true",
        help="매시간 수집한 기술 뉴스 소스 캐시를 후보 발견과 출처 교차 확인에 사용",
    )
    parser.add_argument(
        "--use-whereispost-cache",
        action="store_true",
        help=(
            "Whereispost 캐시를 보조 수요 신호로 사용하고 실시간 조회는 금지. "
            "캐시가 없거나 올바르지 않아도 파이프라인은 계속 진행"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Agent별 제한 시간(초, 기본 3600)",
    )
    parser.add_argument(
        "--topic-workers",
        type=int,
        choices=(1, 2),
        default=2,
        help="TOP2 준비 단계를 병렬 처리할 작업자 수(기본 2)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "외부 호출과 발행 없이 Topic Planner 계약, TOP2 추출 및 "
            "Codex 명령 생성을 검증"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        choices=(1, 2),
        default=2,
        help="선정된 TOP2 중 실행할 주제 수(기본 2)",
    )
    parser.add_argument(
        "--start-rank",
        type=int,
        choices=(1, 2),
        default=1,
        help="TOP2 중 실행을 시작할 순위(기본 1)",
    )
    parser.add_argument(
        "--resume-run-id",
        help="기존 Editor 실행의 topics.md를 사용해 남은 순위만 안전하게 재개",
    )
    return parser


def dry_run_topics() -> str:
    candidates: list[str] = []
    number = 0
    for category in sorted(ACTIVE_EDITOR_CATEGORIES):
        for index in range(1, 8):
            number += 1
            title = f"{category} Dry Run 후보 {index}"
            candidates.append(
                f"## {number}. {title}\n\n"
                f"- title: {title}\n"
                f"- category: {category}\n"
                f"- content_type: {LEGACY_CONTENT_TYPE_BY_CATEGORY[category]}\n"
                "- tags: DryRun, Pipeline, HuntLab\n"
                "- score: 72/90\n"
                "- score_breakdown: 최신성 8; 검색 수요 8; 공식 출처 8; "
                "Evergreen 8; HuntLab 적합성 8; 기술적 깊이 8; 독창성 8; "
                "최근 작성 여부 8; 카테고리 균형 8\n"
                "- reason: 파서 검증\n"
                "- evergreen: 중간\n"
                f"- primary_keyword: {title}\n"
                "- demand_signal_source: dry-run fixture\n"
                "- whereispost_status: unavailable\n"
                "- whereispost_metrics: cache unavailable\n"
                "- whereispost_total_searches: 0\n"
                "- affected_reader: 자동화 계약을 확인하는 운영자\n"
                "- life_impact: 검증 실패를 발행 전에 발견\n"
                "- effective_date: 즉시\n"
                "- reader_action: 드라이런 결과 확인\n"
                "- observed_problem_phrase: 자동화 계약 검증\n"
                "- user_action: 드라이런 결과 확인\n"
                "- search_intent: 자동화 검증\n"
                "- research_focus: 공식 자료 확인\n"
                "- recommended_images: 대표 이미지 1개\n"
                "- duplicate_check: 중복 없음\n"
                "- internal_link_candidates: 없음\n"
                "- topic_cluster: Dry Run\n"
                "- pillar_candidate: 없음\n"
                "- problem_origin: real_project\n"
                "- editorial_thesis: 드라이런은 편집 계약을 검증해야 한다\n"
                "- chosen_focus: 파서와 격리 경계\n"
                "- rejected_angle: 기능 소개는 검증 목적과 달라 제외\n"
                "- structure_mode: decision_memo\n"
                "- sources: dry-run"
            )
    top10_items = candidates[:9] + [candidates[10]]
    top10 = [item.splitlines()[0].split(". ", 1)[1] for item in top10_items]
    return (
        "# Topic Candidates\n\n"
        + "\n\n".join(candidates)
        + "\n\n"
        "## TOP10\n\n"
        + "\n".join(f"{index}. {title}" for index, title in enumerate(top10, 1))
        + "\n\n"
        "## TOP2\n\n"
        f"1. {top10[0]}\n"
        f"2. {top10[-1]}\n"
    )


def validate_dry_run(
    codex: str,
    logger: logging.Logger,
    keywords: str,
    limit: int,
    start_rank: int,
) -> int:
    if start_rank + limit - 1 > 2:
        raise PipelineError("dry-run 실행 범위가 TOP2를 벗어났습니다.")
    run_id = "dry-run-0000000000"
    topics_path = RUNS_DIR / run_id / "topics.md"
    planner = planner_stage(keywords, run_id, topics_path)
    planner_command = build_codex_command(codex, stage_instruction(planner))
    logger.info(
        "dry_run event=command agent=%s command=%s",
        planner.name,
        shlex.join(planner_command[:-1] + ["<PROMPT>"]),
    )

    synthetic_path = LOG_DIR / ".topics-dry-run.md"
    try:
        synthetic_path.write_text(dry_run_topics(), encoding="utf-8")
        document = parse_topic_plan_document(synthetic_path)
        plans = document["top2"]
        with tempfile.TemporaryDirectory(prefix="hunt-news-shadow-dry-run-") as temporary:
            shadow_path = run_news_worthiness_shadow(
                Path(temporary), document, logger
            )
            if shadow_path is None or not shadow_path.is_file():
                raise PipelineError("Shadow ranking dry-run 산출물을 만들지 못했습니다.")
    finally:
        synthetic_path.unlink(missing_ok=True)
    logger.info("dry_run event=top2 topics=%r", [plan["title"] for plan in plans])

    for plan in plans[start_rank - 1 : start_rank - 1 + limit]:
        topic = plan["title"]
        context = make_topic_context(
            run_id,
            topic,
            category=plan["category"],
            content_type=plan["content_type"],
            tags=plan["tags"],
            reason=plan["reason"],
            research_focus=plan["research_focus"],
        )
        logger.info(
            "dry_run topic=%r run_id=%s topic_id=%s event=start",
            topic,
            context.run_id,
            context.topic_id,
        )
        for stage in topic_stages(context):
            command = build_codex_command(codex, stage_instruction(stage))
            logger.info(
                "dry_run topic=%r agent=%s event=command command=%s",
                topic,
                stage.name,
                shlex.join(command[:-1] + ["<PROMPT>"]),
            )
        logger.info("dry_run topic=%r event=end", topic)
    logger.info("dry_run event=end external_calls=0 publishes=0")
    return 0


def read_whereispost_observation(
    path: Path | None,
    *,
    now: datetime | None = None,
    max_age_days: int = DEFAULT_WHEREISPOST_MAX_AGE_DAYS,
) -> str:
    if path is None:
        return ""
    try:
        payload = load_whereispost_shadow(path)
    except SearchSignalError as exc:
        raise PipelineError(f"Whereispost 관측 파일이 올바르지 않습니다: {exc}") from exc
    try:
        checked_at = datetime.fromisoformat(str(payload["checked_at"]))
    except (KeyError, ValueError) as exc:
        raise PipelineError("Whereispost checked_at 형식이 올바르지 않습니다.") from exc
    if checked_at.tzinfo is None:
        raise PipelineError("Whereispost checked_at에 시간대가 없습니다.")
    current = now or datetime.now(UTC)
    age = current.astimezone(UTC) - checked_at.astimezone(UTC)
    if age < -timedelta(minutes=5) or age > timedelta(days=max_age_days):
        raise PipelineError(
            f"Whereispost 관측 캐시가 허용 범위({max_age_days}일)를 벗어났습니다."
        )
    rows = [row for row in payload.get("rows", []) if not row.get("consumed", False)]
    if not rows:
        raise PipelineError("Whereispost 관측 파일에 rows가 없습니다.")
    for index, row in enumerate(rows, 1):
        if "total_searches" not in row or "competition_ratio" not in row:
            raise PipelineError(
                f"Whereispost 관측 행 {index}에 total_searches 또는 "
                "competition_ratio가 없습니다."
            )
    return json.dumps(
        {"checked_at": payload["checked_at"], "rows": rows},
        ensure_ascii=False,
        sort_keys=True,
    )


def read_google_trends_observation(path: Path | None) -> str:
    try:
        payload = load_google_trends_cache(path)
    except SearchSignalError as exc:
        raise PipelineError(f"Google Trends 캐시가 올바르지 않습니다: {exc}") from exc
    rows = payload.get("rows", [])
    if not rows:
        raise PipelineError("Google Trends 캐시에 rows가 없습니다.")
    try:
        checked_at = datetime.fromisoformat(str(payload["checked_at"]))
    except (KeyError, ValueError) as exc:
        raise PipelineError("Google Trends checked_at 형식이 올바르지 않습니다.") from exc
    if checked_at.tzinfo is None:
        raise PipelineError("Google Trends checked_at에 시간대가 없습니다.")
    age_seconds = (datetime.now(UTC) - checked_at.astimezone(UTC)).total_seconds()
    if age_seconds < -300 or age_seconds > 6 * 60 * 60:
        raise PipelineError("Google Trends 캐시가 6시간보다 오래되었습니다.")
    recent_rows = sorted(
        rows,
        key=lambda row: (
            float(row.get("discovery_score", 0.0)),
            str(row.get("last_seen_at", "")),
            int(row.get("approx_traffic", 0)),
        ),
        reverse=True,
    )[:60]
    return json.dumps(
        {
            "provider": payload["provider"],
            "contract_version": payload.get("contract_version", "legacy"),
            "source_snapshot_hash": payload.get("source_snapshot_hash", ""),
            "geo": payload["geo"],
            "checked_at": payload["checked_at"],
            "rows": recent_rows,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def read_editorial_source_observation(path: Path | None) -> str:
    try:
        payload = load_editorial_source_cache(path)
    except SearchSignalError as exc:
        raise PipelineError(f"기술 뉴스 소스 캐시가 올바르지 않습니다: {exc}") from exc
    try:
        checked_at = datetime.fromisoformat(str(payload["checked_at"]))
    except (KeyError, ValueError) as exc:
        raise PipelineError("기술 뉴스 소스 checked_at 형식이 올바르지 않습니다.") from exc
    if checked_at.tzinfo is None:
        raise PipelineError("기술 뉴스 소스 checked_at에 시간대가 없습니다.")
    age = datetime.now(UTC) - checked_at.astimezone(UTC)
    if age < -timedelta(minutes=5) or age > timedelta(hours=6):
        raise PipelineError("기술 뉴스 소스 캐시가 6시간보다 오래되었습니다.")
    rows = sorted(payload.get("rows", []), key=lambda row: str(row.get("published_at", "")), reverse=True)[:120]
    if not rows:
        raise PipelineError("기술 뉴스 소스 캐시에 rows가 없습니다.")
    return json.dumps({
        "provider": payload["provider"],
        "contract_version": payload["contract_version"],
        "source_snapshot_hash": payload["source_snapshot_hash"],
        "checked_at": payload["checked_at"],
        "rows": rows,
    }, ensure_ascii=False, sort_keys=True)


def read_public_category_distribution(base_url: str, *, timeout: float = 10.0) -> str:
    """Read active public category counts for a bounded portfolio-balance signal."""
    endpoint = urllib.parse.urljoin(
        base_url.rstrip("/") + "/",
        "wp-json/wp/v2/categories?per_page=100&hide_empty=false&_fields=slug,count",
    )
    request = urllib.request.Request(
        endpoint,
        headers={"User-Agent": "HuntNewsPlanner/1.0 (+https://huntlab.app/)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            rows = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    counts: dict[str, int] = {}
    for row in rows if isinstance(rows, list) else []:
        slug = str(row.get("slug", "")) if isinstance(row, dict) else ""
        if slug not in ACTIVE_CATEGORY_SLUGS:
            continue
        try:
            counts[ACTIVE_CATEGORY_SLUGS[slug]] = max(int(row.get("count", 0)), 0)
        except (TypeError, ValueError):
            continue
    if not counts:
        return ""
    return json.dumps(
        {"total": sum(counts.values()), "counts": counts},
        ensure_ascii=False,
        sort_keys=True,
    )


def planner_stage(
    keywords: str,
    run_id: str,
    topics_path: Path,
    whereispost_observation: str = "",
    whereispost_cache_mode: bool = False,
    google_trends_observation: str = "",
    google_trends_cache_mode: bool = False,
    editorial_source_observation: str = "",
    editorial_source_cache_mode: bool = False,
    category_distribution: str = "",
) -> Stage:
    return Stage(
        "Topic Planner Agent",
        PROJECT_ROOT / "agents/topic-planner-agent.md",
        (
            f"현재 날짜는 {date.today().isoformat()}입니다. "
            f"run_id는 {run_id!r}입니다. "
            f"추가 키워드는 {keywords.strip() or '없음'}입니다. "
            + (
                "추가 키워드가 있으면 그 키워드를 제목에 포함한 후보를 최소 1개 만들고, "
                "검색 의도와 근거가 충족되면 TOP2에 우선 배정하세요. 키워드가 시스템 설계·아키텍처라면 "
                "category=System Architecture, content_type=system_design_case를 사용하세요. "
                if keywords.strip()
                else ""
            )
            + (
                "Harness가 매시간 수집한 기술 뉴스 소스 캐시를 제공합니다: "
                f"{editorial_source_observation}. 이 목록에서 후보를 발견하고 동일 사건의 독립 출처를 "
                "찾으세요. 활성 카테고리는 AI/ML 핵심, 개발 트렌드, AI 공식 블로그, 국내 IT, 국내 시사 "
                "다섯 개뿐입니다. 국내 시사는 AI·개발·클라우드·반도체·플랫폼·기술 정책과 직접 연결되는 "
                "기사만 후보로 사용하세요. RSS 제목은 발견 근거일 뿐이므로 공식 발표나 원문을 다시 확인하세요. "
                if editorial_source_observation
                else (
                    "기술 뉴스 소스 캐시가 없으면 출처를 추정하지 말고 Google Trends와 공식 원문으로 계속하세요. "
                    if editorial_source_cache_mode else ""
                )
            )
            + (
                "이 실행의 주력 시의성 신호는 매시간 누적한 Google Trends 한국 RSS 캐시입니다: "
                f"{google_trends_observation}. topic, approx_traffic, published_at, first_seen_at, "
                "last_seen_at과 관련 기사 목록을 후보 발견과 급상승 강도 판단에 사용하세요. RSS 기사와 "
                "검색량 표시는 사실 근거가 아니므로 그대로 인용하지 말고, TOP10 전에 핵심 사실을 공식 "
                "원문 하나 또는 서로 독립적인 신뢰 출처 두 개 이상으로 다시 확인하세요. 출처가 부족한 "
                "연예인 이름, 단순 사건명, 종목 코드는 검색량이 높아도 제외하세요. "
                if google_trends_observation
                else (
                    "Google Trends 캐시가 없으면 실시간 검색량을 추정하지 말고 다른 공식 변화와 Search "
                    "Console 관측으로 계속 진행하세요. "
                    if google_trends_cache_mode
                    else ""
                )
            )
            + (
                "Harness가 공식 Keyword Master 화면에서 운영자가 직접 확인한 관측값을 "
                f"제공합니다: {whereispost_observation}. 이 값은 같은 primary_keyword 후보의 "
                "whereispost_status를 verified로 판정하는 수요 근거로만 사용하세요. 다른 키워드로 "
                "확장하거나 정책·가격·시점의 사실 근거로 사용하지 말고, TOP2 선정은 중복 검사와 "
                "공식 원문 검증을 별도로 통과해야 합니다. "
                if whereispost_observation
                else ""
            )
            + (
                "이 실행은 백그라운드 수집기가 누적한 30일 평균 수요 캐시만 보조 신호로 소비합니다. "
                "Whereispost 웹사이트를 열거나 실시간으로 다시 조회하지 마세요. 캐시에 있는 정확한 "
                "keyword 행만 verified로 사용할 수 있고 related_keywords는 별도 조회 없이 verified로 "
                "확장할 수 없습니다. 캐시에 없는 후보는 whereispost_status=unavailable로 기록하되, "
                "그 이유만으로 제외하지 마세요. 캐시는 검색 수요 점수의 참고값일 뿐이며 공개 글·Draft 중복, "
                "공식 원문, 시의성과 생활 영향이 더 강한 후보를 TOP2로 선정하세요. "
                if whereispost_cache_mode
                else ""
            )
            + "Hunt News는 매일 AI와 개발 기술 변화를 골라 개발자가 지금 이해하고 적용할 행동까지 정리하는 기술 뉴스 브리핑입니다. "
            + (
                "Harness가 현재 공개 카테고리 분포를 읽기 전용으로 제공합니다: "
                f"{category_distribution}. 이 값은 후보 품질을 대체하는 할당량이 아니라 카테고리 균형 "
                "점수의 관측 근거입니다. 한 카테고리가 전체의 60%를 넘으면 그 카테고리에는 균형 가산점을 "
                "주지 말고, 공식 근거·검색 수요·실무 영향·비중복 조건을 모두 통과한 저대표 카테고리 후보에만 "
                "카테고리 균형 점수를 우대하세요. 약한 후보를 비율 때문에 TOP2에 넣지는 마세요. "
                if category_distribution
                else "공개 카테고리 분포를 읽지 못하면 비율을 추정하지 말고 기존 글의 최근 편중만 정성적으로 평가하세요. "
            )
            + "기존 WordPress 게시글과 Draft, output의 기존 글을 확인한 뒤 AI/ML 핵심, 개발 트렌드, "
            "AI 공식 블로그, 국내 IT, 국내 시사만 활성 카테고리로 사용하세요. 신규 후보는 검색 의도에 따라 "
            "tutorial_troubleshooting, concept_architecture, ai_ml_experiment, build_log_operations, "
            "current_affairs_policy 중 가장 적합한 content_type을 사용하세요. "
            "후보는 발표명이나 보도자료 제목이 아니라 독자가 검색하는 질문에서 시작해야 합니다. "
            "무엇이 바뀌었는지, 어떤 개발자·팀에 영향이 있는지, 지금 적용할지 관찰할지와 확인할 원문을 "
            "한 제목과 research_focus로 연결하세요. 제품 발표명을 그대로 옮기지 말고 호환성, 비용, 보안, "
            "성능, 운영 방식 중 실제 의사결정이 달라지는 지점을 드러내세요. 숫자와 시점은 공식 원문이나 "
            "재현 가능한 관측으로 확인할 수 있을 때만 사용하세요. 국내 시사는 기술 정책과 산업 운영에 직접 "
            "연결된 경우에만 다루며 사실, 당사자 주장, 전망을 구분하세요. 기존 글과 검색 의도가 겹치면 신규 증산보다 Refresh를 "
            "우선하세요. Build Log는 실제 작업 기록·운영 변경·실패 로그가 있을 때만 사용하며 오늘 실행을 "
            "위해 새로 만든 테스트나 Search Console 관측만으로 선정할 수 없습니다. "
            "IT의 ML 후보는 Isolation Forest 한 알고리즘에 편중하지 말고 분류·회귀·군집화·차원 축소·추천·"
            "시계열·신경망을 폭넓게 검토해 문제 정의, 평가지표, 베이스라인과 대안을 비교하고 실제 적용 판단을 "
            "남기세요. ML적 사고력은 후보 품질 기준이지만 TOP2 의무 할당은 두지 말고, 중복 주제는 후속 관점 "
            "또는 Refresh로 처리하세요. 확인하지 못한 장애를 창작하지 말고 실제 관측 문구만 사용하세요. "
            "Velog 공개 트렌딩(https://velog.io/)은 "
            "한국 개발자 관심사의 보조 신호로만 사용하세요. 제목이나 구성을 복제하지 말고 같은 주제 흐름이 "
            "2회 이상 관측될 때 검색 수요 점수에 최대 1점만 반영하며, 공식 1차 자료와 Search Console 관측값을 "
            "대체할 수 없습니다. Velog 인기만으로 TOP2로 선정해 실제 발행하지 말고, 접근할 수 없으면 Velog "
            "신호 없음으로 계속 진행하세요. "
            "검색 수요 점수는 Google Trends의 최근성·급상승 강도를 우선 반영하고, Analytics 리포트의 "
            "실제 Search Console 검색어와 같은 검색 의도 또는 인접 주제로 연결되면 최대 1점만 가산하세요. "
            "각 TOP2의 demand_signal_source에는 사용한 기술 뉴스 소스 snapshot, Trends 관측 시각과 Search "
            "Console 연결 여부를 구분해 기록하세요. "
            "모든 후보의 google_trends_approx_traffic에는 후보와 직접 일치하는 Trends 행의 approx_traffic을 "
            "쉼표 없는 0 이상의 정수로 기록하고, 일치 관측이 없으면 추정하지 말고 0으로 기록하세요. "
            "TOP2에는 demand_signal_source, observed_problem_phrase, user_action과 함께 "
            "problem_origin(real_project, public_codebase, observed_search_question, controlled_lab, official_change 중 하나), "
            "editorial_thesis(글 전체가 증명할 한 문장), chosen_focus, rejected_angle(넣지 않을 관점과 이유), "
            "structure_mode(problem_first, decision_memo, experiment_diary, code_walkthrough, field_note, "
            "impact_timeline, household_case, before_after, eligibility_check 중 하나)를 기록하세요. "
            "동등한 후보라면 실제 프로젝트·공개 코드·관측 질문에서 출발한 후보를 통제 실험보다 우선하고, "
            "controlled_lab은 실제 선택을 바꾸는 질문에 답할 때만 선정하세요. "
            f"카테고리별 수량을 강제하지 말고 전체 후보 35개 이상, TOP10과 TOP2를 {str(topics_path)!r}에 "
            "작성하세요. 최종 TOP2는 각 후보의 primary_keyword를 제목에 그대로 포함해야 합니다. "
            f"Harness가 분석 리포트 경로 {str(ANALYTICS_REPORT)!r}를 명시적으로 제공합니다. "
            "파일이 있으면 검색어·CTR·조회수 관측값, Refresh 후보와 Content Gap 제안만 참고하고, 데이터가 없으면 "
            "추측하지 마세요. 리포트가 COMPLETE이고 실제 비브랜드 검색어 또는 초기 성공 글이 있으면, "
            "현재도 유효한 문제·공식 또는 직접 검증 근거·비중복 검색 의도를 확인해 강한 후보로 평가하되 "
            "TOP2 자리를 미리 배정하지 마세요. 적합한 후보가 없으면 할당량을 채우기 위해 억지로 만들지 "
            "말고 전체 후보 중 품질이 가장 높은 주제를 선택하세요. "
            "성공 글의 제목이나 본문 구성을 복제하지 말고 검색 의도와 문제 유형만 후속 후보 근거로 사용하세요. "
            "TOP2는 카테고리 할당량으로 채우지 말고 캐시 수요 신호를 참고하되 실무 영향의 구체성, 공식 원문, "
            "비중복 검색 의도와 설명 가능성이 가장 강한 후보를 고르세요. 근거가 부족하면 두 편을 "
            "억지로 채우지 말고 Planner를 실패시키세요. "
            "후보마다 기존 공개 글과 검색 의도가 겹치는지 검사하고 "
            "internal_link_candidates, topic_cluster, pillar_candidate를 기록하세요. "
            "output의 다른 파일은 수정하지 마세요. "
            "글 작성, 본문 리서치, 이미지 생성, Publisher 호출은 하지 마세요. "
            "Planner의 유일한 파일 변경은 위 topics.md 생성입니다. git diff, 테스트 파일, "
            "코드 파일, 다른 output 실행 디렉터리는 수정하지 마세요. 파일을 쓰기 전에 긴 설명을 "
            "출력하지 말고, 후보를 만든 즉시 topics.md를 저장한 뒤 필드와 TOP2를 다시 검증하세요."
        ),
    )


def daily_briefing_stage(
    run_id: str,
    topics_path: Path,
    analysis_path: Path,
    editorial_source_path: Path,
    previous_briefing_path: Path | None = None,
    previous_snapshot_hash: str = "",
) -> Stage:
    if previous_briefing_path:
        retrospective_prompt = (
            f" 이전 보고서 스냅샷 {str(previous_briefing_path)!r}의 core_signals 3개를 "
            "현재 수집 자료와 필요한 공식 원문으로 각각 재검증하세요. retrospective.status는 "
            "available, previous_generated_at은 스냅샷 값, previous_snapshot_hash는 "
            f"{previous_snapshot_hash!r}로 기록하고 items는 이전 순서 1..3을 유지하세요. "
            "판정은 confirmed, changed, unresolved 중 하나이며 새 evidence URL 없이 확정하지 마세요."
        )
    else:
        retrospective_prompt = (
            " 비교할 이전 보고서가 없으므로 retrospective.status는 baseline, "
            "previous_generated_at과 previous_snapshot_hash는 빈 문자열, items는 빈 배열로 기록하세요."
        )
    return Stage(
        "Daily Briefing Analyst",
        PROJECT_ROOT / "agents/daily-briefing-agent.md",
        (
            f"현재 run_id는 {run_id!r}입니다. "
            f"기술 뉴스 cache {str(editorial_source_path)!r}와 Planner 후보 {str(topics_path)!r}를 "
            "읽고 중복 사건을 합친 뒤, 가이드의 핵심 신호·키워드 방향·영향 매트릭스·"
            "액션 타임라인·종합 인사이트·필독 5를 생성하세요. "
            + retrospective_prompt
            + " "
            "headline은 사건 나열이 아니라 오늘 채택할 것, 보류할 것 또는 먼저 막을 위험을 "
            "분명히 말하는 편집 판단 한 문장으로 작성하세요. summary는 그 판단의 이유와 우선순위를 "
            "한 문단으로만 설명하세요. core_signals, insight_cards, themes, developer_insights에서 같은 "
            "사실·결론·행동 문장을 되풀이하지 말고 각 항목이 서로 다른 질문에 답하게 하세요. "
            "같은 원문을 여러 항목의 대표 근거로 재사용해야 한다면 새 판단이 추가되는 경우로 제한하세요. "
            f"결과 JSON은 {str(analysis_path)!r}에만 저장하세요. "
            "원문 기사 나열을 보고서 본문으로 대체하지 말고 각 판단에 근거 URL과 구체적인 "
            "행동을 연결하세요. WordPress와 다른 외부 시스템은 변경하지 마세요."
        ),
    )


def freeze_previous_daily_briefing(
    *, run_id: str, run_directory: Path
) -> tuple[Path | None, str, list[str], list[dict[str, Any]]]:
    """Freeze the latest valid prior analysis as the retrospective input."""
    try:
        current_report_date = (
            datetime.strptime(run_id[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            + timedelta(hours=9)
        ).date()
    except ValueError:
        return None, "", [], []
    previous_report_date = current_report_date - timedelta(days=1)

    def is_previous_report(path: Path) -> bool:
        try:
            candidate_date = (
                datetime.strptime(path.parent.name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
                + timedelta(hours=9)
            ).date()
        except ValueError:
            return False
        return candidate_date == previous_report_date

    candidates = sorted(
        (
            path
            for path in RUNS_DIR.glob("*/daily-briefing-analysis.json")
            if path.parent != run_directory and is_previous_report(path)
        ),
        key=lambda path: path.parent.name,
        reverse=True,
    )
    for candidate_path in candidates:
        try:
            previous = load_daily_briefing(candidate_path)
        except DailyBriefingError:
            continue
        snapshot = {
            "contract_version": "daily-briefing-retrospective-input.v1",
            "previous_run_id": candidate_path.parent.name,
            "generated_at": previous["generated_at"],
            "headline": previous["headline"],
            "core_signals": previous["core_signals"],
        }
        destination = run_directory / "previous-daily-briefing.json"
        atomic_write_manifest(destination, snapshot)
        snapshot_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
        labels = [str(row["label"]) for row in snapshot["core_signals"]]
        return destination, snapshot_hash, labels, list(snapshot["core_signals"])
    return None, "", [], []


def run_daily_briefing_analysis(
    codex: str,
    *,
    run_id: str,
    run_directory: Path,
    topics_path: Path,
    logger: logging.Logger,
    timeout_seconds: int,
) -> Path:
    """Generate the required daily briefing analysis before publication."""
    analysis_path = run_directory / "daily-briefing-analysis.json"
    source_snapshot_path = run_directory / "editorial-sources-snapshot.json"
    try:
        previous_path, previous_hash, previous_labels, previous_signals = freeze_previous_daily_briefing(
            run_id=run_id,
            run_directory=run_directory,
        )
        if not source_snapshot_path.is_file():
            source_payload = json.loads(DEFAULT_EDITORIAL_SOURCE_CACHE.read_text(encoding="utf-8"))
            atomic_write_manifest(source_snapshot_path, source_payload)
        source_cache = load_editorial_source_cache(source_snapshot_path)
        source_hash = str(source_cache.get("source_snapshot_hash", ""))
        if not source_cache.get("rows") or not source_hash:
            raise DailyBriefingError("editorial source cache unavailable")
        if analysis_path.is_file():
            try:
                payload = load_daily_briefing(
                    analysis_path,
                    source_snapshot_hash=source_hash,
                    previous_snapshot_hash=previous_hash,
                    previous_signal_labels=previous_labels or None,
                    previous_core_signals=previous_signals or None,
                    retrospective_required=True,
                )
            except DailyBriefingError:
                invalid_path = analysis_path.with_suffix(".invalid.json")
                analysis_path.replace(invalid_path)
                payload = {}
        else:
            payload = {}
        if not payload:
            run_stage(
                codex,
                daily_briefing_stage(
                    run_id,
                    topics_path,
                    analysis_path,
                    source_snapshot_path,
                    previous_path,
                    previous_hash,
                ),
                logger,
                timeout_seconds=timeout_seconds,
            )
            payload = load_daily_briefing(
                analysis_path,
                source_snapshot_hash=source_hash,
                previous_snapshot_hash=previous_hash,
                previous_signal_labels=previous_labels or None,
                previous_core_signals=previous_signals or None,
                retrospective_required=True,
            )
        logger.info(
            "daily_briefing event=ready failed=false run_id=%s signals=%d must_read=%d "
            "retrospective=%s artifact=%s",
            run_id,
            len(payload["core_signals"]),
            len(payload["must_read"]),
            payload["retrospective"]["status"],
            analysis_path,
        )
        return analysis_path
    except (DailyBriefingError, PipelineError, SearchSignalError, OSError, ValueError) as exc:
        logger.error(
            "daily_briefing event=failed failed=true continuing=false run_id=%s reason_type=%s",
            run_id,
            type(exc).__name__,
        )
        raise PipelineError(
            f"필수 일일 보고서 생성에 실패했습니다: {type(exc).__name__}"
        ) from exc


def planner_retry_stage(stage: Stage, topics_path: Path) -> Stage:
    """Retry a Planner that returned without its required topics artifact."""
    return Stage(
        stage.name,
        stage.agent_file,
        stage.prompt
        + f"\n\n재시도입니다. 이전 실행은 {str(topics_path)!r}를 생성하지 못했습니다. "
        "원래 지시에 명시된 가이드, 기존 WordPress 글, output 기록과 수요 신호는 "
        "필요한 범위에서 읽기 전용으로 다시 확인하세요. 다른 파일이나 외부 시스템은 수정하지 "
        "말고, 검증을 통과한 최소 35개 후보와 TOP10/TOP2를 "
        f"{str(topics_path)!r}에 저장하세요. 유일하게 변경할 파일은 topics.md이며, "
        "저장 후에만 짧게 완료를 보고하세요.",
    )


def run_topic_pipeline(
    codex: str,
    context: TopicContext,
    plan: dict[str, Any],
    logger: logging.Logger,
    *,
    timeout_seconds: int,
    resume: bool,
    publish_lock: threading.Lock,
    humanize_lock: threading.Lock,
) -> dict[str, Any]:
    """Prepare one isolated topic; serialize shared state and WordPress writes."""
    if resume:
        if context.directory.exists():
            assert_owned_path(context, context.directory)
        else:
            context.directory.mkdir(parents=False, exist_ok=False)
    else:
        context.directory.mkdir(parents=False, exist_ok=False)
    if resume and has_successful_publish(context):
        publish_result = read_publish_result(context)
        logger.info(
            "topic=%r run_id=%s topic_id=%s event=resume_published_skip "
            "post_id=%s url=%s",
            context.title,
            context.run_id,
            context.topic_id,
            publish_result["post_id"],
            publish_result["url"],
        )
        return publish_result
    planner_context_path = write_planner_context(context, plan)
    recent_style_context_path = write_recent_style_context(context)
    logger.info(
        "topic=%r run_id=%s topic_id=%s directory=%s "
        "planner_context=%s recent_style_context=%s event=start",
        context.title,
        context.run_id,
        context.topic_id,
        context.directory,
        planner_context_path,
        recent_style_context_path,
    )
    for stage in topic_stages(context):
        if resume:
            required = {
                "Research Agent": (context.directory / "research.md",),
                "Writer Agent": (context.directory / "draft.md",),
                "Humanize Experiment Agent": (
                    context.directory / "draft.md",
                    context.directory / "humanized-draft.md",
                    context.directory / "humanize-summary.md",
                ),
                "Image Maker Agent": (
                    context.directory / "draft.md",
                    context.directory / "images/thumbnail.png",
                ),
                "Assembler Agent": (
                    context.directory / "final.md",
                    context.directory / "final.html",
                ),
                "Reviewer Agent": (
                    context.directory / "publish.md",
                    context.directory / "review.md",
                ),
                "Publisher Agent": (context.directory / "publisher-audit.jsonl",),
            }.get(stage.name, ())
            reviewer_approved = False
            if stage.name == "Reviewer Agent":
                reviewer_approved = read_review_decision(context) == "APPROVED"
            can_skip = required and all(path.is_file() for path in required)
            if stage.name == "Reviewer Agent" and not reviewer_approved:
                can_skip = False
            if stage.name == "Publisher Agent":
                can_skip = has_successful_publish(context)
            if can_skip:
                validate_stage_artifacts(context, stage.name)
                if stage.name == "Research Agent":
                    validate_research_readiness(context)
                logger.info(
                    "topic=%r run_id=%s topic_id=%s agent=%s event=resume_skip",
                    context.title,
                    context.run_id,
                    context.topic_id,
                    stage.name,
                )
                continue
        if stage.name == "Publisher Agent":
            with publish_lock:
                run_review_repair_cycle(
                    codex,
                    context,
                    logger,
                    timeout_seconds=timeout_seconds,
                )
                digest = validate_publish_contract(context)
                logger.info(
                    "topic=%r run_id=%s topic_id=%s "
                    "event=publisher_contract_passed publish_sha256=%s "
                    "publish_path=%s",
                    context.title,
                    context.run_id,
                    context.topic_id,
                    digest,
                    context.directory / "publish.md",
                )
                run_stage(
                    codex,
                    stage,
                    logger,
                    timeout_seconds=timeout_seconds,
                    topic=context.title,
                )
        else:
            run_stage(
                codex,
                stage,
                logger,
                timeout_seconds=timeout_seconds,
                topic=context.title,
            )
        validate_stage_artifacts(context, stage.name)
        if stage.name == "Research Agent":
            validate_research_readiness(context)
        if stage.name == "Humanize Experiment Agent":
            if humanize_experiment_mode() in {"manual-one-off", "on"}:
                original = context.directory / "draft-original.md"
                shutil.copy2(context.directory / "draft.md", original)
                shutil.copy2(
                    context.directory / "humanized-draft.md",
                    context.directory / "draft.md",
                )
                logger.info(
                    "topic=%r agent=%s event=manual_one_off_selected "
                    "original=%s selected=%s",
                    context.title,
                    stage.name,
                    original,
                    context.directory / "draft.md",
                )
            with humanize_lock:
                consume_humanize_experiment_slot(context)
    publish_result = read_publish_result(context)
    logger.info(
        "topic=%r run_id=%s topic_id=%s event=post_published "
        "post_id=%s url=%s image_count=%s",
        context.title,
        context.run_id,
        context.topic_id,
        publish_result["post_id"],
        publish_result["url"],
        publish_result["image_count"],
    )
    logger.info(
        "topic=%r run_id=%s topic_id=%s event=end failed=false",
        context.title,
        context.run_id,
        context.topic_id,
    )
    return publish_result


def run_selected_topics(
    codex: str,
    contexts: list[TopicContext],
    plans: list[dict[str, Any]],
    logger: logging.Logger,
    *,
    timeout_seconds: int,
    resume: bool,
    workers: int,
) -> list[dict[str, Any]]:
    """Run isolated TOP2 work concurrently while preserving result order."""
    publish_lock = threading.Lock()
    humanize_lock = threading.Lock()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(workers, len(contexts)),
        thread_name_prefix="huntlab-topic",
    ) as executor:
        futures = [
            executor.submit(
                run_topic_pipeline,
                codex,
                context,
                plan,
                logger,
                timeout_seconds=timeout_seconds,
                resume=resume,
                publish_lock=publish_lock,
                humanize_lock=humanize_lock,
            )
            for context, plan in zip(contexts, plans)
        ]
        return [future.result() for future in futures]


def quality_fallback_plans(
    top10: list[dict[str, Any]], legacy_top2: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return legacy TOP10 order after TOP2 without consulting Shadow ranking."""
    selected = {str(plan.get("title", "")) for plan in legacy_top2}
    return [plan for plan in top10 if str(plan.get("title", "")) not in selected]


def _write_publication_fallback_artifact(
    run_directory: Path, payload: dict[str, Any]
) -> Path:
    run_directory.mkdir(parents=True, exist_ok=True)
    destination = run_directory / "publication-fallback.json"
    temporary = run_directory / ".publication-fallback.json.tmp"
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def run_topics_with_quality_fallback(
    codex: str,
    contexts: list[TopicContext],
    plans: list[dict[str, Any]],
    fallback_plans: list[dict[str, Any]],
    logger: logging.Logger,
    *,
    timeout_seconds: int,
    resume: bool,
    workers: int,
) -> list[dict[str, Any]]:
    """Backfill only evidence/Reviewer rejections, preserving both ranking outputs."""
    publish_lock = threading.Lock()
    humanize_lock = threading.Lock()
    results: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    replacements: list[dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(workers, len(contexts)),
        thread_name_prefix="huntlab-topic",
    ) as executor:
        futures = [
            executor.submit(
                run_topic_pipeline,
                codex,
                context,
                plan,
                logger,
                timeout_seconds=timeout_seconds,
                resume=resume,
                publish_lock=publish_lock,
                humanize_lock=humanize_lock,
            )
            for context, plan in zip(contexts, plans)
        ]
        for context, future in zip(contexts, futures):
            try:
                results.append(future.result())
            except ContentQualityRejection as exc:
                rejected.append(
                    {
                        "topic_id": context.topic_id,
                        "title": context.title,
                        "reason": str(exc),
                    }
                )
                logger.warning(
                    "topic=%r topic_id=%s event=quality_rejected "
                    "fallback_eligible=true reason=%s",
                    context.title,
                    context.topic_id,
                    exc,
                )

    needed = len(contexts) - len(results)
    for plan in fallback_plans:
        if needed <= 0:
            break
        context = make_topic_context(
            contexts[0].run_id,
            str(plan["title"]),
            category=str(plan["category"]),
            content_type=str(plan["content_type"]),
            tags=tuple(plan["tags"]),
            reason=str(plan["reason"]),
            research_focus=str(plan["research_focus"]),
        )
        try:
            result = run_topic_pipeline(
                codex,
                context,
                plan,
                logger,
                timeout_seconds=timeout_seconds,
                resume=context.directory.exists(),
                publish_lock=publish_lock,
                humanize_lock=humanize_lock,
            )
        except ContentQualityRejection as exc:
            rejected.append(
                {
                    "topic_id": context.topic_id,
                    "title": context.title,
                    "reason": str(exc),
                }
            )
            logger.warning(
                "topic=%r topic_id=%s event=fallback_quality_rejected reason=%s",
                context.title,
                context.topic_id,
                exc,
            )
            continue
        results.append(result)
        replacements.append(
            {
                "topic_id": context.topic_id,
                "title": context.title,
                "post_id": result.get("post_id"),
                "url": result.get("url"),
            }
        )
        needed -= 1

    artifact = {
        "contract_version": "publication-fallback.v1",
        "legacy_top2": [context.title for context in contexts],
        "shadow_selection_used": False,
        "rejected": rejected,
        "replacements": replacements,
        "published_count": len(results),
        "target_count": len(contexts),
        "complete": len(results) == len(contexts),
    }
    _write_publication_fallback_artifact(contexts[0].directory.parent, artifact)
    if len(results) != len(contexts):
        raise PipelineError(
            f"품질 기준을 통과한 발행 결과가 {len(results)}/{len(contexts)}건입니다."
        )
    return results


def write_and_sync_briefing_manifest(
    *,
    run_id: str,
    run_directory: Path,
    plan_document: dict[str, Any],
    logger: logging.Logger,
) -> Path:
    """Persist and synchronise the required end-to-end briefing manifest."""
    destination = run_directory / "briefing-manifest.json"
    editorial_source_path = run_directory / "editorial-sources-snapshot.json"
    if not editorial_source_path.is_file():
        editorial_source_path = DEFAULT_EDITORIAL_SOURCE_CACHE
    payload = build_briefing_manifest(
        run_id=run_id,
        plan_document=plan_document,
        publications=collect_run_publications(run_directory),
        trends_cache_path=DEFAULT_GOOGLE_TRENDS_CACHE,
        editorial_source_cache_path=editorial_source_path,
        shadow_path=run_directory / "news-worthiness-shadow.json",
        fallback_path=run_directory / "publication-fallback.json",
        daily_briefing_path=run_directory / "daily-briefing-analysis.json",
    )
    atomic_write_manifest(destination, payload)
    logger.info(
        "briefing_manifest event=written run_id=%s complete=%s published=%d artifact=%s",
        run_id,
        payload["complete"],
        len(payload["published"]),
        destination,
    )
    if not payload["complete"]:
        completion = payload.get("completion", {})
        logger.error(
            "briefing_manifest event=incomplete failed=true continuing=false "
            "analysis_complete=%s publications_complete=%s",
            bool(completion.get("analysis_complete")),
            bool(completion.get("publications_complete")),
        )
        raise PipelineError("필수 브리핑 매니페스트가 완전하지 않습니다")
    try:
        config = WordPressConfig.from_environment(PROJECT_ROOT / ".env")
        response = WordPressClient(config).sync_briefing_manifest(payload)
        stored = isinstance(response, dict) and response.get("stored") is True
        logger.info(
            "briefing_manifest event=synced failed=false run_id=%s stored=%s",
            run_id,
            stored,
        )
        if not stored:
            raise WordPressError(
                "briefing_manifest_storage",
                "WordPress did not confirm briefing manifest storage",
            )
    except (ConfigurationError, WordPressError, OSError, ValueError) as exc:
        logger.error(
            "briefing_manifest event=sync_failed failed=true continuing=false "
            "run_id=%s reason_type=%s",
            run_id,
            type(exc).__name__,
        )
        raise PipelineError(
            f"필수 브리핑 매니페스트 동기화에 실패했습니다: {type(exc).__name__}"
        ) from exc
    return destination


def main() -> int:
    args = build_parser().parse_args()
    logger = configure_logger(date.today())
    started = time.monotonic()
    lock = PipelineLock(LOCK_FILE)
    try:
        lock.acquire()
        codex = resolve_codex()
        if args.dry_run:
            return validate_dry_run(
                codex,
                logger,
                args.keywords,
                args.limit,
                args.start_rank,
            )
        if args.start_rank + args.limit - 1 > 2:
            raise PipelineError("실행 범위가 TOP2를 벗어났습니다.")
        if args.resume_run_id:
            if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{10}", args.resume_run_id):
                raise PipelineError("resume-run-id 형식이 올바르지 않습니다.")
            run_id = args.resume_run_id
            run_directory = RUNS_DIR / run_id
            topics_path = run_directory / "topics.md"
            if not topics_path.is_file():
                raise PipelineError("재개할 topics.md가 없습니다.")
            logger.info(
                "pipeline event=resume run_id=%s start_rank=%s limit=%s",
                run_id,
                args.start_rank,
                args.limit,
            )
        else:
            if args.start_rank != 1:
                raise PipelineError("새 실행은 start-rank 1부터 시작해야 합니다.")
            run_id = make_run_id()
            run_directory = RUNS_DIR / run_id
            run_directory.mkdir(parents=True, exist_ok=False)
            topics_path = run_directory / "topics.md"
            observation_path = args.whereispost_observation
            if args.use_whereispost_cache and observation_path is None:
                observation_path = DEFAULT_WHEREISPOST_CACHE
            try:
                whereispost_observation = read_whereispost_observation(
                    observation_path
                )
            except PipelineError as exc:
                if not args.use_whereispost_cache:
                    raise
                logger.warning(
                    "whereispost_cache status=UNAVAILABLE continuing=true reason=%s",
                    exc,
                )
                whereispost_observation = ""
            google_trends_observation = ""
            if args.use_google_trends_cache:
                try:
                    google_trends_observation = read_google_trends_observation(
                        DEFAULT_GOOGLE_TRENDS_CACHE
                    )
                except PipelineError as exc:
                    logger.warning(
                        "google_trends_cache status=UNAVAILABLE continuing=true reason=%s",
                        exc,
                    )
            editorial_source_observation = ""
            if args.use_editorial_source_cache:
                try:
                    editorial_source_observation = read_editorial_source_observation(DEFAULT_EDITORIAL_SOURCE_CACHE)
                except PipelineError as exc:
                    logger.warning("editorial_source_cache status=UNAVAILABLE continuing=true reason=%s", exc)
            planner = planner_stage(
                args.keywords,
                run_id,
                topics_path,
                whereispost_observation,
                whereispost_cache_mode=args.use_whereispost_cache,
                google_trends_observation=google_trends_observation,
                google_trends_cache_mode=args.use_google_trends_cache,
                editorial_source_observation=editorial_source_observation,
                editorial_source_cache_mode=args.use_editorial_source_cache,
                category_distribution=read_public_category_distribution(
                    os.environ.get("PUBLIC_SITE_URL", "https://huntlab.app/")
                ),
            )
            logger.info(
                "pipeline event=start run_id=%s run_directory=%s",
                run_id,
                run_directory,
            )
            # Planner inspects the live WordPress corpus, 35+ candidates,
            # official sources and demand signals. It must honor the same
            # operator-selected ceiling as the evidence-heavy topic stages;
            # a hidden 15-minute cap caused valid planning runs to time out.
            planner_timeout = args.timeout
            run_stage(codex, planner, logger, timeout_seconds=planner_timeout)
            if not topics_path.is_file():
                logger.warning(
                    "planner event=missing_topics retry=true path=%s",
                    topics_path,
                )
                retry = planner_retry_stage(planner, topics_path)
                run_stage(codex, retry, logger, timeout_seconds=planner_timeout)
            if not topics_path.is_file():
                raise PipelineError(
                    f"Topic Planner가 재시도 후에도 {topics_path}를 생성하지 않았습니다."
                )
        plan_document = parse_topic_plan_document(topics_path)
        plans = plan_document["top2"]
        run_daily_briefing_analysis(
            codex,
            run_id=run_id,
            run_directory=run_directory,
            topics_path=topics_path,
            logger=logger,
            timeout_seconds=args.timeout,
        )
        # Shadow ranking is observability-only. Failure cannot replace, reorder,
        # or block the legacy TOP2 and therefore cannot affect 02:00 publishing.
        run_news_worthiness_shadow(run_directory, plan_document, logger)
        topics = [plan["title"] for plan in plans]
        selected_plans = plans[
            args.start_rank - 1 : args.start_rank - 1 + args.limit
        ]
        contexts = [
            make_topic_context(
                run_id,
                plan["title"],
                category=plan["category"],
                content_type=plan["content_type"],
                tags=plan["tags"],
                reason=plan["reason"],
                research_focus=plan["research_focus"],
            )
            for plan in selected_plans
        ]
        if len({context.topic_id for context in contexts}) != args.limit:
            raise PipelineError("실행 대상 topic_id가 고유하지 않습니다.")
        logger.info(
            "pipeline event=top2 run_id=%s topics=%r topic_ids=%r",
            run_id,
            topics,
            [context.topic_id for context in contexts],
        )

        if args.start_rank == 1 and args.limit == 2:
            results = run_topics_with_quality_fallback(
                codex,
                contexts,
                selected_plans,
                quality_fallback_plans(plan_document["top10"], plans),
                logger,
                timeout_seconds=args.timeout,
                resume=bool(args.resume_run_id),
                workers=args.topic_workers,
            )
        else:
            results = run_selected_topics(
                codex,
                contexts,
                selected_plans,
                logger,
                timeout_seconds=args.timeout,
                resume=bool(args.resume_run_id),
                workers=args.topic_workers,
            )
        write_and_sync_briefing_manifest(
            run_id=run_id,
            run_directory=run_directory,
            plan_document=plan_document,
            logger=logger,
        )
        logger.info(
            "pipeline event=end failed=false run_id=%s topics=%r posts=%r "
            "duration_seconds=%.3f",
            run_id,
            topics,
            results,
            time.monotonic() - started,
        )
        verify_logs_do_not_contain_secrets()
        return 0
    except (PipelineError, OSError) as exc:
        logger.exception("pipeline event=failed reason=%s", exc)
        return 1
    finally:
        lock.release()


def _env_secret_values() -> list[str]:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return []
    secrets: list[str] = []
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw_line or raw_line.lstrip().startswith("#"):
            continue
        key, value = raw_line.split("=", 1)
        if key.strip() in {"WORDPRESS_APP_PASSWORD"} and value.strip():
            secrets.append(value.strip().strip("\"'"))
    return secrets


def verify_logs_do_not_contain_secrets() -> None:
    secrets = _env_secret_values()
    for path in (LOG_DIR / f"{date.today().isoformat()}.log", LOG_DIR / "cron.log"):
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        if any(secret and secret in content for secret in secrets):
            raise PipelineError(f"로그 비밀정보 검사 실패: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
