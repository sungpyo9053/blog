#!/usr/bin/env python3
"""Collect the public Google Trends Korea RSS feed into a bounded cache."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = PROJECT_ROOT / "output/search-signals/google-trends-kr.json"
DEFAULT_FEED_URL = "https://trends.google.com/trending/rss?geo=KR"
PROVIDER = "google_trends_kr_rss"
HT_NAMESPACE = "https://trends.google.com/trending/rss"
USER_AGENT = "HuntNews-TrendCollector/1.0 (+https://huntlab.app/)"


class TrendsCollectorError(RuntimeError):
    """Raised when a feed cannot be safely parsed or persisted."""


def normalize_topic(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def parse_approx_traffic(value: str) -> int:
    normalized = value.replace(",", "").replace("+", "").strip().lower()
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([km]?)", normalized)
    if not match:
        raise TrendsCollectorError(f"invalid approximate traffic: {value!r}")
    multiplier = {"": 1, "k": 1_000, "m": 1_000_000}[match.group(2)]
    return int(float(match.group(1)) * multiplier)


def parse_feed(xml_bytes: bytes, *, collected_at: datetime) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise TrendsCollectorError("Google Trends RSS XML is invalid") from exc

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    namespace = {"ht": HT_NAMESPACE}
    for item in root.findall("./channel/item"):
        topic = (item.findtext("title") or "").strip()
        traffic_text = (item.findtext("ht:approx_traffic", namespaces=namespace) or "").strip()
        published_text = (item.findtext("pubDate") or "").strip()
        if not topic or not traffic_text or not published_text:
            continue
        key = normalize_topic(topic)
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            published_at = parsedate_to_datetime(published_text)
        except (TypeError, ValueError) as exc:
            raise TrendsCollectorError(f"invalid RSS pubDate: {published_text!r}") from exc
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)

        news_items: list[dict[str, str]] = []
        news_seen: set[str] = set()
        for news in item.findall("ht:news_item", namespace):
            url = (news.findtext("ht:news_item_url", namespaces=namespace) or "").strip()
            title = (news.findtext("ht:news_item_title", namespaces=namespace) or "").strip()
            source = (news.findtext("ht:news_item_source", namespaces=namespace) or "").strip()
            if not url or not title or url in news_seen:
                continue
            news_seen.add(url)
            news_items.append({"title": title, "url": url, "source": source})

        rows.append(
            {
                "topic": topic,
                "normalized_topic": key,
                "approx_traffic": parse_approx_traffic(traffic_text),
                "traffic_label": traffic_text,
                "published_at": published_at.astimezone(UTC).isoformat(),
                "first_seen_at": collected_at.astimezone(UTC).isoformat(),
                "last_seen_at": collected_at.astimezone(UTC).isoformat(),
                "news_items": news_items,
                "news_source_count": len(
                    {entry["source"].casefold() for entry in news_items if entry["source"]}
                ),
            }
        )
    if not rows:
        raise TrendsCollectorError("Google Trends RSS contained no usable topics")
    return rows


def load_existing(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TrendsCollectorError("existing Google Trends cache is invalid") from exc
    if payload.get("provider") != PROVIDER or not isinstance(payload.get("rows"), list):
        raise TrendsCollectorError("existing Google Trends cache contract mismatch")
    return payload["rows"]


def merge_rows(
    existing: list[dict[str, Any]],
    fresh: list[dict[str, Any]],
    *,
    collected_at: datetime,
    retention_hours: int,
    max_rows: int,
) -> list[dict[str, Any]]:
    cutoff = collected_at.astimezone(UTC) - timedelta(hours=retention_hours)
    merged: dict[str, dict[str, Any]] = {}
    for row in existing:
        key = normalize_topic(str(row.get("normalized_topic") or row.get("topic") or ""))
        try:
            last_seen = datetime.fromisoformat(str(row.get("last_seen_at", "")))
        except ValueError:
            continue
        if key and last_seen.astimezone(UTC) >= cutoff:
            merged[key] = {**row, "normalized_topic": key}

    for row in fresh:
        key = row["normalized_topic"]
        previous = merged.get(key)
        if previous:
            previous_traffic = int(previous.get("approx_traffic", 0))
            fresh_traffic = int(row["approx_traffic"])
            row = {
                **row,
                "first_seen_at": previous.get("first_seen_at", row["first_seen_at"]),
                "approx_traffic": max(previous_traffic, fresh_traffic),
                "traffic_label": (
                    previous.get("traffic_label", row["traffic_label"])
                    if previous_traffic > fresh_traffic
                    else row["traffic_label"]
                ),
            }
        merged[key] = row

    return sorted(
        merged.values(),
        key=lambda row: (
            str(row.get("last_seen_at", "")), int(row.get("approx_traffic", 0))
        ),
        reverse=True,
    )[:max_rows]


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def fetch_feed(url: str, *, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except OSError as exc:
        raise TrendsCollectorError(f"Google Trends RSS request failed: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect Google Trends Korea RSS")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--feed-url", default=DEFAULT_FEED_URL)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retention-hours", type=int, default=48)
    parser.add_argument("--max-rows", type=int, default=300)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    collected_at = datetime.now(UTC)
    try:
        fresh = parse_feed(fetch_feed(args.feed_url, timeout=args.timeout), collected_at=collected_at)
        rows = merge_rows(
            load_existing(args.cache),
            fresh,
            collected_at=collected_at,
            retention_hours=args.retention_hours,
            max_rows=args.max_rows,
        )
        atomic_write(
            args.cache,
            {
                "provider": PROVIDER,
                "geo": "KR",
                "checked_at": collected_at.isoformat(),
                "retention_hours": args.retention_hours,
                "rows": rows,
            },
        )
    except TrendsCollectorError as exc:
        print(f"google_trends_collector status=ERROR cache_preserved=true reason={exc}")
        return 1
    print(
        "google_trends_collector status=SUCCESS "
        f"fresh={len(fresh)} cache_rows={len(rows)} cache={args.cache}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
