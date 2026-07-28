#!/usr/bin/env python3
"""Backfill a small, reviewed internal-link graph without rewriting articles."""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient

MARKER = "<!-- huntlab-related-links:v1 -->"
LINKS = {
    67: (63, 37),
    63: (67, 42),
    42: (63, 16),
    37: (67, 24),
    24: (37, 30),
    30: (24, 16),
    16: (50, 30),
    50: (16, 42),
    72: (46, 58),
    46: (72, 58),
    58: (46, 72),
}


def related_section(targets: list[dict]) -> str:
    items = "\n".join(
        f'<li><a href="{html.escape(post["link"], quote=True)}">'
        f'{html.escape(post["title"]["rendered"])}</a></li>'
        for post in targets
    )
    return (
        f"\n\n{MARKER}\n"
        '<section class="huntlab-related-articles" aria-labelledby="huntlab-related-title">\n'
        '<h2 id="huntlab-related-title">함께 읽으면 좋은 글</h2>\n'
        f"<ul>\n{items}\n</ul>\n"
        "</section>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    posts = client.request(
        "GET",
        "posts?status=publish&context=edit&per_page=100",
        expected=(200,),
    )
    by_id = {int(post["id"]): post for post in posts}
    changes = []
    for source_id, target_ids in LINKS.items():
        source = by_id.get(source_id)
        targets = [by_id[target_id] for target_id in target_ids if target_id in by_id]
        if source is None or len(targets) != len(target_ids):
            raise RuntimeError(f"Missing reviewed source/target for post {source_id}")
        content = source["content"]["raw"]
        if MARKER in content:
            continue
        changes.append(
            {
                "post_id": source_id,
                "title": source["title"]["rendered"],
                "original_content": content,
                "updated_content": content.rstrip() + related_section(targets),
                "targets": list(target_ids),
            }
        )

    print(
        json.dumps(
            [
                {
                    "post_id": item["post_id"],
                    "title": item["title"],
                    "targets": item["targets"],
                }
                for item in changes
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.apply:
        return 0

    backup_dir = ROOT / "output" / "internal-link-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    backup.write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in changes:
        client.request(
            "POST",
            f"posts/{item['post_id']}",
            payload={"content": item["updated_content"]},
            expected=(200,),
        )
        print(f"updated post_id={item['post_id']} targets={item['targets']}")
    print(f"backup={backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
