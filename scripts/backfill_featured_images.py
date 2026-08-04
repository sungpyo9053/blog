#!/usr/bin/env python3
"""Safely replace reviewed WordPress featured images from a manifest."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient


def load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Manifest must be a non-empty JSON array.")
    required = {"post_id", "slug", "title", "image"}
    seen_ids: set[int] = set()
    for item in data:
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"Manifest item is missing fields: {required}")
        post_id = int(item["post_id"])
        if post_id in seen_ids:
            raise ValueError(f"Duplicate post_id in manifest: {post_id}")
        seen_ids.add(post_id)
        image = (path.parent / str(item["image"])).resolve()
        if not image.is_file():
            raise ValueError(f"Image does not exist for post {post_id}: {image}")
        try:
            from PIL import Image

            with Image.open(image) as opened:
                if opened.size != (1600, 900):
                    raise ValueError(
                        f"Featured image must be 1600x900 for post {post_id}: "
                        f"got {opened.size[0]}x{opened.size[1]}"
                    )
        except OSError as exc:
            raise ValueError(f"Unreadable image for post {post_id}: {image}") from exc
        item["post_id"] = post_id
        item["resolved_image"] = image
    return data


def verify_targets(client: WordPressClient, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for item in items:
        post = client.get_post(item["post_id"])
        if str(post.get("slug", "")) != item["slug"]:
            raise RuntimeError(
                f"Post identity mismatch for {item['post_id']}: "
                f"expected {item['slug']!r}, got {post.get('slug')!r}"
            )
        verified.append(
            {
                **item,
                "old_featured_media": int(post.get("featured_media") or 0),
                "status": str(post.get("status", "")),
            }
        )
    return verified


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    items = load_manifest(manifest_path)
    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    verified = verify_targets(client, items)
    preview = [
        {
            "post_id": item["post_id"],
            "slug": item["slug"],
            "old_featured_media": item["old_featured_media"],
            "image": str(item["resolved_image"]),
        }
        for item in verified
    ]
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    if not args.apply:
        return 0

    backup_dir = ROOT / "output" / "featured-image-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    audit = {"manifest": str(manifest_path), "items": preview, "updates": []}
    backup_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    updated: list[dict[str, Any]] = []
    try:
        for item in verified:
            media = client.upload_media(
                item["resolved_image"],
                alt_text=item["title"],
            )
            client.request(
                "POST",
                f"posts/{item['post_id']}",
                payload={"featured_media": int(media["id"])},
                expected=(200,),
            )
            result = {
                "post_id": item["post_id"],
                "old_featured_media": item["old_featured_media"],
                "new_featured_media": int(media["id"]),
            }
            updated.append(result)
            audit["updates"] = updated
            backup_path.write_text(
                json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"updated post_id={item['post_id']} media_id={media['id']}")
    except Exception:
        for item in reversed(updated):
            client.request(
                "POST",
                f"posts/{item['post_id']}",
                payload={"featured_media": item["old_featured_media"]},
                expected=(200,),
            )
        raise

    print(f"backup={backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
