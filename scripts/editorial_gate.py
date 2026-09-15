"""Deterministic pre-publication checks, not an AdSense approval predictor."""
from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path


def prose(text: str) -> str:
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```|<pre\b.*?</pre>", " ", text, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def style_preservation(before: str, after: str) -> dict:
    """Keep code, URLs, identifiers, quantities and metadata during copy-editing."""
    patterns = {
        "frontmatter": r"\A---\s*\n.*?\n---",
        "code": r"```.*?```|<pre\b.*?</pre>|`[^`\n]+`",
        "urls": r"https?://[^\s<>\)\]\"]+",
        "numbers": r"\d+(?:[.,:/-]\d+)*(?:%|ms|GB|MB)?",
    }
    failures = [key for key, pattern in patterns.items()
                if Counter(re.findall(pattern, before, re.S | re.I)) != Counter(re.findall(pattern, after, re.S | re.I))]
    change = 1 - SequenceMatcher(None, before, after, autojunk=False).ratio()
    if change > .3:
        failures.append("excessive_rewrite")
    if not after.strip():
        failures.append("empty")
    return {"passed": not failures, "failures": failures, "change_ratio": round(change, 4)}


def inspect_article(text: str, inventory: dict, *, now: datetime | None = None, existing_post_id: int | None = None) -> dict:
    """Surface hard failures; semantic quality still requires the Reviewer."""
    failures, duplicates = [], []
    if not isinstance(inventory, dict):
        inventory = {}
    meta = inventory.get("metadata", {})
    if not isinstance(meta, dict):
        meta = {}
    if not meta.get("complete") or not meta.get("full_content"):
        failures.append("incomplete_full_content_inventory")
    try:
        age = ((now or datetime.now(UTC)) - datetime.fromisoformat(meta["collected_at"])).total_seconds()
        if age < -300 or age > 86400:
            failures.append("stale_inventory")
    except (KeyError, TypeError, ValueError):
        failures.append("invalid_inventory_date")
    body = prose(text)
    posts = inventory.get("posts")
    counts = meta.get("statuses")
    valid_rows = isinstance(posts, list) and all(
        isinstance(post, dict) and type(post.get("post_id")) is int
        and post["post_id"] > 0 and isinstance(post.get("content"), str)
        and post.get("status") in {"publish", "draft"} for post in posts
    )
    if not valid_rows:
        failures.append("invalid_inventory_posts")
        posts = []
    elif len({post["post_id"] for post in posts}) != len(posts):
        failures.append("duplicate_inventory_ids")
    actual = {status: sum(post["status"] == status for post in posts) for status in ("publish", "draft")}
    if not isinstance(counts, dict) or any(type(counts.get(status)) is not int or counts[status] != count for status, count in actual.items()):
        failures.append("inventory_status_count_mismatch")
    if not body:
        failures.append("empty_body")
    if re.search(r"물론입니다[!.]|도움이 되셨|요청하신.*정리해|제 지식.*기준", body):
        failures.append("chatbot_framing")
    # Any substantial verbatim passage in another post needs an editorial
    # decision before publication. Exclude code and metadata from comparison.
    # Fixed-width exact strings avoid SequenceMatcher's quadratic behavior on
    # long repetitive Korean prose. Every offset participates; Python sets
    # resolve hash collisions with full string equality, so no matches are lost
    # or invented. Report the confirmed lower bound, not a longest-match claim.
    duplicate_threshold = 180
    windows = {body[offset:offset + duplicate_threshold]
               for offset in range(len(body) - duplicate_threshold + 1)}
    for post in posts:
        if existing_post_id and post.get("post_id") == existing_post_id:
            continue
        other = prose(str(post.get("content", "")))
        if not windows or len(other) < duplicate_threshold:
            continue
        if any(other[offset:offset + duplicate_threshold] in windows
               for offset in range(len(other) - duplicate_threshold + 1)):
            duplicates.append({"post_id": post.get("post_id"),
                               "characters": duplicate_threshold,
                               "characters_is_lower_bound": True})
    if duplicates:
        failures.append("substantial_existing_passage")
    return {"passed": not failures, "failures": failures, "duplicates": duplicates,
            "checked_posts": len(posts),
            "content_sha256": hashlib.sha256(text.encode()).hexdigest()}


def enforce_prepublication(publish_path: Path, inventory_path: Path, *, existing_post_id: int | None = None) -> dict:
    report = inspect_article(publish_path.read_text(encoding="utf-8"), json.loads(inventory_path.read_text(encoding="utf-8")), existing_post_id=existing_post_id)
    (publish_path.parent / "editorial-gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not report["passed"]:
        raise ValueError("editorial gate: " + ", ".join(report["failures"]))
    return report
