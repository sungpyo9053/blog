#!/usr/bin/env python3
"""Exclude reviewed legacy posts and terms from AIOSEO discovery sitemaps."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient
from scripts.adsense_p0_scope import NOINDEX_CATEGORY_SLUGS, NOINDEX_POST_IDS
from scripts.audit_adsense_content import fetch_all


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()

    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    response = client.request("GET", "options", expected=(200,), namespace="aioseo/v1")
    options = response["options"]
    categories = fetch_all(client, "categories")
    categories_by_slug = {str(row.get("slug", "")): row for row in categories}
    missing = sorted(NOINDEX_CATEGORY_SLUGS - categories_by_slug.keys())
    if missing:
        raise SystemExit(f"refusing: missing categories {missing}")
    term_ids = sorted(int(categories_by_slug[slug]["id"]) for slug in NOINDEX_CATEGORY_SLUGS)

    args.backup.parent.mkdir(parents=True, exist_ok=True)
    args.backup.write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "scope": "aioseo-options-before-adsense-p0",
                "options": options,
                "target_post_ids": sorted(NOINDEX_POST_IDS),
                "target_term_ids": term_ids,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"backup={args.backup} post_ids={len(NOINDEX_POST_IDS)} term_ids={term_ids}")
    if not args.apply:
        print("status=DRY_RUN writes=0")
        return 0

    patch = {
        "sitemap": {
            "general": {
                "advancedSettings": {
                    "enable": True,
                    "excludePosts": sorted(NOINDEX_POST_IDS),
                    "excludeTerms": term_ids,
                }
            }
        }
    }
    result = client.request(
        "POST", "options", payload={"options": patch}, expected=(200,), namespace="aioseo/v1"
    )
    if not result.get("success"):
        raise SystemExit("AIOSEO option update returned success=false")
    after = client.request("GET", "options", expected=(200,), namespace="aioseo/v1")["options"]
    advanced = after["sitemap"]["general"]["advancedSettings"]
    if set(map(int, advanced["excludePosts"])) != NOINDEX_POST_IDS:
        raise SystemExit("post sitemap exclusion verification failed")
    if set(map(int, advanced["excludeTerms"])) != set(term_ids):
        raise SystemExit("term sitemap exclusion verification failed")
    print("status=APPLIED excluded_posts=37 excluded_terms=6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
