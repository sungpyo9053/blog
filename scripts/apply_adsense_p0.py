#!/usr/bin/env python3
"""Apply the reversible Hunt News AdSense P0 indexing boundary.

This command never changes post content, identity, slugs, media, categories, or
canonical URLs.  It only writes AIOSEO robots metadata to the reviewed posts
and legacy category archives.  The default mode is a read-only preflight.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient
from scripts.adsense_p0_scope import NOINDEX_CATEGORY_SLUGS, NOINDEX_POST_IDS
from scripts.audit_adsense_content import fetch_all

ROBOTS_PATCH = {
    # AIOSEO's write contract uses editor keys; its read model exposes the
    # corresponding robots_* columns.
    "default": False,
    "noindex": True,
    "nofollow": False,
}


def stable_post_identity(post: dict[str, Any]) -> dict[str, Any]:
    content = str((post.get("content") or {}).get("raw", ""))
    return {
        "id": int(post["id"]),
        "slug": str(post.get("slug", "")),
        "link": str(post.get("link", "")),
        "featured_media": int(post.get("featured_media", 0)),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "canonical_url": (post.get("aioseo_meta_data") or {}).get("canonical_url"),
    }


def build_backup(
    posts: list[dict[str, Any]], categories: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "adsense-p0-before",
        "posts": posts,
        "categories": categories,
        "target_post_ids": sorted(NOINDEX_POST_IDS),
        "target_category_slugs": sorted(NOINDEX_CATEGORY_SLUGS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()

    if len(NOINDEX_POST_IDS) != 37:
        raise SystemExit("refusing: expected exactly 37 reviewed post IDs")
    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    posts = fetch_all(client, "posts", status="publish")
    categories = fetch_all(client, "categories")
    posts_by_id = {int(row["id"]): row for row in posts}
    categories_by_slug = {str(row.get("slug", "")): row for row in categories}
    missing_posts = sorted(NOINDEX_POST_IDS - posts_by_id.keys())
    missing_categories = sorted(NOINDEX_CATEGORY_SLUGS - categories_by_slug.keys())
    if missing_posts or missing_categories:
        raise SystemExit(
            f"refusing: missing_posts={missing_posts} missing_categories={missing_categories}"
        )

    args.backup.parent.mkdir(parents=True, exist_ok=True)
    backup = build_backup(posts, categories)
    args.backup.write_text(
        json.dumps(backup, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    before = {post_id: stable_post_identity(posts_by_id[post_id]) for post_id in NOINDEX_POST_IDS}
    print(f"backup={args.backup} posts={len(posts)} targets={len(NOINDEX_POST_IDS)}")
    if not args.apply:
        print("status=DRY_RUN writes=0")
        return 0

    for post_id in sorted(NOINDEX_POST_IDS):
        client.request(
            "POST",
            "post",
            payload={"id": post_id, **ROBOTS_PATCH},
            expected=(200,),
            namespace="aioseo/v1",
        )

    verified = {post_id: client.get_post(post_id) for post_id in sorted(NOINDEX_POST_IDS)}
    mismatches = [
        post_id
        for post_id, post in verified.items()
        if stable_post_identity(post) != before[post_id]
    ]
    noindex_failures = [
        post_id
        for post_id, post in verified.items()
        if not bool((post.get("aioseo_meta_data") or {}).get("robots_noindex"))
        or bool((post.get("aioseo_meta_data") or {}).get("robots_nofollow"))
    ]
    if mismatches or noindex_failures:
        raise SystemExit(
            f"verification failed: identity={mismatches} robots={noindex_failures}"
        )
    print("status=APPLIED post_noindex=37 post_nofollow=0 identity_mismatches=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
