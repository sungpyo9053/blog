#!/usr/bin/env python3
"""Apply one reviewed internal-link discovery action from the Aug-7 report."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient

RELATED_MARKER = "<!-- huntlab-related-links:v1 -->"
ACTION_MARKER_PREFIX = "<!-- huntlab-index-discovery:v1:"


def normalize_url_for_compare(value: str) -> tuple[str, str, str]:
    """Compare equivalent HuntLab URLs independent of percent-hex casing."""
    parsed = urlsplit(value.strip())
    path = unquote(parsed.path)
    if path != "/":
        path = path.rstrip("/") + "/"
    return parsed.scheme.lower(), parsed.netloc.lower(), path


def parse_report(report: str, expected_date: date) -> str:
    generated = re.search(r"(?m)^- generated_at: `([^`]+)`$", report)
    status = re.search(r"(?m)^- index_discovery_action: `([^`]+)`$", report)
    target = re.search(r"(?m)^- index_discovery_target: `([^`]+)`$", report)
    if generated is None or status is None or target is None:
        raise ValueError("current analytics report has no eligible discovery action")
    generated_date = datetime.fromisoformat(generated.group(1)).date()
    if generated_date != expected_date:
        raise ValueError("analytics report date does not match the one-shot review date")
    if status.group(1) != "ELIGIBLE_REVIEW":
        raise ValueError("index discovery action is not eligible")
    url = target.group(1).strip()
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "huntlab.app":
        raise ValueError("discovery target must be an HTTPS HuntLab URL")
    return url


def choose_related_source(posts: list[dict], target: dict) -> tuple[dict, set[int]]:
    target_id = int(target["id"])
    target_tags = {int(value) for value in target.get("tags", [])}
    ranked: list[tuple[int, int, dict, set[int]]] = []
    for post in posts:
        if int(post["id"]) == target_id or post.get("status") != "publish":
            continue
        raw = str(post.get("content", {}).get("raw", ""))
        if target.get("link") in raw or f"{ACTION_MARKER_PREFIX}{target_id} -->" in raw:
            continue
        shared_tags = target_tags & {int(value) for value in post.get("tags", [])}
        if not shared_tags:
            continue
        shared_categories = set(target.get("categories", [])) & set(
            post.get("categories", [])
        )
        ranked.append(
            (
                len(shared_tags),
                len(shared_categories),
                post,
                shared_tags,
            )
        )
    if not ranked:
        raise ValueError("no published source with a shared reviewed tag")
    ranked.sort(key=lambda item: (item[0], item[1], int(item[2]["id"])), reverse=True)
    return ranked[0][2], ranked[0][3]


def add_discovery_link(content: str, target: dict) -> str:
    target_id = int(target["id"])
    marker = f"{ACTION_MARKER_PREFIX}{target_id} -->"
    if marker in content or str(target["link"]) in content:
        return content
    title = html.escape(html.unescape(str(target["title"]["rendered"])))
    link = html.escape(str(target["link"]), quote=True)
    item = f'{marker}\n<li><a href="{link}">{title}</a></li>'
    marker_at = content.find(RELATED_MARKER)
    if marker_at >= 0:
        list_end = content.find("</ul>", marker_at)
        if list_end >= 0:
            return content[:list_end] + item + "\n" + content[list_end:]
    return (
        content.rstrip()
        + "\n\n"
        + marker
        + "\n<section class=\"huntlab-related-articles\" "
        + "aria-labelledby=\"huntlab-related-title\">\n"
        + '<h2 id="huntlab-related-title">함께 읽으면 좋은 글</h2>\n'
        + f"<ul>\n<li><a href=\"{link}\">{title}</a></li>\n</ul>\n"
        + "</section>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--review-date", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--report", type=Path, default=ROOT / "output/analytics/latest.md"
    )
    args = parser.parse_args()
    if datetime.now().astimezone().date() != args.review_date:
        raise SystemExit("one-shot review date is not today")
    target_url = parse_report(
        args.report.read_text(encoding="utf-8"),
        args.review_date,
    )

    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    posts = client.request(
        "GET",
        "posts?status=publish&context=edit&per_page=100",
        expected=(200,),
    )
    normalized_target = normalize_url_for_compare(target_url)
    target = next(
        (
            post
            for post in posts
            if normalize_url_for_compare(str(post.get("link", "")))
            == normalized_target
        ),
        None,
    )
    if target is None:
        raise SystemExit("eligible target is not a published WordPress post")
    source, shared_tags = choose_related_source(posts, target)
    original = str(source["content"]["raw"])
    updated = add_discovery_link(original, target)
    action = {
        "review_date": args.review_date.isoformat(),
        "source_id": int(source["id"]),
        "source_title": source["title"]["rendered"],
        "target_id": int(target["id"]),
        "target_title": target["title"]["rendered"],
        "target_url": target_url,
        "shared_tag_ids": sorted(shared_tags),
        "status": "already_present" if updated == original else "ready",
    }
    print(json.dumps(action, ensure_ascii=False, indent=2))
    if not args.apply or updated == original:
        return 0

    backup_dir = ROOT / "output/index-discovery-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    backup.write_text(
        json.dumps(
            {**action, "original_content": original, "updated_content": updated},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    client.update_post(int(source["id"]), {"content": updated}, status="publish")
    verified = client.get_post(int(source["id"]))
    verified_content = str(verified.get("content", {}).get("raw", ""))
    if target_url not in verified_content:
        raise RuntimeError("WordPress update returned without the reviewed target link")
    audit = ROOT / "logs/index-discovery-actions.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    with audit.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    **action,
                    "status": "applied",
                    "applied_at": datetime.now(UTC).isoformat(),
                    "backup": str(backup.relative_to(ROOT)),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    print(f"applied source_id={source['id']} target_id={target['id']} backup={backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
