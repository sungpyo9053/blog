#!/usr/bin/env python3
"""Collect the configured technology-news RSS/Atom feeds into one bounded cache."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
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
DEFAULT_CONFIG = PROJECT_ROOT / "config/editorial-sources.json"
DEFAULT_CACHE = PROJECT_ROOT / "output/search-signals/editorial-sources.json"
PROVIDER = "hunt_news_editorial_sources"
CONTRACT_VERSION = "editorial-source-cache.v1"
USER_AGENT = "HuntNews-SourceCollector/1.0 (+https://huntlab.app/)"


class EditorialSourceError(RuntimeError):
    pass


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _text(node: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", "" if node is None else "".join(node.itertext())).strip()


def _published(value: str, fallback: datetime) -> str:
    value = value.strip()
    if value:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                parsed = fallback
    else:
        parsed = fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def parse_feed(data: bytes, source: dict[str, str], *, collected_at: datetime, limit: int = 20) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise EditorialSourceError(f"{source['name']}: invalid XML") from exc
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    entries = root.findall("./channel/item")
    if not entries:
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
    for entry in entries:
        title = _text(entry.find("title")) or _text(entry.find("{http://www.w3.org/2005/Atom}title"))
        link = _text(entry.find("link"))
        atom_link = entry.find("{http://www.w3.org/2005/Atom}link")
        if not link and atom_link is not None:
            link = (atom_link.attrib.get("href") or "").strip()
        if not title or not link or link in seen:
            continue
        seen.add(link)
        published = (
            _text(entry.find("pubDate"))
            or _text(entry.find("{http://www.w3.org/2005/Atom}published"))
            or _text(entry.find("{http://www.w3.org/2005/Atom}updated"))
        )
        rows.append({
            "category": source["category"], "source": source["name"],
            "title": title[:300], "url": link, "published_at": _published(published, collected_at),
            "collected_at": collected_at.astimezone(UTC).isoformat(),
        })
        if len(rows) >= limit:
            break
    if not rows:
        raise EditorialSourceError(f"{source['name']}: no usable entries")
    return rows


def fetch_source(source: dict[str, str], *, collected_at: datetime, timeout: float, limit: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    request = urllib.request.Request(source["feed_url"], headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            rows = parse_feed(response.read(2_000_000), source, collected_at=collected_at, limit=limit)
    except (OSError, ValueError, EditorialSourceError) as exc:
        return ({"category": source["category"], "name": source["name"], "status": "ERROR", "reason": str(exc)[:180]}, [])
    return ({"category": source["category"], "name": source["name"], "status": "SUCCESS", "item_count": len(rows)}, rows)


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def _previous_rows(cache_path: Path) -> list[dict[str, Any]]:
    if not cache_path.is_file():
        return []
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if payload.get("provider") != PROVIDER or payload.get("contract_version") != CONTRACT_VERSION:
        return []
    return [row for row in payload.get("rows", []) if isinstance(row, dict)]


def collect(config_path: Path, cache_path: Path, *, now: datetime | None = None, timeout: float = 15.0, per_source: int = 20, max_rows: int = 300) -> dict[str, Any]:
    collected_at = (now or datetime.now(UTC)).astimezone(UTC)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise EditorialSourceError("source registry is empty")
    results: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(sources))) as executor:
        futures = [executor.submit(fetch_source, source, collected_at=collected_at, timeout=timeout, limit=per_source) for source in sources]
        for future in futures:
            results.append(future.result())
    statuses = [result[0] for result in results]
    successful_names = {row["name"] for row in statuses if row["status"] == "SUCCESS"}
    failed_names = {row["name"] for row in statuses if row["status"] == "ERROR"}
    rows = [row for _, items in results for row in items]
    fallback_rows = [
        row for row in _previous_rows(cache_path)
        if row.get("source") in failed_names and row.get("source") not in successful_names
    ]
    if fallback_rows:
        rows.extend(fallback_rows)
        fallback_names = {str(row.get("source", "")) for row in fallback_rows}
        for status in statuses:
            if status["status"] == "ERROR" and status["name"] in fallback_names:
                status["fallback"] = "LAST_GOOD_CACHE"
    rows.sort(key=lambda row: (row["published_at"], row["source"], row["url"]), reverse=True)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    cutoff = collected_at - timedelta(hours=72)
    for row in rows:
        if row["url"] in seen or datetime.fromisoformat(row["published_at"]) < cutoff:
            continue
        seen.add(row["url"]); deduped.append(row)
        if len(deduped) >= max_rows: break
    if not deduped:
        raise EditorialSourceError("all editorial sources failed")
    payload = {"provider": PROVIDER, "contract_version": CONTRACT_VERSION, "checked_at": collected_at.isoformat(), "retention_hours": 72, "source_count": len(sources), "successful_source_count": sum(row["status"] == "SUCCESS" for row in statuses), "fallback_source_count": sum(row.get("fallback") == "LAST_GOOD_CACHE" for row in statuses), "sources": statuses, "rows": deduped}
    payload["source_snapshot_hash"] = canonical_hash(deduped)
    atomic_write(cache_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    try:
        payload = collect(args.config, args.cache)
    except (OSError, ValueError, json.JSONDecodeError, EditorialSourceError) as exc:
        print(f"editorial_source_collector status=ERROR cache_preserved=true reason={exc}")
        return 1
    print(f"editorial_source_collector status=SUCCESS sources={payload['successful_source_count']}/{payload['source_count']} rows={len(payload['rows'])} hash={payload['source_snapshot_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
