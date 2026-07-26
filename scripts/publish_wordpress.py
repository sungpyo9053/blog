#!/usr/bin/env python3
"""Create or publish a HuntLab WordPress post from approved Markdown."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from publisher.config import ConfigurationError, WordPressConfig
from publisher.frontmatter import FrontmatterError, load_document
from publisher.service import DraftPublisher
from publisher.wordpress import WordPressClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Reviewer-approved Markdown and create a WordPress Draft "
            "or published post according to publish_mode."
        )
    )
    parser.add_argument("markdown_file", type=Path)
    parser.add_argument(
        "--reviewer-approved",
        action="store_true",
        help="Confirm that Reviewer approval exists for this exact content.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Environment file to load (default: .env).",
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=Path("logs/publisher-audit.jsonl"),
        help="Append-only JSONL audit log path.",
    )
    parser.add_argument("--review-file", type=Path)
    parser.add_argument("--expected-run-id")
    parser.add_argument("--expected-topic-id")
    parser.add_argument("--expected-source-id")
    parser.add_argument("--expected-category")
    parser.add_argument(
        "--check-existing",
        action="store_true",
        help="Read-only duplicate lookup; do not create or update WordPress resources.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = WordPressConfig.from_environment(args.env_file)
    except ConfigurationError as exc:
        print(
            json.dumps(
                {
                    "status": "Failed",
                    "action": "None",
                    "error_report": {
                        "stage": "configuration",
                        "category": "configuration",
                        "message": str(exc),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    client = WordPressClient(config)
    if args.check_existing:
        try:
            document = load_document(args.markdown_file)
        except FrontmatterError as exc:
            print(json.dumps({"status": "Failed", "message": str(exc)}, ensure_ascii=False))
            return 2
        title = str(document.metadata.get("title", "")).strip()
        slug = str(document.metadata.get("slug", "")).strip()
        matches: dict[int, dict[str, object]] = {}
        for post in client.find_posts(title=title):
            matches[int(post["id"])] = post
        if slug:
            for post in client.find_posts(slug=slug):
                matches[int(post["id"])] = post
        safe_matches = []
        for post_id, post in matches.items():
            content_value = post.get("content", {})
            content = (
                content_value.get("raw") or content_value.get("rendered") or ""
                if isinstance(content_value, dict)
                else str(content_value or "")
            )
            safe_matches.append({
                "id": post_id,
                "status": post.get("status"),
                "slug": post.get("slug"),
                "title": (
                    post.get("title", {}).get("raw")
                    or post.get("title", {}).get("rendered")
                    if isinstance(post.get("title"), dict)
                    else post.get("title")
                ),
                "link": post.get("link"),
                "modified_gmt": post.get("modified_gmt"),
                "featured_media": post.get("featured_media"),
                "category_ids": post.get("categories", []),
                "tag_ids": post.get("tags", []),
                "body_image_count": content.count("<img "),
                "contains_local_image_path": "./images/" in content,
                "content_length": len(content),
            })
        print(
            json.dumps(
                {"status": "Success", "action": "ReadOnlyCheck", "matches": safe_matches},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    publisher = DraftPublisher(
        client,
        audit_log=args.audit_log,
    )
    result = publisher.publish_file(
        args.markdown_file,
        reviewer_approved=args.reviewer_approved,
        review_path=args.review_file,
        expected_identity={
            "run_id": args.expected_run_id or "",
            "topic_id": args.expected_topic_id or "",
            "source_id": args.expected_source_id or "",
            "category": args.expected_category or "",
        },
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.status == "Success" else 1


if __name__ == "__main__":
    sys.exit(main())
