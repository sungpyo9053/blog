#!/usr/bin/env python3
"""Run the HuntLab daily TOP2 blog pipeline with fail-fast logging."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from publisher.frontmatter import FrontmatterError, load_document


OUTPUT_DIR = PROJECT_ROOT / "output"
RUNS_DIR = OUTPUT_DIR / "runs"
LOG_DIR = PROJECT_ROOT / "logs"
LOCK_FILE = LOG_DIR / "daily-pipeline.lock"
TOP2_PATTERN = re.compile(r"(?m)^\s*[12]\.\s+(.+?)\s*$")
EDITOR_CATEGORIES = {
    "Tech",
    "AI",
    "Economy",
    "Society",
    "Politics",
    "Hot Issue",
    "Build Log",
}


class PipelineError(RuntimeError):
    """Raised when a stage cannot safely continue."""


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


def parse_topic_plan(path: Path) -> list[dict[str, Any]]:
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
    }
    category_counts = {category: 0 for category in EDITOR_CATEGORIES}
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
        tags = tuple(
            dict.fromkeys(tag.strip() for tag in fields["tags"].split(",") if tag.strip())
        )
        if not 3 <= len(tags) <= 7:
            raise PipelineError(f"{title}: tags는 3~7개여야 합니다.")
        category_counts[category] += 1
        candidates[title] = {**fields, "tags": tags}

    insufficient = {
        category: count for category, count in category_counts.items() if count < 5
    }
    if insufficient:
        raise PipelineError(f"카테고리별 후보가 5개 미만입니다: {insufficient}")

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
    non_technical = {"Economy", "Society", "Politics", "Hot Issue"}
    if not any(candidates[title]["category"] in non_technical for title in topics):
        raise PipelineError(
            "TOP2에는 Economy, Society, Politics, Hot Issue 중 하나가 필요합니다."
        )
    return [candidates[title] for title in topics]


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
) -> TopicContext:
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
    payload = {
        "run_id": context.run_id,
        "topic_id": context.topic_id,
        "title": context.title,
        "category": context.category,
        "tags": list(context.tags),
        "primary_keyword": plan.get("primary_keyword", ""),
        "secondary_keywords": plan.get("secondary_keywords", ""),
        "target_reader": plan.get("target_reader", ""),
        "reason": context.reason,
        "search_intent": plan.get("search_intent", ""),
        "research_focus": context.research_focus,
        "duplicate_check": duplicate_check,
        "sources": plan.get("sources", ""),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def topic_stages(context: TopicContext) -> list[Stage]:
    topic = context.title
    topic_dir = context.directory
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
        f"tags={list(context.tags)!r}, reason={context.reason!r}, "
        f"research_focus={context.research_focus!r}입니다. 이 값을 그대로 활용하고 "
        "카테고리와 태그를 다른 값으로 바꾸지 마세요. "
    )
    common += editorial
    return [
        Stage(
            "Research Agent",
            PROJECT_ROOT / "agents/researcher.md",
            (
                common
                + f"Topic Planner의 TOP2 중 다음 주제만 조사하세요: {topic!r}. "
                f"선정 근거와 검색 의도는 {str(topic_dir / 'planner-context.json')!r}에서 "
                "읽고, 중복 검사 결과를 사실 근거로 확대 해석하지 마세요. "
                f"다른 주제를 조사하지 말고 산출물을 "
                f"{str(topic_dir / 'research.md')!r}에 저장하세요."
            ),
        ),
        Stage(
            "Writer Agent",
            PROJECT_ROOT / "agents/writer.md",
            (
                common
                + f"입력은 {str(topic_dir / 'research.md')!r} 하나입니다. "
                f"분석 리포트 {str(PROJECT_ROOT / 'output/analytics/latest.md')!r}가 있으면 "
                "검색 의도·CTA 제안만 참고하고 사실 근거는 research.md를 우선하세요. "
                f"기존 Guide를 적용해 {str(topic_dir / 'draft.md')!r}를 작성하세요."
            ),
        ),
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
                f"{str(PROJECT_ROOT / 'guides/style-guide.md')!r}, "
                f"{str(PROJECT_ROOT / 'guides/seo-guide.md')!r}, "
                f"{str(PROJECT_ROOT / 'guides/monetization-guide.md')!r}, "
                f"{str(PROJECT_ROOT / 'guides/publisher-guide.md')!r} "
                "기준으로 검토하세요. 정책 문서는 읽기만 하고 주제 디렉터리로 "
                "복사하지 마세요. "
                f"원문 의미를 바꾸지 않는 {str(topic_dir / 'publish.md')!r}를 "
                "준비하되 WordPress "
                "제목이 H1이 되도록 본문은 H2부터 시작하고 필요한 Frontmatter를 "
                f"추가하세요. Frontmatter title은 {topic!r}와 정확히 일치해야 하고, "
                f"run_id는 {context.run_id!r}, topic_id는 {context.topic_id!r}, "
                f"source_id는 {context.source_id!r}, category는 "
                f"{context.category!r}, tags는 {list(context.tags)!r}, "
                "publish_mode는 'publish'여야 "
                f"합니다. publish.md의 SHA-256, run_id, topic_id와 APPROVED 또는 "
                f"REJECTED를 {str(topic_dir / 'review.md')!r}에 기록하세요. "
                "planner-context.json의 기존 WordPress 제목·Draft 중복 검사 결과를 "
                "검토 기록에 근거로 반영하세요. "
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
                "publish_mode가 publish가 아니면 실패하세요. schedule과 기존 "
                "공개글 변경은 수행하지 마세요. .env는 Publisher 스크립트만 "
                "읽게 하고 값을 직접 열거나 출력하지 마세요."
            ),
        ),
    ]


def validate_stage_artifacts(context: TopicContext, stage_name: str) -> None:
    required: dict[str, tuple[Path, ...]] = {
        "Research Agent": (context.directory / "research.md",),
        "Writer Agent": (context.directory / "draft.md",),
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

    digest = hashlib.sha256(publish_path.read_bytes()).hexdigest()
    review = review_path.read_text(encoding="utf-8")
    required_tokens = ("APPROVED", context.run_id, context.topic_id, digest)
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
        if event.get("event") == "post_published" and event.get("status") == "Success":
            events.append(event)
    if not events:
        raise PipelineError(f"{context.topic_id}: 성공한 Publish 기록이 없습니다.")
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HuntLab TOP2 daily pipeline")
    parser.add_argument(
        "--keywords",
        default="",
        help="Topic Planner에 전달할 쉼표 구분 추가 키워드",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Agent별 제한 시간(초, 기본 3600)",
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
    for category in sorted(EDITOR_CATEGORIES):
        for index in range(1, 6):
            number += 1
            title = f"{category} Dry Run 후보 {index}"
            candidates.append(
                f"## {number}. {title}\n\n"
                f"- title: {title}\n"
                f"- category: {category}\n"
                "- tags: DryRun, Pipeline, HuntLab\n"
                "- score: 72/90\n"
                "- score_breakdown: 최신성 8; 검색 수요 8; 공식 출처 8; "
                "Evergreen 8; HuntLab 적합성 8; 기술적 깊이 8; 독창성 8; "
                "최근 작성 여부 8; 카테고리 균형 8\n"
                "- reason: 파서 검증\n"
                "- evergreen: 중간\n"
                "- search_intent: 자동화 검증\n"
                "- research_focus: 공식 자료 확인\n"
                "- recommended_images: 대표 이미지 1개\n"
                "- duplicate_check: 중복 없음\n"
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
        plans = parse_topic_plan(synthetic_path)
    finally:
        synthetic_path.unlink(missing_ok=True)
    logger.info("dry_run event=top2 topics=%r", [plan["title"] for plan in plans])

    for plan in plans[start_rank - 1 : start_rank - 1 + limit]:
        topic = plan["title"]
        context = make_topic_context(
            run_id,
            topic,
            category=plan["category"],
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


def planner_stage(keywords: str, run_id: str, topics_path: Path) -> Stage:
    return Stage(
        "Topic Planner Agent",
        PROJECT_ROOT / "agents/topic-planner-agent.md",
        (
            f"현재 날짜는 {date.today().isoformat()}입니다. "
            f"run_id는 {run_id!r}입니다. "
            f"추가 키워드는 {keywords.strip() or '없음'}입니다. "
            "기존 WordPress 게시글과 Draft, output의 기존 글을 확인한 뒤 "
            "Tech, AI, Economy, Society, Politics, Hot Issue, Build Log에서 "
            f"각각 후보 5개 이상, 전체 35개 이상, TOP10과 TOP2를 {str(topics_path)!r}에 "
            "작성하세요. "
            f"{str(PROJECT_ROOT / 'output/analytics/latest.md')!r}가 있으면 검색어·CTR·조회수 "
            "관측값과 제안만 참고하고, 데이터가 없으면 추측하지 마세요. "
            "output의 다른 파일은 수정하지 마세요. "
            "글 작성, 본문 리서치, 이미지 생성, Publisher 호출은 하지 마세요."
        ),
    )


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
            planner = planner_stage(args.keywords, run_id, topics_path)
            logger.info(
                "pipeline event=start run_id=%s run_directory=%s",
                run_id,
                run_directory,
            )
            run_stage(codex, planner, logger, timeout_seconds=args.timeout)
        plans = parse_topic_plan(topics_path)
        topics = [plan["title"] for plan in plans]
        selected_plans = plans[
            args.start_rank - 1 : args.start_rank - 1 + args.limit
        ]
        contexts = [
            make_topic_context(
                run_id,
                plan["title"],
                category=plan["category"],
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

        results: list[dict[str, Any]] = []
        for context in contexts:
            if args.resume_run_id:
                if context.directory.exists():
                    assert_owned_path(context, context.directory)
                else:
                    context.directory.mkdir(parents=False, exist_ok=False)
            else:
                context.directory.mkdir(parents=False, exist_ok=False)
            plan = next(
                plan for plan in selected_plans if plan["title"] == context.title
            )
            planner_context_path = write_planner_context(context, plan)
            logger.info(
                "topic=%r run_id=%s topic_id=%s directory=%s "
                "planner_context=%s event=start",
                context.title,
                context.run_id,
                context.topic_id,
                context.directory,
                planner_context_path,
            )
            for stage in topic_stages(context):
                if args.resume_run_id:
                    required = {
                        "Research Agent": (context.directory / "research.md",),
                        "Writer Agent": (context.directory / "draft.md",),
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
                        review_path = context.directory / "review.md"
                        reviewer_approved = review_path.is_file() and "APPROVED" in review_path.read_text(encoding="utf-8")
                    can_skip = required and all(path.is_file() for path in required)
                    if stage.name == "Reviewer Agent" and not reviewer_approved:
                        can_skip = False
                    if can_skip:
                        logger.info(
                            "topic=%r run_id=%s topic_id=%s agent=%s event=resume_skip",
                            context.title,
                            context.run_id,
                            context.topic_id,
                            stage.name,
                        )
                        continue
                if stage.name == "Publisher Agent":
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
                    timeout_seconds=args.timeout,
                    topic=context.title,
                )
                validate_stage_artifacts(context, stage.name)
            publish_result = read_publish_result(context)
            results.append(publish_result)
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
