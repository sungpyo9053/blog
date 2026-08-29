#!/usr/bin/env python3
"""Build the public-safe Hunt Brief run manifest.

The manifest joins observed collection state, deterministic selection artifacts,
and successful WordPress publication events. It never controls publication and
is therefore safe to generate or sync as a non-blocking observer.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from scripts.daily_briefing import (
    contains_hangul,
    DailyBriefingError,
    load_daily_briefing,
    required_source_translation_urls,
)
from scripts.collect_editorial_sources import normalize_source_config, matches_source_relevance


CONTRACT_VERSION = "briefing-manifest.v1"
MAX_PUBLIC_TOPICS = 7
MAX_PUBLIC_SOURCE_ITEMS = 60
EDITORIAL_CATEGORY_ORDER = (
    "AI/ML 핵심",
    "개발 트렌드",
    "AI 공식 블로그",
    "국내 IT",
    "국내 시사",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(str(value or "0").replace(",", "").strip()))
    except (TypeError, ValueError):
        return 0


def _source_domains(*values: Any) -> list[str]:
    domains: set[str] = set()
    for value in values:
        for url in re.findall(r"https?://[^\s,;)<>\]]+", str(value or "")):
            host = (urlsplit(url).hostname or "").lower()
            if host:
                domains.add(host.removeprefix("www."))
    return sorted(domains)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def collect_run_publications(run_directory: Path) -> list[dict[str, Any]]:
    """Read successful Publisher events without trusting service exit status."""
    publications: list[dict[str, Any]] = []
    for audit_path in sorted(run_directory.glob("*/publisher-audit.jsonl")):
        context = load_json(audit_path.parent / "planner-context.json")
        successful: list[dict[str, Any]] = []
        try:
            lines = audit_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                event.get("event") in {"post_published", "post_updated"}
                and event.get("status") == "Success"
                and event.get("post_id")
                and event.get("published_url")
            ):
                successful.append(event)
        if not successful:
            continue
        event = successful[-1]
        publications.append(
            {
                "run_id": str(context.get("run_id", "")),
                "topic_id": str(context.get("topic_id", audit_path.parent.name)),
                "title": str(context.get("title", "")),
                "category": str(context.get("category", "")),
                "post_id": int(event["post_id"]),
                "url": str(event["published_url"]),
                "published_at": str(event.get("timestamp", "")),
            }
        )
    publications.sort(key=lambda item: (item["published_at"], item["post_id"]))
    return publications


def _collection_summary(cache_path: Path) -> dict[str, Any]:
    payload = load_json(cache_path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    topics: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in sorted(
        rows,
        key=lambda item: (
            _nonnegative_int(item.get("approx_traffic")),
            str(item.get("last_seen_at", "")),
        ),
        reverse=True,
    ):
        topic = str(row.get("topic", "")).strip()
        normalized = topic.casefold()
        if not topic or normalized in seen:
            continue
        seen.add(normalized)
        topics.append(
            {
                "topic": topic,
                "approx_traffic": _nonnegative_int(row.get("approx_traffic")),
                "last_seen_at": str(row.get("last_seen_at", "")),
                "news_source_count": _nonnegative_int(row.get("news_source_count")),
            }
        )
        if len(topics) >= MAX_PUBLIC_TOPICS:
            break
    return {
        "provider": str(payload.get("provider", "google_trends_kr_rss")),
        "checked_at": str(payload.get("checked_at", "")),
        "retention_hours": _nonnegative_int(payload.get("retention_hours")),
        "observed_topic_count": len(rows),
        "top_topics": topics,
    }


def _collection_health(collection: Mapping[str, Any], generated: datetime) -> dict[str, Any]:
    checked_at = str(collection.get("checked_at", ""))
    try:
        checked = datetime.fromisoformat(checked_at).astimezone(UTC)
    except (TypeError, ValueError):
        return {"status": "unavailable", "age_minutes": 0}
    age_minutes = max(0, int((generated - checked).total_seconds() // 60))
    return {
        "status": "fresh" if age_minutes <= 120 else "stale",
        "age_minutes": age_minutes,
    }


def _editorial_source_summary(
    cache_path: Path | None,
    preferred_urls: set[str] | None = None,
    translated_urls: set[str] | None = None,
) -> dict[str, Any]:
    payload = load_json(cache_path) if cache_path else {}
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    preferred_urls = preferred_urls or set()
    category_rows: dict[str, list[dict[str, str]]] = {
        category: [] for category in EDITORIAL_CATEGORY_ORDER
    }
    other_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        normalized_source = normalize_source_config({
            "category": row.get("category", ""),
            "name": row.get("source", ""),
            "relevance_profile": row.get("relevance_profile", ""),
        })
        if not matches_source_relevance(str(row.get("title", "")), normalized_source):
            continue
        url = str(row.get("url", "")).strip()
        title = str(row.get("title", "")).strip()
        if not url.startswith("https://") or not title or url in seen:
            continue
        if (
            translated_urls is not None
            and not contains_hangul(title)
            and url not in translated_urls
            and url not in preferred_urls
        ):
            continue
        seen.add(url)
        safe_row = {
            "category": str(normalized_source.get("category", ""))[:40],
            "source": str(row.get("source", ""))[:80],
            "title": title[:300], "url": url,
            "published_at": str(row.get("published_at", ""))[:40],
        }
        if safe_row["category"] in category_rows:
            category_rows[safe_row["category"]].append(safe_row)
        else:
            other_rows.append(safe_row)
    safe_rows: list[dict[str, str]] = []
    round_index = 0
    while len(safe_rows) < MAX_PUBLIC_SOURCE_ITEMS:
        added = False
        for category in EDITORIAL_CATEGORY_ORDER:
            bucket = category_rows[category]
            if round_index < len(bucket):
                safe_rows.append(bucket[round_index])
                added = True
                if len(safe_rows) >= MAX_PUBLIC_SOURCE_ITEMS:
                    break
        if not added:
            break
        round_index += 1
    if len(safe_rows) < MAX_PUBLIC_SOURCE_ITEMS:
        safe_rows.extend(other_rows[: MAX_PUBLIC_SOURCE_ITEMS - len(safe_rows)])
    safe_by_url = {row["url"]: row for row in safe_rows}
    eligible_by_url = {
        row["url"]: row
        for bucket in category_rows.values()
        for row in bucket
    }
    eligible_by_url.update({row["url"]: row for row in other_rows})
    for preferred_url in sorted(preferred_urls):
        if preferred_url in safe_by_url or preferred_url not in eligible_by_url:
            continue
        replacement_index = next(
            (
                index
                for index in range(len(safe_rows) - 1, -1, -1)
                if safe_rows[index]["url"] not in preferred_urls
            ),
            None,
        )
        if replacement_index is None:
            break
        safe_rows[replacement_index] = eligible_by_url[preferred_url]
        safe_by_url = {row["url"]: row for row in safe_rows}
    return {
        "provider": str(payload.get("provider", "hunt_news_editorial_sources")),
        "checked_at": str(payload.get("checked_at", "")),
        "source_snapshot_hash": str(payload.get("source_snapshot_hash", "")),
        "successful_source_count": _nonnegative_int(payload.get("successful_source_count")),
        "source_count": _nonnegative_int(payload.get("source_count")),
        "items": safe_rows,
    }


def build_briefing_manifest(
    *,
    run_id: str,
    plan_document: Mapping[str, Any],
    publications: Sequence[Mapping[str, Any]],
    trends_cache_path: Path,
    editorial_source_cache_path: Path | None = None,
    shadow_path: Path,
    fallback_path: Path,
    daily_briefing_path: Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = (generated_at or datetime.now(UTC)).astimezone(UTC)
    candidates = [dict(item) for item in plan_document.get("candidates", [])]
    candidate_by_title = {
        str(item.get("title", "")): item for item in candidates if item.get("title")
    }
    legacy_top2 = [
        str(item.get("title", "")) for item in plan_document.get("top2", [])
    ]
    shadow = load_json(shadow_path)
    fallback = load_json(fallback_path)
    collection = _collection_summary(trends_cache_path)
    collection.update(_collection_health(collection, generated))
    raw_analysis = load_json(daily_briefing_path) if daily_briefing_path else {}
    preferred_source_urls = {
        str(row.get("source_url") or "").strip()
        for row in raw_analysis.get("must_read", [])
        if isinstance(row, Mapping)
        and str(row.get("source_url") or "").startswith("https://")
    }
    translated_source_urls = {
        str(row.get("source_url") or "").strip()
        for row in raw_analysis.get("source_title_translations", [])
        if isinstance(row, Mapping)
        and str(row.get("source_url") or "").startswith("https://")
    }
    editorial_sources = _editorial_source_summary(
        editorial_source_cache_path,
        preferred_urls=preferred_source_urls,
        translated_urls=translated_source_urls if raw_analysis else None,
    )
    analysis: dict[str, Any] = {}
    if daily_briefing_path:
        try:
            analysis = load_daily_briefing(
                daily_briefing_path,
                source_snapshot_hash=editorial_sources.get("source_snapshot_hash", ""),
                required_translation_urls=required_source_translation_urls(
                    list(editorial_sources.get("items", []))
                ),
                source_rows=list(editorial_sources.get("items", [])),
            )
        except DailyBriefingError:
            analysis = {}

    legacy_order = {title: index for index, title in enumerate(legacy_top2)}
    ordered_publications = sorted(
        publications,
        key=lambda item: (
            legacy_order.get(str(item.get("title", "")), len(legacy_order)),
            str(item.get("published_at", "")),
        ),
    )
    public_posts: list[dict[str, Any]] = []
    used_post_ids: set[int] = set()
    for publication in ordered_publications:
        publication_run_id = str(publication.get("run_id", ""))
        post_id = _nonnegative_int(publication.get("post_id"))
        if (publication_run_id and publication_run_id != run_id) or not post_id:
            continue
        if post_id in used_post_ids:
            continue
        used_post_ids.add(post_id)
        title = str(publication.get("title", ""))
        candidate = candidate_by_title.get(title, {})
        domains = _source_domains(
            candidate.get("sources"),
            candidate.get("evidence_plan"),
            candidate.get("demand_signal_source"),
        )
        public_posts.append(
            {
                "run_id": run_id,
                "topic_id": str(publication.get("topic_id", "")),
                "post_id": post_id,
                "url": str(publication.get("url", "")),
                "published_at": str(publication.get("published_at", "")),
                "title": title,
                "category": str(publication.get("category") or candidate.get("category", "")),
                "primary_keyword": str(candidate.get("primary_keyword", "")),
                "selection_track": str(candidate.get("selection_track", "legacy")),
                "selection_reason": str(candidate.get("reason", "")),
                "reader_action": str(
                    candidate.get("reader_action") or candidate.get("user_action", "")
                ),
                "life_impact": str(candidate.get("life_impact", "")),
                "effective_date": str(candidate.get("effective_date", "")),
                "google_trends_approx_traffic": _nonnegative_int(
                    candidate.get("google_trends_approx_traffic")
                ),
                "whereispost_total_searches": _nonnegative_int(
                    candidate.get("whereispost_total_searches")
                ),
                "source_count": len(domains),
                "source_domains": domains,
            }
        )

    selection = {
        "candidate_count": len(candidates),
        "legacy_top2": legacy_top2,
        "shadow_top2": shadow.get("shadow_top2", []),
        "overlap_count": _nonnegative_int(shadow.get("overlap_count")),
        "shadow_status": str(shadow.get("status", "unavailable")),
        "fallback_used": bool(fallback.get("replacements")),
    }
    source_contract = {
        "run_id": run_id,
        "candidate_count": len(candidates),
        "legacy_top2": legacy_top2,
        "publication_ids": [item["post_id"] for item in public_posts],
        "collection_checked_at": collection["checked_at"],
        "shadow_source_snapshot_hash": shadow.get("source_snapshot_hash", ""),
    }
    analysis_complete = bool(analysis)
    publications_complete = len(public_posts) == 2
    return {
        "contract_version": CONTRACT_VERSION,
        "generated_at": generated.isoformat(),
        "run_id": run_id,
        "complete": analysis_complete and publications_complete,
        "completion": {
            "analysis_complete": analysis_complete,
            "publications_complete": publications_complete,
            "published_count": len(public_posts),
        },
        "source_snapshot_hash": _sha256(source_contract),
        "collection": collection,
        "editorial_sources": editorial_sources,
        "analysis": analysis,
        "selection": selection,
        "published": public_posts,
    }


def atomic_write_manifest(path: Path, payload: Mapping[str, Any]) -> None:
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
