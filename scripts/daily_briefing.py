#!/usr/bin/env python3
"""Validate the evidence-backed daily briefing analysis artifact."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.collect_editorial_sources import matches_source_relevance, normalize_source_config


CONTRACT_VERSION = "daily-briefing-analysis.v1"
CATEGORIES = {"AI/ML 핵심", "개발 트렌드", "AI 공식 블로그", "국내 IT", "국내 시사"}
TONES = {"green", "amber", "red", "violet"}
DIRECTIONS = {"up", "down", "stable"}
QUADRANTS = {"focus", "future", "apply", "watch"}
HORIZONS = {"today", "week", "month", "year"}
RETROSPECTIVE_STATUSES = {"baseline", "available"}
RETROSPECTIVE_VERDICTS = {"confirmed", "changed", "unresolved"}
SIGNAL_CONTINUITIES = {"new", "follow_up"}


class DailyBriefingError(RuntimeError):
    """The analyst artifact is absent or violates its public contract."""


def contains_hangul(value: Any) -> bool:
    """Return whether a public title contains at least one Hangul syllable."""
    return any("가" <= char <= "힣" for char in str(value or ""))


def required_source_translation_urls(
    rows: list[dict[str, Any]], *, category_limit: int = 10
) -> set[str]:
    """Find non-Korean source titles visible in each public category column."""
    counts = {category: 0 for category in CATEGORIES}
    required: set[str] = set()
    for row in rows:
        source = normalize_source_config(
            {
                "category": row.get("category", ""),
                "name": row.get("source", ""),
                "relevance_profile": row.get("relevance_profile", ""),
            }
        )
        if not matches_source_relevance(str(row.get("title") or ""), source):
            continue
        category = str(source.get("category") or "").strip()
        if category not in counts or counts[category] >= category_limit:
            continue
        counts[category] += 1
        title = str(row.get("title") or "").strip()
        source_url = str(row.get("url") or "").strip()
        if title and not contains_hangul(title) and source_url.startswith("https://"):
            required.add(source_url)
    return required


def _text(value: Any, field: str, *, limit: int = 500) -> str:
    text = str(value or "").strip()
    if not text:
        raise DailyBriefingError(f"{field} is required")
    return text[:limit]


def _urls(value: Any, field: str, *, minimum: int = 1) -> list[str]:
    if not isinstance(value, list):
        raise DailyBriefingError(f"{field} must be a list")
    urls = list(dict.fromkeys(str(item).strip() for item in value if str(item).startswith("https://")))[:4]
    if len(urls) < minimum:
        raise DailyBriefingError(f"{field} requires {minimum} evidence URL(s)")
    return urls


def _rows(payload: dict[str, Any], field: str, expected: int | tuple[int, int]) -> list[dict[str, Any]]:
    rows = payload.get(field)
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise DailyBriefingError(f"{field} must be an object list")
    low, high = (expected, expected) if isinstance(expected, int) else expected
    if not low <= len(rows) <= high:
        raise DailyBriefingError(f"{field} requires {low}..{high} rows")
    return rows


def validate_daily_briefing(
    payload: Any,
    *,
    source_snapshot_hash: str = "",
    previous_snapshot_hash: str = "",
    previous_signal_labels: list[str] | None = None,
    previous_core_signals: list[dict[str, Any]] | None = None,
    required_translation_urls: set[str] | None = None,
    source_rows: list[dict[str, Any]] | None = None,
    retrospective_required: bool = False,
) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("contract_version") != CONTRACT_VERSION:
        raise DailyBriefingError("invalid daily briefing contract")
    artifact_hash = _text(payload.get("source_snapshot_hash"), "source_snapshot_hash", limit=128)
    if source_snapshot_hash and artifact_hash != source_snapshot_hash:
        raise DailyBriefingError("source snapshot hash mismatch")
    safe: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "generated_at": _text(payload.get("generated_at"), "generated_at", limit=40),
        "source_snapshot_hash": artifact_hash,
        "headline": _text(payload.get("headline"), "headline", limit=180),
        "summary": _text(payload.get("summary"), "summary", limit=700),
    }

    retrospective_present = "retrospective" in payload
    retrospective = payload.get("retrospective")
    if retrospective is None and not retrospective_required:
        retrospective = {"status": "baseline", "items": []}
    if retrospective_required and not retrospective_present:
        raise DailyBriefingError("retrospective is required")
    if not isinstance(retrospective, dict):
        raise DailyBriefingError("retrospective must be an object")
    retrospective_status = str(retrospective.get("status") or "").strip()
    if retrospective_status not in RETROSPECTIVE_STATUSES:
        raise DailyBriefingError("invalid retrospective status")
    retrospective_rows = retrospective.get("items", [])
    if not isinstance(retrospective_rows, list) or not all(
        isinstance(row, dict) for row in retrospective_rows
    ):
        raise DailyBriefingError("retrospective.items must be an object list")
    if retrospective_status == "baseline":
        if previous_snapshot_hash or retrospective_rows:
            raise DailyBriefingError("baseline retrospective cannot replace a previous report")
        safe["retrospective"] = {
            "status": "baseline",
            "previous_generated_at": "",
            "previous_snapshot_hash": "",
            "items": [],
        }
    else:
        artifact_previous_hash = _text(
            retrospective.get("previous_snapshot_hash"),
            "retrospective.previous_snapshot_hash",
            limit=128,
        )
        if len(artifact_previous_hash) != 64:
            raise DailyBriefingError("invalid previous briefing snapshot hash")
        if previous_snapshot_hash and artifact_previous_hash != previous_snapshot_hash:
            raise DailyBriefingError("previous briefing snapshot hash mismatch")
        if len(retrospective_rows) != 3:
            raise DailyBriefingError("available retrospective requires three rows")
        safe_rows = []
        used_indexes: set[int] = set()
        for row in retrospective_rows:
            try:
                signal_index = int(row.get("previous_signal_index", 0))
            except (TypeError, ValueError) as exc:
                raise DailyBriefingError("previous signal index must be an integer") from exc
            if signal_index not in {1, 2, 3} or signal_index in used_indexes:
                raise DailyBriefingError("retrospective requires unique signal indexes 1..3")
            used_indexes.add(signal_index)
            previous_label = _text(row.get("previous_label"), "previous_label", limit=100)
            if previous_signal_labels and previous_label != previous_signal_labels[signal_index - 1]:
                raise DailyBriefingError("retrospective previous signal label mismatch")
            verdict = _text(row.get("verdict"), "verdict", limit=20)
            if verdict not in RETROSPECTIVE_VERDICTS:
                raise DailyBriefingError("invalid retrospective verdict")
            safe_rows.append({
                "previous_signal_index": signal_index,
                "previous_label": previous_label,
                "previous_detail": _text(row.get("previous_detail"), "previous_detail", limit=320),
                "verdict": verdict,
                "current_status": _text(row.get("current_status"), "current_status", limit=420),
                "action": _text(row.get("action"), "action", limit=240),
                "evidence_urls": _urls(row.get("evidence_urls"), "evidence_urls"),
            })
        safe["retrospective"] = {
            "status": "available",
            "previous_generated_at": _text(
                retrospective.get("previous_generated_at"),
                "retrospective.previous_generated_at",
                limit=40,
            ),
            "previous_snapshot_hash": artifact_previous_hash,
            "items": sorted(safe_rows, key=lambda row: row["previous_signal_index"]),
        }

    safe["core_signals"] = []
    for index, row in enumerate(_rows(payload, "core_signals", 3)):
        tone = _text(row.get("tone"), f"core_signals[{index}].tone", limit=20)
        if tone not in TONES:
            raise DailyBriefingError("invalid signal tone")
        continuity = str(row.get("continuity") or "").strip()
        event_key = str(row.get("event_key") or "").strip()[:120]
        change_basis = str(row.get("change_basis") or "").strip()[:320]
        if previous_core_signals and continuity not in SIGNAL_CONTINUITIES:
            raise DailyBriefingError(
                f"core_signals[{index}].continuity must be new or follow_up"
            )
        if previous_core_signals and not event_key:
            raise DailyBriefingError(f"core_signals[{index}].event_key is required")
        evidence_urls = _urls(row.get("evidence_urls"), "evidence_urls")
        label = _text(row.get("label"), "label", limit=100)
        normalized_label = "".join(label.lower().split())
        overlapping_previous = []
        for previous in previous_core_signals or []:
            previous_urls = set(previous.get("evidence_urls") or [])
            previous_event_key = str(previous.get("event_key") or "").strip().lower()
            previous_label = "".join(str(previous.get("label") or "").lower().split())
            if (
                set(evidence_urls) & previous_urls
                or (event_key and previous_event_key and event_key.lower() == previous_event_key)
                or (normalized_label and normalized_label == previous_label)
            ):
                overlapping_previous.append(previous)
        if overlapping_previous:
            if continuity != "follow_up" or not change_basis:
                raise DailyBriefingError(
                    f"core_signals[{index}] overlaps the previous report without a follow-up basis"
                )
            previous_urls = {
                url
                for previous in overlapping_previous
                for url in previous.get("evidence_urls") or []
            }
            if not set(evidence_urls) - previous_urls:
                raise DailyBriefingError(
                    f"core_signals[{index}] follow_up requires new evidence"
                )
        elif previous_core_signals and continuity != "new":
            raise DailyBriefingError(
                f"core_signals[{index}] is marked follow_up without previous overlap"
            )
        safe["core_signals"].append({
            "metric": _text(row.get("metric"), "metric", limit=40),
            "label": label,
            "detail": _text(row.get("detail"), "detail", limit=320),
            "action": _text(row.get("action"), "action", limit=240),
            "tone": tone,
            "evidence_urls": evidence_urls,
            "event_key": event_key,
            "continuity": continuity,
            "change_basis": change_basis,
        })

    safe["keywords"] = []
    for row in _rows(payload, "keywords", 7):
        direction = _text(row.get("direction"), "direction", limit=12)
        if direction not in DIRECTIONS:
            raise DailyBriefingError("invalid keyword direction")
        try:
            score = max(0, min(10, int(row.get("score", 0))))
        except (TypeError, ValueError) as exc:
            raise DailyBriefingError("keyword score must be an integer") from exc
        safe["keywords"].append({
            "keyword": _text(row.get("keyword"), "keyword", limit=60),
            "score": score,
            "direction": direction,
            "basis": _text(row.get("basis"), "basis", limit=220),
        })

    safe["matrix"] = []
    quadrants: set[str] = set()
    for row in _rows(payload, "matrix", 4):
        quadrant = _text(row.get("quadrant"), "quadrant", limit=12)
        if quadrant not in QUADRANTS or quadrant in quadrants:
            raise DailyBriefingError("matrix requires four unique quadrants")
        quadrants.add(quadrant)
        safe["matrix"].append({
            "quadrant": quadrant,
            "label": _text(row.get("label"), "label", limit=90),
            "meaning": _text(row.get("meaning"), "meaning", limit=260),
            "action": _text(row.get("action"), "action", limit=220),
            "evidence_urls": _urls(row.get("evidence_urls"), "evidence_urls"),
        })

    safe["timeline"] = []
    horizons: set[str] = set()
    for row in _rows(payload, "timeline", 4):
        horizon = _text(row.get("horizon"), "horizon", limit=12)
        if horizon not in HORIZONS or horizon in horizons:
            raise DailyBriefingError("timeline requires four unique horizons")
        horizons.add(horizon)
        safe["timeline"].append({
            "horizon": horizon,
            "action": _text(row.get("action"), "action", limit=240),
            "reason": _text(row.get("reason"), "reason", limit=260),
            "evidence_urls": _urls(row.get("evidence_urls"), "evidence_urls"),
        })

    for field, expected in (("insight_cards", 3), ("themes", (3, 4)), ("developer_insights", (3, 4))):
        safe[field] = []
        for row in _rows(payload, field, expected):
            safe[field].append({
                "title": _text(row.get("title"), "title", limit=140),
                "analysis": _text(row.get("analysis"), "analysis", limit=700),
                "action": _text(row.get("action"), "action", limit=260),
                "evidence_urls": _urls(row.get("evidence_urls"), "evidence_urls"),
            })

    safe["watchlist"] = []
    for row in _rows(payload, "watchlist", (2, 3)):
        safe["watchlist"].append({
            "title": _text(row.get("title"), "title", limit=140),
            "reason": _text(row.get("reason"), "reason", limit=500),
            "trigger": _text(row.get("trigger"), "trigger", limit=240),
            "evidence_urls": _urls(row.get("evidence_urls"), "evidence_urls"),
        })

    translations = payload.get("source_title_translations", [])
    if not isinstance(translations, list) or not all(isinstance(row, dict) for row in translations):
        raise DailyBriefingError("source_title_translations must be an object list")
    safe["source_title_translations"] = []
    translated_urls: set[str] = set()
    for row in translations[:60]:
        source_url = _text(row.get("source_url"), "source_url", limit=500)
        korean_title = _text(row.get("korean_title"), "korean_title", limit=220)
        if not source_url.startswith("https://") or source_url in translated_urls:
            raise DailyBriefingError("source title translations require unique https URLs")
        if not contains_hangul(korean_title):
            raise DailyBriefingError("korean_title must contain Korean text")
        translated_urls.add(source_url)
        safe["source_title_translations"].append({
            "source_url": source_url,
            "korean_title": korean_title,
        })
    missing_translation_urls = set(required_translation_urls or ()) - translated_urls
    if missing_translation_urls:
        raise DailyBriefingError(
            "source title translations are incomplete for visible non-Korean titles"
        )

    safe["must_read"] = []
    categories: set[str] = set()
    source_rows_by_url = {
        str(row.get("url") or "").strip(): row
        for row in source_rows or []
        if str(row.get("url") or "").startswith("https://")
    }
    for row in _rows(payload, "must_read", 5):
        category = _text(row.get("category"), "category", limit=40)
        if category not in CATEGORIES or category in categories:
            raise DailyBriefingError("must_read requires one item per active category")
        categories.add(category)
        source_url = _text(row.get("source_url"), "source_url", limit=500)
        if not source_url.startswith("https://"):
            raise DailyBriefingError("must_read source_url must use https")
        title = _text(row.get("title"), "title", limit=220)
        source = _text(row.get("source"), "source", limit=80)
        korean_title = str(row.get("korean_title") or "").strip()[:220]
        if not contains_hangul(title) and not contains_hangul(korean_title):
            raise DailyBriefingError(
                "must_read.korean_title must contain Korean text for non-Korean titles"
            )
        if source_rows is not None:
            source_row = source_rows_by_url.get(source_url)
            if source_row is None:
                raise DailyBriefingError("must_read source_url must exist in source snapshot")
            if (
                str(source_row.get("title") or "").strip() != title
                or str(source_row.get("source") or "").strip() != source
                or str(source_row.get("category") or "").strip() != category
            ):
                raise DailyBriefingError(
                    "must_read title, source, and category must match source snapshot"
                )
        safe["must_read"].append({
            "title": title,
            "korean_title": korean_title,
            "category": category,
            "source": source,
            "source_url": source_url,
            "why_it_matters": _text(row.get("why_it_matters"), "why_it_matters", limit=420),
            "action": _text(row.get("action"), "action", limit=260),
        })
    return safe


def load_daily_briefing(
    path: Path,
    *,
    source_snapshot_hash: str = "",
    previous_snapshot_hash: str = "",
    previous_signal_labels: list[str] | None = None,
    previous_core_signals: list[dict[str, Any]] | None = None,
    required_translation_urls: set[str] | None = None,
    source_rows: list[dict[str, Any]] | None = None,
    retrospective_required: bool = False,
) -> dict[str, Any]:
    if not path.is_file():
        raise DailyBriefingError(f"daily briefing artifact missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DailyBriefingError("daily briefing artifact is not valid JSON") from exc
    return validate_daily_briefing(
        payload,
        source_snapshot_hash=source_snapshot_hash,
        previous_snapshot_hash=previous_snapshot_hash,
        previous_signal_labels=previous_signal_labels,
        previous_core_signals=previous_core_signals,
        required_translation_urls=required_translation_urls,
        source_rows=source_rows,
        retrospective_required=retrospective_required,
    )
