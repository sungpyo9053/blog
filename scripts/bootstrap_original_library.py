#!/usr/bin/env python3
"""Curate verified existing posts into the original technical explainer library.

The command is plan-only by default. ``--apply --yes`` creates the category if
needed, appends it to selected posts without replacing existing taxonomy, and
saves a reversible before-state artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient


DEFAULT_POST_IDS = (619, 622, 629, 637, 644)
CATEGORY_SLUG = "technical-explainer"
CATEGORY_NAME = "기술 해설"
CATEGORY_DESCRIPTION = (
    "검색 수요가 확인된 기술 변화를 코드·설정·비교와 실패 조건까지 "
    "독립 해설로 풀어냅니다."
)


def category_by_slug(client: WordPressClient, slug: str) -> dict[str, Any] | None:
    rows = client.request(
        "GET",
        f"categories?{urlencode({'slug': slug, 'context': 'edit', 'per_page': '100'})}",
        expected=(200,),
    )
    return rows[0] if rows else None


def ensure_category(client: WordPressClient) -> dict[str, Any]:
    existing = category_by_slug(client, CATEGORY_SLUG)
    if existing:
        return existing
    created = client.request(
        "POST",
        "categories",
        payload={"name": CATEGORY_NAME, "slug": CATEGORY_SLUG, "description": CATEGORY_DESCRIPTION},
        expected=(201,),
    )
    if not created or not created.get("id"):
        raise RuntimeError("technical explainer category creation was not verified")
    return created


def build_plan(client: WordPressClient, post_ids: list[int]) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for post_id in post_ids:
        post = client.get_post(post_id)
        plan.append(
            {
                "id": int(post["id"]),
                "slug": str(post.get("slug", "")),
                "status": str(post.get("status", "")),
                "link": str(post.get("link", "")),
                "categories_before": [int(value) for value in post.get("categories", [])],
            }
        )
    return plan


def apply_plan(client: WordPressClient, plan: list[dict[str, Any]], *, backup_dir: Path) -> list[dict[str, Any]]:
    category = ensure_category(client)
    category_id = int(category["id"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"original-library-before-{stamp}.json"
    backup_path.write_text(
        json.dumps(
            {"category_id": category_id, "category_slug": CATEGORY_SLUG, "posts": plan},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    applied: list[dict[str, Any]] = []
    for row in plan:
        categories = list(dict.fromkeys([*row["categories_before"], category_id]))
        updated = client.request(
            "POST", f"posts/{row['id']}", payload={"categories": categories}, expected=(200,)
        )
        actual = [int(value) for value in updated.get("categories", [])]
        if category_id not in actual:
            raise RuntimeError(f"post {row['id']} category verification failed")
        applied.append({**row, "categories_after": actual})
    return applied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--backup-dir", type=Path, default=ROOT / "artifacts" / "wordpress-backups")
    parser.add_argument("--post-id", type=int, action="append", dest="post_ids")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--yes", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    post_ids = args.post_ids or list(DEFAULT_POST_IDS)
    client = WordPressClient(WordPressConfig.from_environment(args.env_file))
    plan = build_plan(client, post_ids)
    if not args.apply:
        print(json.dumps({"mode": "plan", "category": CATEGORY_SLUG, "posts": plan}, ensure_ascii=False, indent=2))
        return 0
    if not args.yes:
        raise SystemExit("--apply requires --yes")
    applied = apply_plan(client, plan, backup_dir=args.backup_dir)
    print(json.dumps({"mode": "applied", "category": CATEGORY_SLUG, "posts": applied}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
