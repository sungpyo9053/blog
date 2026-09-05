#!/usr/bin/env python3
"""Update an approved pilot only when Reviewer approval matches immutable bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient

ALLOWED_POSTS = {
    50: "wordpress-rest-api-retry",
    132: "wordpress-rest-api-pagination",
}


def checked_html(path: Path, approval: dict) -> tuple[str, str]:
    raw = path.read_bytes()
    if b"\r" in raw or not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise ValueError("HTML must use LF and end with exactly one newline")
    text = raw.decode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if approval.get("decision") != "APPROVED":
        raise ValueError("Reviewer decision is not APPROVED")
    if approval.get("post_id") not in ALLOWED_POSTS:
        raise ValueError("approval post_id is not an allowed pilot")
    if approval.get("sha256") != digest:
        raise ValueError("Reviewer SHA does not match final HTML bytes")
    return text, digest


def identity(post: dict) -> dict:
    aioseo = post.get("aioseo_meta_data") or {}
    return {
        "id": post.get("id"),
        "slug": post.get("slug"),
        "link": post.get("link"),
        "featured_media": post.get("featured_media"),
        "canonical_url": aioseo.get("canonical_url") or "",
    }


def raw_content(post: dict) -> str:
    content = post.get("content") or {}
    raw = content.get("raw") if isinstance(content, dict) else None
    if not isinstance(raw, str):
        raise RuntimeError("WordPress read-back did not include editable raw content")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--post-id", type=int, choices=sorted(ALLOWED_POSTS), required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    approval = json.loads(args.approval.read_text(encoding="utf-8"))
    html, digest = checked_html(args.html, approval)
    if approval.get("post_id") != args.post_id:
        raise ValueError("CLI post_id does not match Reviewer approval")
    if not args.apply:
        print(
            f"status=DRY_RUN post_id={args.post_id} "
            f"sha256={digest} bytes={len(html.encode('utf-8'))}"
        )
        return 0

    # Freeze the exact approved payload before any WordPress interaction. If
    # the file changed after initial validation, abort with zero API calls.
    html, preflight_digest = checked_html(args.html, approval)
    if preflight_digest != digest:
        raise RuntimeError("HTML changed between validation and WordPress write")

    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    before = client.get_post(args.post_id)
    before_identity = identity(before)
    if before_identity["slug"] != ALLOWED_POSTS[args.post_id]:
        raise RuntimeError(f"unexpected Post {args.post_id} slug")

    client.update_post(
        args.post_id,
        {"title": approval["title"], "content": html},
        status="publish",
    )
    after = client.get_post(args.post_id)
    if identity(after) != before_identity:
        raise RuntimeError("Post ID/URL/slug/media/canonical changed")
    if after.get("status") != "publish":
        raise RuntimeError(f"Post {args.post_id} is not published after update")
    if raw_content(after) != html:
        raise RuntimeError("WordPress read-back content does not match approved HTML")
    print(
        f"status=UPDATED post_id={args.post_id} "
        f"sha256={digest} url={after.get('link')} featured_media={after.get('featured_media')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
