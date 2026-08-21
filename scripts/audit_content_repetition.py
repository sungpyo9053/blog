#!/usr/bin/env python3
"""Audit material repetition across public Hunt News posts."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "output" / "audits" / "content-repetition-latest.json"
STANDARD_HEADINGS = {"20초 핵심 요약", "핵심 요약", "한눈에 보기", "참고", "함께 읽기"}
NEAR_DUPLICATE_THRESHOLD = 0.72


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paragraphs: list[str] = []
        self.headings: list[str] = []
        self._capture: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "h2"}:
            self._capture = tag
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != self._capture:
            return
        value = normalize_text(" ".join(self._parts))
        if value:
            (self.paragraphs if tag == "p" else self.headings).append(value)
        self._capture = None
        self._parts = []


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def fingerprint(values: list[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()


def shingles(values: list[str], width: int = 5) -> set[str]:
    normalized = re.sub(r"[^0-9a-z가-힣]+", "", " ".join(values).casefold())
    if len(normalized) < width:
        return {normalized} if normalized else set()
    return {normalized[index : index + width] for index in range(len(normalized) - width + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def near_duplicate_pairs(
    rows: list[dict[str, Any]], field: str, *, threshold: float = NEAR_DUPLICATE_THRESHOLD
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for left_index, left in enumerate(rows):
        left_shingles = shingles(left[field])
        for right in rows[left_index + 1 :]:
            similarity = jaccard(left_shingles, shingles(right[field]))
            if similarity < threshold:
                continue
            pairs.append(
                {
                    "similarity": round(similarity, 4),
                    "left": {"id": left["id"], "title": left["title"], "link": left["link"]},
                    "right": {"id": right["id"], "title": right["title"], "link": right["link"]},
                }
            )
    return sorted(pairs, key=lambda pair: pair["similarity"], reverse=True)


def extract_structure(rendered: str) -> dict[str, Any]:
    parser = StructureParser()
    parser.feed(rendered)
    headings = [heading for heading in parser.headings if heading not in STANDARD_HEADINGS]
    intro = parser.paragraphs[:2]
    conclusion = parser.paragraphs[-2:]
    return {
        "intro": intro,
        "headings": headings,
        "conclusion": conclusion,
        "intro_fingerprint": fingerprint(intro),
        "heading_fingerprint": fingerprint(headings),
        "conclusion_fingerprint": fingerprint(conclusion),
    }


def duplicate_groups(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[field])].append(row)
    return [
        {
            "fingerprint": key,
            "count": len(group),
            "posts": [{"id": row["id"], "title": row["title"], "link": row["link"]} for row in group],
        }
        for key, group in grouped.items()
        if len(group) > 1
    ]


def analyze_posts(posts: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for post in posts:
        structure = extract_structure(str(post.get("content", {}).get("rendered", "")))
        rows.append(
            {
                "id": int(post["id"]),
                "title": normalize_text(str(post.get("title", {}).get("rendered", ""))),
                "link": str(post.get("link", "")),
                **structure,
            }
        )
    duplicate_intros = duplicate_groups(rows, "intro_fingerprint")
    duplicate_headings = duplicate_groups(rows, "heading_fingerprint")
    duplicate_conclusions = duplicate_groups(rows, "conclusion_fingerprint")
    near_duplicate_intros = near_duplicate_pairs(rows, "intro")
    near_duplicate_headings = near_duplicate_pairs(rows, "headings")
    near_duplicate_conclusions = near_duplicate_pairs(rows, "conclusion")
    return {
        "contract_version": "content-repetition-audit.v1",
        "post_count": len(rows),
        "standard_headings_excluded": sorted(STANDARD_HEADINGS),
        "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
        "duplicate_intro_groups": duplicate_intros,
        "duplicate_heading_flow_groups": duplicate_headings,
        "duplicate_conclusion_groups": duplicate_conclusions,
        "near_duplicate_intro_pairs": near_duplicate_intros,
        "near_duplicate_heading_flow_pairs": near_duplicate_headings,
        "near_duplicate_conclusion_pairs": near_duplicate_conclusions,
        "risk_post_ids": sorted(
            {
                post["id"]
                for groups in (duplicate_intros, duplicate_headings, duplicate_conclusions)
                for group in groups
                for post in group["posts"]
            }
            | {
                side["id"]
                for pairs in (
                    near_duplicate_intros,
                    near_duplicate_headings,
                    near_duplicate_conclusions,
                )
                for pair in pairs
                for side in (pair["left"], pair["right"])
            }
        ),
    }


def fetch_public_posts(base_url: str) -> list[dict[str, Any]]:
    url = (
        base_url.rstrip("/")
        + "/wp-json/wp/v2/posts?per_page=100&status=publish&_fields=id,link,title,content"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "HuntNews-RepetitionAudit/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit material repetition across Hunt News")
    parser.add_argument("--base-url", default="https://huntlab.app")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        **analyze_posts(fetch_public_posts(args.base_url)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
