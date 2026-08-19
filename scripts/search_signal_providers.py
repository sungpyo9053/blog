"""Optional, non-scraping search signal inputs for the analytics report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOOGLE_TRENDS_CACHE = (
    PROJECT_ROOT / "output/search-signals/google-trends-kr.json"
)


class SearchSignalError(ValueError):
    """Raised when an optional shadow-mode export is malformed."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SearchSignalError(f"invalid shadow export: {path.name}") from exc
    if not isinstance(payload, dict):
        raise SearchSignalError(f"shadow export must be an object: {path.name}")
    return payload


def load_naver_searchadvisor(path: Path | None) -> dict[str, Any]:
    """Load an owner-provided Search Advisor export without browser automation."""
    if path is None or not path.is_file():
        return {
            "provider": "naver_searchadvisor",
            "status": "N/A",
            "reason": "owner_export_or_supported_api_required",
            "rows": [],
        }
    payload = _load_json(path)
    if payload.get("provider") != "naver_searchadvisor":
        raise SearchSignalError("naver provider mismatch")
    if not str(payload.get("checked_at", "")).strip():
        raise SearchSignalError("naver checked_at is required")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise SearchSignalError("naver rows must be a list")
    return {**payload, "status": "AVAILABLE", "rows": rows}


def load_whereispost_shadow(path: Path | None) -> dict[str, Any]:
    """Load manually supplied Keyword Master observations; never scrape the UI."""
    if path is None or not path.is_file():
        return {
            "provider": "whereispost_keywordmaster",
            "status": "N/A",
            "reason": "official_automation_api_unverified_no_scraping",
            "rows": [],
        }
    payload = _load_json(path)
    if payload.get("provider") != "whereispost_keywordmaster":
        raise SearchSignalError("whereispost provider mismatch")
    if not str(payload.get("checked_at", "")).strip():
        raise SearchSignalError("whereispost checked_at is required")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise SearchSignalError("whereispost rows must be a list")
    required = {"keyword", "pc_searches", "mobile_searches", "documents"}
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not required.issubset(row):
            raise SearchSignalError(f"whereispost row {index} is incomplete")
        if not str(row["keyword"]).strip():
            raise SearchSignalError(f"whereispost row {index} keyword is empty")
        for field in ("pc_searches", "mobile_searches", "documents"):
            if not isinstance(row[field], int) or row[field] < 0:
                raise SearchSignalError(f"whereispost row {index} {field} is invalid")
        if "total_searches" in row and row["total_searches"] != (
            row["pc_searches"] + row["mobile_searches"]
        ):
            raise SearchSignalError(f"whereispost row {index} total_searches mismatch")
        if "competition_ratio" in row and (
            not isinstance(row["competition_ratio"], (int, float))
            or row["competition_ratio"] < 0
        ):
            raise SearchSignalError(
                f"whereispost row {index} competition_ratio is invalid"
            )
    return {**payload, "status": "AVAILABLE", "rows": rows}


def load_google_trends_cache(path: Path | None) -> dict[str, Any]:
    """Load the bounded, public Google Trends Korea RSS cache."""
    if path is None or not path.is_file():
        return {
            "provider": "google_trends_kr_rss",
            "status": "N/A",
            "reason": "hourly_cache_unavailable",
            "rows": [],
        }
    payload = _load_json(path)
    if payload.get("provider") != "google_trends_kr_rss":
        raise SearchSignalError("Google Trends provider mismatch")
    if payload.get("geo") != "KR" or not str(payload.get("checked_at", "")).strip():
        raise SearchSignalError("Google Trends geo and checked_at are required")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise SearchSignalError("Google Trends rows must be a list")
    required = {
        "topic",
        "normalized_topic",
        "approx_traffic",
        "published_at",
        "first_seen_at",
        "last_seen_at",
        "news_items",
    }
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not required.issubset(row):
            raise SearchSignalError(f"Google Trends row {index} is incomplete")
        if not str(row["topic"]).strip():
            raise SearchSignalError(f"Google Trends row {index} topic is empty")
        if not isinstance(row["approx_traffic"], int) or row["approx_traffic"] < 0:
            raise SearchSignalError(f"Google Trends row {index} traffic is invalid")
        if not isinstance(row["news_items"], list):
            raise SearchSignalError(f"Google Trends row {index} news_items is invalid")
    return {**payload, "status": "AVAILABLE", "rows": rows}


def collect_shadow_signals(
    naver_path: Path | None,
    whereispost_path: Path | None,
) -> dict[str, dict[str, Any]]:
    return {
        "naver": load_naver_searchadvisor(naver_path),
        "whereispost": load_whereispost_shadow(whereispost_path),
    }
