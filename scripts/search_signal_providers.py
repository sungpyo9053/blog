"""Optional, non-scraping search signal inputs for the analytics report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
    return {**payload, "status": "AVAILABLE", "rows": rows}


def collect_shadow_signals(
    naver_path: Path | None,
    whereispost_path: Path | None,
) -> dict[str, dict[str, Any]]:
    return {
        "naver": load_naver_searchadvisor(naver_path),
        "whereispost": load_whereispost_shadow(whereispost_path),
    }
