#!/usr/bin/env python3
"""Validate and atomically promote an operator-observed Whereispost cache."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.search_signal_providers import SearchSignalError, load_whereispost_shadow


DEFAULT_CACHE = ROOT / "output" / "search-signals" / "whereispost-latest.json"
DEFAULT_MAX_AGE_DAYS = 7
DEFAULT_MIN_ELIGIBLE = 6
MIN_AUTOMATIC_SEARCHES = 100
ALLOWED_SOURCE_ORIGINS = {
    "search_console",
    "official_change",
    "observed_search_question",
    "user_request",
    "topic_cluster",
}


class CacheValidationError(ValueError):
    """Raised when an observation cannot become the active cache."""


def _parse_checked_at(value: str) -> datetime:
    try:
        checked_at = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CacheValidationError("checked_at must be ISO-8601") from exc
    if checked_at.tzinfo is None:
        raise CacheValidationError("checked_at must include a timezone")
    return checked_at.astimezone(timezone.utc)


def validate_cache_payload(
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    min_eligible: int = DEFAULT_MIN_ELIGIBLE,
) -> dict[str, Any]:
    if payload.get("provider") != "whereispost_keywordmaster":
        raise CacheValidationError("provider mismatch")
    checked_at_text = str(payload.get("checked_at", "")).strip()
    checked_at = _parse_checked_at(checked_at_text)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if checked_at > current + timedelta(minutes=5):
        raise CacheValidationError("checked_at is in the future")
    if current - checked_at > timedelta(days=max_age_days):
        raise CacheValidationError(
            f"cache is older than {max_age_days} day(s)"
        )

    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise CacheValidationError("rows must be a non-empty list")

    normalized_rows: list[dict[str, Any]] = []
    seen_keywords: set[str] = set()
    for index, raw in enumerate(rows, 1):
        if not isinstance(raw, dict):
            raise CacheValidationError(f"row {index} must be an object")
        keyword = str(raw.get("keyword", "")).strip()
        keyword_key = keyword.casefold()
        if not keyword:
            raise CacheValidationError(f"row {index} keyword is empty")
        if keyword_key in seen_keywords:
            raise CacheValidationError(f"duplicate keyword: {keyword}")
        seen_keywords.add(keyword_key)

        source_origin = str(raw.get("source_origin", "")).strip()
        if source_origin not in ALLOWED_SOURCE_ORIGINS:
            raise CacheValidationError(
                f"row {index} source_origin is invalid: {source_origin or 'missing'}"
            )
        related = raw.get("related_keywords", [])
        if not isinstance(related, list) or not all(
            isinstance(item, str) and item.strip() for item in related
        ):
            raise CacheValidationError(
                f"row {index} related_keywords must be a string list"
            )

        normalized = dict(raw)
        normalized["keyword"] = keyword
        normalized["source_origin"] = source_origin
        normalized["related_keywords"] = [item.strip() for item in related]
        normalized["consumed"] = bool(raw.get("consumed", False))
        normalized_rows.append(normalized)

    normalized_payload = {
        **payload,
        "provider": "whereispost_keywordmaster",
        "checked_at": checked_at_text,
        "cache_contract_version": 1,
        "max_age_days": max_age_days,
        "minimum_eligible_rows": min_eligible,
        "rows": normalized_rows,
    }

    with tempfile.TemporaryDirectory() as temporary:
        probe = Path(temporary) / "whereispost.json"
        probe.write_text(
            json.dumps(normalized_payload, ensure_ascii=False), encoding="utf-8"
        )
        try:
            load_whereispost_shadow(probe)
        except SearchSignalError as exc:
            raise CacheValidationError(str(exc)) from exc

    eligible = [
        row
        for row in normalized_rows
        if not row["consumed"]
        and row.get("total_searches", 0) >= MIN_AUTOMATIC_SEARCHES
    ]
    if len(eligible) < min_eligible:
        raise CacheValidationError(
            f"eligible rows {len(eligible)} is below required {min_eligible}"
        )
    normalized_payload["eligible_rows"] = len(eligible)
    return normalized_payload


def promote_cache(
    source: Path,
    destination: Path = DEFAULT_CACHE,
    *,
    now: datetime | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    min_eligible: int = DEFAULT_MIN_ELIGIBLE,
) -> dict[str, Any]:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CacheValidationError(f"cannot read candidate cache: {source}") from exc
    if not isinstance(payload, dict):
        raise CacheValidationError("candidate cache must be an object")
    validated = validate_cache_payload(
        payload,
        now=now,
        max_age_days=max_age_days,
        min_eligible=min_eligible,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(validated, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return validated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and atomically promote a Whereispost observation cache"
    )
    parser.add_argument("input", type=Path, help="operator-observed candidate JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    parser.add_argument("--min-eligible", type=int, default=DEFAULT_MIN_ELIGIBLE)
    parser.add_argument("--check-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.max_age_days < 1 or args.min_eligible < 1:
        raise SystemExit("max-age-days and min-eligible must be positive")
    if args.check_only:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        validated = validate_cache_payload(
            payload,
            max_age_days=args.max_age_days,
            min_eligible=args.min_eligible,
        )
    else:
        validated = promote_cache(
            args.input,
            args.output,
            max_age_days=args.max_age_days,
            min_eligible=args.min_eligible,
        )
    print(
        "whereispost_cache status=VALID "
        f"checked_at={validated['checked_at']} "
        f"rows={len(validated['rows'])} "
        f"eligible={validated['eligible_rows']} "
        f"mode={'check' if args.check_only else 'promote'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
