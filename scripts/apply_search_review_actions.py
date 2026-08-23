#!/usr/bin/env python3
"""Apply explicitly approved post-search-review actions with backups and audit logs."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient

CASE_LINK_MARKER = "<!-- huntlab-index-cases:v1 -->"


def _plain_title(post: dict[str, Any]) -> str:
    value = post.get("title", {})
    if isinstance(value, dict):
        value = value.get("raw") or value.get("rendered") or ""
    return html.unescape(str(value)).strip()


def _raw_content(post: dict[str, Any]) -> str:
    value = post.get("content", {})
    if isinstance(value, dict):
        return str(value.get("raw") or value.get("rendered") or "")
    return str(value or "")


def parse_title_experiment(report: str, expected_date: date) -> dict[str, Any]:
    generated = re.search(r"(?m)^- generated_at: `([^`]+)`$", report)
    status = re.search(r"(?m)^- resident_title_experiment: `([^`]+)`$", report)
    proposed = re.search(
        r"(?m)^- proposed_single_change: `title_only` → `([^`]+)`$", report
    )
    metrics = re.search(
        r"(?m)^- resident_title_metrics: `clicks=([0-9.]+), "
        r"impressions=([0-9.]+), position=([0-9.]+)`$",
        report,
    )
    stop_rule = re.search(r"(?m)^- experiment_stop_rule: `([^`]+)`$", report)
    if None in {generated, status, proposed, metrics, stop_rule}:
        raise ValueError("analytics report has no complete title experiment decision")
    assert generated and status and proposed and metrics and stop_rule
    if datetime.fromisoformat(generated.group(1)).date() != expected_date:
        raise ValueError("analytics report date does not match review date")
    if status.group(1) != "ELIGIBLE_REVIEW":
        raise ValueError("title experiment is not eligible for review")
    return {
        "proposed_title": proposed.group(1).strip(),
        "clicks": float(metrics.group(1)),
        "impressions": float(metrics.group(2)),
        "position": float(metrics.group(3)),
        "stop_rule": stop_rule.group(1),
    }


def add_reviewed_case_links(content: str, targets: list[dict[str, Any]]) -> str:
    missing: list[dict[str, Any]] = []
    content_folded = html.unescape(content).casefold()
    for target in targets:
        link = str(target.get("link", "")).strip()
        slug = str(target.get("slug", "")).strip()
        title = _plain_title(target)
        if not link or not slug or not title:
            raise ValueError("reviewed target is missing link, slug, or title")
        if link in content:
            continue
        if slug.casefold() not in content_folded and title.casefold() not in content_folded:
            raise ValueError(
                f"source article does not mention reviewed target {int(target['id'])}"
            )
        missing.append(target)
    if not missing:
        return content

    items = "\n".join(
        f'<li><a href="{html.escape(str(target["link"]), quote=True)}">'
        f'{html.escape(_plain_title(target))}</a></li>'
        for target in missing
    )
    if CASE_LINK_MARKER in content:
        marker_at = content.index(CASE_LINK_MARKER)
        list_end = content.find("</ul>", marker_at)
        if list_end < 0:
            raise ValueError("existing reviewed case-link section is malformed")
        return content[:list_end] + items + "\n" + content[list_end:]

    section = (
        f"{CASE_LINK_MARKER}\n"
        '<section class="huntlab-index-cases" '
        'aria-labelledby="huntlab-index-cases-title">\n'
        '<h2 id="huntlab-index-cases-title">진단 대상 글</h2>\n'
        "<p>이번 URL Inspection 비교에 사용한 실제 HuntLab 글이다.</p>\n"
        f"<ul>\n{items}\n</ul>\n</section>\n"
    )
    reference_heading = re.search(r"(?i)<h2[^>]*>\s*참고 링크\s*</h2>", content)
    if reference_heading:
        return content[: reference_heading.start()] + section + content[reference_heading.start() :]
    return content.rstrip() + "\n\n" + section


def _backup_path(kind: str, timestamp: datetime, *, resource: str) -> Path:
    directory = ROOT / "output" / "search-review-backups"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{timestamp:%Y%m%dT%H%M%S%fZ}-{resource}-{kind}.json"


def _append_audit(entry: dict[str, Any]) -> None:
    path = ROOT / "logs" / "search-review-actions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def apply_internal_links(
    client: WordPressClient,
    *,
    source_id: int,
    target_ids: list[int],
    apply: bool,
    approved_by: str,
    timestamp: datetime,
) -> dict[str, Any]:
    source = client.get_post(source_id)
    targets = [client.get_post(target_id) for target_id in target_ids]
    if source.get("status") != "publish" or any(
        target.get("status") != "publish" for target in targets
    ):
        raise ValueError("source and reviewed targets must all be published")
    original = _raw_content(source)
    updated = add_reviewed_case_links(original, targets)
    action = {
        "action": "internal_links",
        "source_id": source_id,
        "target_ids": target_ids,
        "target_urls": [str(target["link"]) for target in targets],
        "status": "already_present" if updated == original else "ready",
    }
    if not apply or updated == original:
        return action

    backup = _backup_path(
        "internal-links", timestamp, resource=f"post-{source_id}"
    )
    backup.write_text(
        json.dumps(
            {
                **action,
                "approved_by": approved_by,
                "original_content": original,
                "updated_content": updated,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client.update_post(source_id, {"content": updated}, status="publish")
    verified = client.get_post(source_id)
    verified_content = _raw_content(verified)
    missing = [url for url in action["target_urls"] if url not in verified_content]
    if missing:
        raise RuntimeError("WordPress update returned without all reviewed links")
    result = {
        **action,
        "status": "applied",
        "applied_at": timestamp.isoformat(),
        "approved_by": approved_by,
        "backup": str(backup.relative_to(ROOT)),
    }
    _append_audit(result)
    return result


def apply_title_experiment(
    client: WordPressClient,
    *,
    post_id: int,
    expected_current_title: str,
    decision: dict[str, Any],
    apply: bool,
    approved_by: str,
    timestamp: datetime,
) -> dict[str, Any]:
    post = client.get_post(post_id)
    if post.get("status") != "publish":
        raise ValueError("title experiment target must be published")
    current_title = _plain_title(post)
    proposed_title = str(decision["proposed_title"])
    if current_title == proposed_title:
        return {
            "action": "title_experiment",
            "post_id": post_id,
            "status": "already_applied",
            "title": proposed_title,
        }
    if current_title != expected_current_title:
        raise ValueError("current WordPress title does not match reviewed baseline")
    original_content = _raw_content(post)
    original_slug = str(post.get("slug", ""))
    action = {
        "action": "title_experiment",
        "post_id": post_id,
        "status": "ready",
        "previous_title": current_title,
        "proposed_title": proposed_title,
        "slug": original_slug,
        "baseline": {
            "clicks": decision["clicks"],
            "impressions": decision["impressions"],
            "position": decision["position"],
        },
        "stop_rule": decision["stop_rule"],
    }
    if not apply:
        return action

    backup = _backup_path(
        "title-experiment", timestamp, resource=f"post-{post_id}"
    )
    backup.write_text(
        json.dumps(
            {
                **action,
                "approved_by": approved_by,
                "content_sha256": hashlib.sha256(
                    original_content.encode("utf-8")
                ).hexdigest(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client.update_post(post_id, {"title": proposed_title}, status="publish")
    verified = client.get_post(post_id)
    if _plain_title(verified) != proposed_title:
        raise RuntimeError("WordPress did not retain the approved experiment title")
    if str(verified.get("slug", "")) != original_slug:
        raise RuntimeError("title experiment unexpectedly changed the public slug")
    if hashlib.sha256(_raw_content(verified).encode("utf-8")).hexdigest() != hashlib.sha256(
        original_content.encode("utf-8")
    ).hexdigest():
        raise RuntimeError("title experiment unexpectedly changed post content")
    result = {
        **action,
        "status": "applied",
        "applied_at": timestamp.isoformat(),
        "approved_by": approved_by,
        "backup": str(backup.relative_to(ROOT)),
    }
    _append_audit(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-date", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--report", type=Path, default=ROOT / "output" / "analytics" / "latest.md"
    )
    parser.add_argument("--internal-link-source-id", type=int)
    parser.add_argument("--internal-link-target-id", type=int, action="append", default=[])
    parser.add_argument("--title-post-id", type=int)
    parser.add_argument("--expected-current-title")
    parser.add_argument("--approved-by", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.internal_link_source_id and not args.title_post_id:
        raise SystemExit("at least one reviewed action is required")
    if args.internal_link_source_id and not args.internal_link_target_id:
        raise SystemExit("internal-link action requires at least one target")
    if args.title_post_id and not args.expected_current_title:
        raise SystemExit("title action requires --expected-current-title")
    if args.apply and not args.approved_by.strip():
        raise SystemExit("--apply requires a non-secret approval reference")

    report = args.report.read_text(encoding="utf-8")
    generated = re.search(r"(?m)^- generated_at: `([^`]+)`$", report)
    if generated is None or datetime.fromisoformat(generated.group(1)).date() != args.review_date:
        raise SystemExit("analytics report date does not match review date")
    decision = (
        parse_title_experiment(report, args.review_date) if args.title_post_id else None
    )
    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    timestamp = datetime.now(UTC)
    results: list[dict[str, Any]] = []
    if args.internal_link_source_id:
        results.append(
            apply_internal_links(
                client,
                source_id=args.internal_link_source_id,
                target_ids=args.internal_link_target_id,
                apply=args.apply,
                approved_by=args.approved_by.strip(),
                timestamp=timestamp,
            )
        )
    if args.title_post_id and decision:
        results.append(
            apply_title_experiment(
                client,
                post_id=args.title_post_id,
                expected_current_title=args.expected_current_title,
                decision=decision,
                apply=args.apply,
                approved_by=args.approved_by.strip(),
                timestamp=timestamp,
            )
        )
    print(json.dumps({"status": "Success", "actions": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
