#!/usr/bin/env python3
"""Build a reversible, evidence-led AdSense content inventory from WordPress."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient


TECH_CATEGORY_SLUGS = {
    "it",
    "ai",
    "ai-ml-core",
    "development-trends",
    "ai-official-blogs",
    "korea-it",
    "korea-current-affairs",
    "technical-explainer",
    "tech",
    "build-log",
    "harness-engineering",
    "ml-algorithms",
    "system-architecture",
}
NONTECH_CATEGORY_SLUGS = {
    "life",
    "economy",
    "society",
    "politics",
    "real-estate",
    "culture-entertainment",
}

DIRECT_TERMS = (
    "직접 실행",
    "직접 검증",
    "직접 확인",
    "재현 환경",
    "검증 환경",
    "테스트 환경",
    "실행 결과",
    "검증 결과",
)
FAILURE_TERMS = (
    "실패 로그",
    "실패했다",
    "실패했습니다",
    "exit code",
    "exit_code",
    "traceback",
    "오류 로그",
)
MEASUREMENT_RE = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*(?:ms|초|분|시간|mb|gb|kb|%|배|건|회|rps|tokens?/s)\b|"
    r"p50|p95|p99|throughput|latency|benchmark|벤치마크|전후 비교)",
    re.IGNORECASE,
)
COMMAND_RE = re.compile(
    r"\b(?:python|python3|curl|docker|git|npm|pnpm|pytest|systemctl|journalctl|aws|kubectl|"
    r"terraform|make|go test|cargo test)\b",
    re.IGNORECASE,
)
NOT_DIRECT_TERMS = (
    "직접 시험하지",
    "직접 테스트하지",
    "직접 실행하지",
    "재현하지 못",
    "검증하지 못",
    "공개 자료만",
    "not_directly_tested",
)
QUICK_SUMMARY_RE = re.compile(r"20초\s*핵심\s*요약")
CHECK_TITLE_RE = re.compile(r"확인|점검|검증|어떻게|하는 법|할 것")

# Human editorial review of the 119-post production snapshot.  A heuristic is
# useful for surfacing evidence, but code blocks and numbers alone do not prove
# first-hand experience.  KEEP therefore requires an explicit reviewed ID for
# this snapshot; everything else technical remains a rewrite candidate.
KEEP_EVIDENCE = {
    96: "scripts/backfill_internal_links.py; logs/launchd.out.log",
    269: "output/runs/20260805T040942Z-3f0a7d87ff/topic-09439ac1c357727f/research.md; review.md",
    274: "output/runs/20260805T043557Z-8b555b4bb1/topic-f0a9bfee1d587f09/research.md; publisher-audit.jsonl",
    290: "publisher/service.py; tests/test_publisher.py",
    301: "deploy/wordpress/huntlab-article-toc/huntlab-article-toc.php; commit ffd304f",
    373: "scripts/run_daily_pipeline.py; tests/test_daily_pipeline.py; logs/2026-08-14.log",
}
MERGE_TARGETS = {
    178: 348,
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored and data.strip():
            self.parts.append(data.strip())


def visible_text(document: str) -> str:
    parser = TextExtractor()
    parser.feed(document)
    return " ".join(html.unescape(part) for part in parser.parts)


def fetch_all(
    client: WordPressClient,
    endpoint: str,
    *,
    context: str = "edit",
    status: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        query = {"per_page": "100", "page": str(page), "context": context}
        if status:
            query["status"] = status
        try:
            batch = client.request(
                "GET",
                f"{endpoint}?{urlencode(query)}",
                expected=(200,),
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) == 400 and page > 1:
                break
            raise
        rows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return rows


def _field(row: dict[str, Any], name: str) -> str:
    value = row.get(name, {})
    if isinstance(value, dict):
        return str(value.get("raw") or value.get("rendered") or "")
    return str(value or "")


def _present_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    return [term for term in terms if term.casefold() in lowered]


def inspect_post(
    post: dict[str, Any],
    categories_by_id: dict[int, dict[str, Any]],
    authors_by_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    raw = _field(post, "content")
    text = visible_text(raw)
    title = visible_text(_field(post, "title"))
    category_rows = [
        categories_by_id[category_id]
        for category_id in post.get("categories", [])
        if category_id in categories_by_id
    ]
    slugs = [str(row.get("slug", "")) for row in category_rows]
    names = [str(row.get("name", "")) for row in category_rows]
    direct_terms = _present_terms(text, DIRECT_TERMS)
    failure_terms = _present_terms(text, FAILURE_TERMS)
    not_direct_terms = _present_terms(text, NOT_DIRECT_TERMS)
    code_blocks = len(re.findall(r"<(?:pre|code)\b", raw, re.IGNORECASE))
    commands = sorted(set(match.group(0) for match in COMMAND_RE.finditer(text)))
    measurements = MEASUREMENT_RE.findall(text)
    table_count = len(re.findall(r"<table\b", raw, re.IGNORECASE))
    heading_count = len(re.findall(r"<h[2-4]\b", raw, re.IGNORECASE))
    raw_quick_summary = bool(QUICK_SUMMARY_RE.search(text))
    technical = bool(set(slugs) & TECH_CATEGORY_SLUGS)
    nontechnical = bool(set(slugs) & NONTECH_CATEGORY_SLUGS)

    evidence_score = 0
    evidence_score += min(code_blocks, 2) * 2
    evidence_score += 2 if direct_terms else 0
    evidence_score += 2 if failure_terms else 0
    evidence_score += 2 if measurements else 0
    evidence_score += 1 if commands else 0
    evidence_score += 1 if table_count else 0
    evidence_score -= 4 if not_direct_terms else 0

    # Code fences, numbers and first-person wording only surface candidates.
    # They do not establish first-hand evidence without a durable artifact.
    direct_verification = "YES" if int(post["id"]) in KEEP_EVIDENCE else "NO"

    template_signals: list[str] = []
    if raw_quick_summary:
        template_signals.append("raw_20초_요약")
    if ":" in title or "：" in title:
        template_signals.append("콜론_제목")
    if CHECK_TITLE_RE.search(title):
        template_signals.append("확인형_제목")
    if heading_count >= 7:
        template_signals.append("다단_고정구조")

    post_id = int(post["id"])
    if nontechnical and not technical:
        decision = "NOINDEX"
        reason = "현재 AI·개발 전문 포지셔닝과 직접 연결되지 않는 비기술 카테고리"
    elif post_id in MERGE_TARGETS:
        decision = "MERGE"
        reason = f"검색 의도와 핵심 내용이 겹치는 post {MERGE_TARGETS[post_id]}로 통합 후 이 URL은 noindex"
    elif post_id in KEEP_EVIDENCE:
        decision = "KEEP"
        reason = f"추적 가능한 1차 근거: {KEEP_EVIDENCE[post_id]}"
    else:
        decision = "REWRITE"
        reason = "기술 주제이지만 코드·수치만으로 1차 경험을 입증할 수 없어 재현 과정과 판단을 보강해야 함"

    contribution_bits: list[str] = []
    if code_blocks:
        contribution_bits.append(f"코드블록 {code_blocks}")
    if direct_terms:
        contribution_bits.append("직접 검증 고지")
    if failure_terms:
        contribution_bits.append("실패 기록")
    if measurements:
        contribution_bits.append(f"측정 신호 {len(measurements)}")
    if commands:
        contribution_bits.append("실행 명령")
    if not_direct_terms:
        contribution_bits.append("미검증 고지")
    if not contribution_bits:
        contribution_bits.append("문서·출처 종합 중심")

    aioseo = post.get("aioseo_meta_data") or {}
    author = authors_by_id.get(int(post.get("author", 0)), {})
    return {
        "post_id": post_id,
        "url": str(post.get("link", "")),
        "slug": str(post.get("slug", "")),
        "title": title,
        "published_at": str(post.get("date", "")),
        "modified_at": str(post.get("modified", "")),
        "category_ids": list(post.get("categories", [])),
        "category_slugs": slugs,
        "categories": names,
        "author_id": int(post.get("author", 0)),
        "author": str(author.get("name", "")),
        "direct_verification": direct_verification,
        "evidence_path": KEEP_EVIDENCE.get(post_id, ""),
        "evidence_score": evidence_score,
        "unique_value": ", ".join(contribution_bits),
        "template_risk": ", ".join(template_signals) or "낮음",
        "raw_20s_summary": raw_quick_summary,
        "code_blocks": code_blocks,
        "table_count": table_count,
        "heading_count": heading_count,
        "measurement_signal_count": len(measurements),
        "direct_terms": direct_terms,
        "failure_terms": failure_terms,
        "not_direct_terms": not_direct_terms,
        "commands": commands,
        "current_noindex": bool(aioseo.get("robots_noindex", False)),
        "decision": decision,
        "reason": reason,
    }


def write_outputs(
    output_dir: Path,
    posts: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    users: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    categories_by_id = {int(row["id"]): row for row in categories}
    authors_by_id = {int(row["id"]): row for row in users}
    inventory = [
        inspect_post(post, categories_by_id, authors_by_id)
        for post in sorted(posts, key=lambda row: (str(row.get("date", "")), int(row["id"])))
    ]
    backup = {
        "created_at": datetime.now(UTC).isoformat(),
        "posts": posts,
        "categories": categories,
        "pages": pages,
        "users": users,
    }
    (output_dir / "wordpress-backup.json").write_text(
        json.dumps(backup, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    fieldnames = [
        "post_id",
        "url",
        "title",
        "categories",
        "direct_verification",
        "evidence_path",
        "unique_value",
        "template_risk",
        "decision",
        "reason",
    ]
    with (output_dir / "inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in inventory:
            writer.writerow({key: row[key] for key in fieldnames})

    decisions = Counter(row["decision"] for row in inventory)
    categories_count = Counter(
        slug for row in inventory for slug in row["category_slugs"]
    )
    dates = Counter(str(row["published_at"])[:10] for row in inventory)
    lines = [
        "# Hunt News AdSense Content Inventory",
        "",
        f"- generated_at: `{datetime.now(UTC).isoformat()}`",
        f"- published_posts: `{len(inventory)}`",
        f"- decisions: `{json.dumps(dict(sorted(decisions.items())), ensure_ascii=False)}`",
        f"- category_assignments: `{json.dumps(dict(sorted(categories_count.items())), ensure_ascii=False)}`",
        f"- raw_20s_summary: `{sum(row['raw_20s_summary'] for row in inventory)}`",
        f"- public_wrapper_20s_summary: `공개 크롤러 기준 119/119`",
        f"- direct_yes: `{sum(row['direct_verification'] == 'YES' for row in inventory)}`",
        f"- direct_partial: `{sum(row['direct_verification'] == 'PARTIAL' for row in inventory)}`",
        f"- direct_no: `{sum(row['direct_verification'] == 'NO' for row in inventory)}`",
        f"- peak_2026-08-15_to_17: `{sum(dates[day] for day in ('2026-08-15', '2026-08-16', '2026-08-17'))}`",
        "",
        "| post_id | 판정 | 직접 검증 | 카테고리 | 제목 | URL | 근거 |",
        "|---:|---|---|---|---|---|---|",
    ]
    for row in inventory:
        safe_title = row["title"].replace("|", "\\|")
        safe_reason = row["reason"].replace("|", "\\|")
        lines.append(
            f"| {row['post_id']} | {row['decision']} | {row['direct_verification']} | "
            f"{', '.join(row['categories'])} | {safe_title} | {row['url']} | {safe_reason} |"
        )
    (output_dir / "inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "output" / "audits" / "adsense-overhaul",
    )
    args = parser.parse_args()
    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    posts = fetch_all(client, "posts", status="publish")
    categories = fetch_all(client, "categories")
    pages = fetch_all(client, "pages")
    users = fetch_all(client, "users", context="view")
    write_outputs(args.output_dir, posts, categories, pages, users)
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
