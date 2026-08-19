#!/usr/bin/env python3
"""Collect a small Whereispost batch through its normal browser UI.

The collector never clicks the site's ad-unlock control and never replaces a
working cache after a lock, challenge, parse error, or empty result.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.manage_whereispost_cache import validate_cache_payload


SEOUL = ZoneInfo("Asia/Seoul")
DEFAULT_CACHE = ROOT / "output" / "search-signals" / "whereispost-latest.json"
DEFAULT_QUEUE = ROOT / "output" / "search-signals" / "whereispost-queue.json"
DEFAULT_PROFILE = ROOT / "output" / "search-signals" / "browser-profile"
DEFAULT_SEEDS = ROOT / "config" / "search-signals" / "whereispost-seeds.txt"
DEFAULT_URL = "https://whereispost.com/keyword"
LOCK_TEXT = "짧은 광고 보기"
ROW_TTL_DAYS = 30


class CollectorError(RuntimeError):
    """A collection run could not safely produce observations."""


class CollectorLocked(CollectorError):
    """The site requested an ad unlock; the existing cache must be retained."""


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectorError(f"invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise CollectorError(f"JSON root must be an object: {path}")
    return payload


def load_seed_keywords(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CollectorError(f"cannot read seeds: {path}") from exc
    return unique_keywords(
        line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")
    )


def unique_keywords(values: Any) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        keyword = " ".join(str(value).split())
        key = keyword.casefold()
        if keyword and key not in seen:
            seen.add(key)
            output.append(keyword)
    return output


def load_rows(cache_path: Path) -> list[dict[str, Any]]:
    payload = _load_json(cache_path)
    rows = payload.get("rows", [])
    if rows and not isinstance(rows, list):
        raise CollectorError("cache rows must be a list")
    return [dict(row) for row in rows if isinstance(row, dict)]


def build_queue(
    seeds: list[str],
    rows: list[dict[str, Any]],
    queue_payload: dict[str, Any],
) -> list[str]:
    existing_queue = queue_payload.get("pending", [])
    if not isinstance(existing_queue, list):
        existing_queue = []
    expansion: list[str] = []
    for row in rows:
        expansion.append(str(row.get("keyword", "")))
        related = row.get("related_keywords", [])
        if isinstance(related, list):
            expansion.extend(str(item) for item in related)
    return unique_keywords([*existing_queue, *seeds, *expansion])


def parse_count(value: str, field: str) -> int:
    normalized = value.replace(",", "").strip()
    if not re.fullmatch(r"\d+", normalized):
        raise CollectorError(f"{field} is not an exact integer: {value!r}")
    return int(normalized)


def parse_ratio(value: str) -> float:
    normalized = value.replace(",", "").strip()
    try:
        ratio = float(normalized)
    except ValueError as exc:
        raise CollectorError(f"ratio is not numeric: {value!r}") from exc
    if ratio < 0:
        raise CollectorError("ratio is negative")
    return ratio


def parse_dom_result(result: dict[str, Any], keyword: str, observed_at: str) -> dict[str, Any]:
    cells = result.get("cells")
    if not isinstance(cells, list) or len(cells) < 7:
        raise CollectorError(f"no result row for {keyword}")
    returned_keyword = " ".join(str(cells[1]).split())
    if returned_keyword.casefold() != keyword.casefold():
        raise CollectorError(
            f"keyword mismatch: requested={keyword!r} returned={returned_keyword!r}"
        )
    pc = parse_count(str(cells[2]), "pc_searches")
    mobile = parse_count(str(cells[3]), "mobile_searches")
    total = parse_count(str(cells[4]), "total_searches")
    if total != pc + mobile:
        raise CollectorError(f"search total mismatch for {keyword}")
    related = result.get("related", [])
    return {
        "keyword": returned_keyword,
        "pc_searches": pc,
        "mobile_searches": mobile,
        "total_searches": total,
        "documents": parse_count(str(cells[5]), "documents"),
        "competition_ratio": parse_ratio(str(cells[6])),
        "related_keywords": unique_keywords(related if isinstance(related, list) else []),
        "source_origin": "topic_cluster",
        "observed_at": observed_at,
        "consumed": False,
    }


async def page_is_locked(page: Any) -> bool:
    return await page.get_by_text(LOCK_TEXT, exact=False).count() > 0


async def submit_search(page: Any, keyword: str) -> str:
    """Submit a keyword before waiting for the site's lazy Turnstile flow."""
    await page.locator("#keyword").fill(keyword)
    await page.get_by_role("button", name="검색").click()
    try:
        await page.wait_for_function(
            """(keyword) => {
              if (document.body.innerText.includes('짧은 광고 보기')) return true;
              const cells = [...document.querySelectorAll('#result tbody tr:first-child td')];
              return cells.length >= 7 && cells[1].innerText.trim() === keyword;
            }""",
            keyword,
            timeout=20_000,
        )
    except Exception as exc:
        if await page_is_locked(page):
            return "LOCKED"
        raise CollectorError(f"result timeout for {keyword}") from exc
    return "LOCKED" if await page_is_locked(page) else "RESULT"


async def collect_batch(
    keywords: list[str], profile_dir: Path, *, headless: bool = True
) -> tuple[list[dict[str, Any]], list[str], str]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise CollectorError("playwright is not installed") from exc

    observations: list[dict[str, Any]] = []
    remaining = list(keywords)
    profile_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(profile_dir), headless=headless
        )
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(DEFAULT_URL, wait_until="domcontentloaded", timeout=30_000)
            if await page_is_locked(page):
                raise CollectorLocked("ad unlock is required")

            for index, keyword in enumerate(keywords):
                if await page_is_locked(page):
                    return observations, keywords[index:], "LOCKED"
                try:
                    search_status = await submit_search(page, keyword)
                except CollectorError:
                    if observations:
                        return observations, keywords[index:], "UNAVAILABLE"
                    raise
                if search_status == "LOCKED":
                    return observations, keywords[index:], "LOCKED"
                raw = await page.evaluate(
                    """() => ({
                      cells: [...document.querySelectorAll('#result tbody tr:first-child td')]
                        .map(cell => cell.innerText.trim()),
                      related: [...document.querySelectorAll('#relkey li')]
                        .map(item => item.innerText.trim()).filter(Boolean)
                    })"""
                )
                observed_at = datetime.now(SEOUL).isoformat(timespec="seconds")
                try:
                    observations.append(parse_dom_result(raw, keyword, observed_at))
                except CollectorError:
                    if observations:
                        return observations, keywords[index:], "UNAVAILABLE"
                    raise
                remaining = keywords[index + 1 :]
                await page.wait_for_timeout(1_500)
        finally:
            await context.close()
    return observations, remaining, "SUCCESS"


def merge_rows(
    existing: list[dict[str, Any]], fresh: list[dict[str, Any]], now: datetime
) -> list[dict[str, Any]]:
    cutoff = now.astimezone(timezone.utc) - timedelta(days=ROW_TTL_DAYS)
    merged: dict[str, dict[str, Any]] = {}
    for row in [*existing, *fresh]:
        keyword = " ".join(str(row.get("keyword", "")).split())
        if not keyword:
            continue
        observed_text = str(row.get("observed_at") or row.get("checked_at") or "")
        if observed_text:
            try:
                observed = datetime.fromisoformat(observed_text).astimezone(timezone.utc)
            except ValueError:
                observed = now.astimezone(timezone.utc)
            if observed < cutoff:
                continue
        normalized = dict(row)
        normalized["keyword"] = keyword
        normalized.setdefault("source_origin", "topic_cluster")
        normalized.setdefault("related_keywords", [])
        normalized["consumed"] = False
        merged[keyword.casefold()] = normalized
    return sorted(
        merged.values(),
        key=lambda row: (-int(row.get("total_searches", 0)), row["keyword"]),
    )


async def run(args: argparse.Namespace) -> int:
    now = datetime.now(SEOUL)
    existing_rows = load_rows(args.cache)
    queue_payload = _load_json(args.queue)
    queue = build_queue(load_seed_keywords(args.seeds), existing_rows, queue_payload)
    batch = queue[: args.batch_size]
    if not batch:
        print("whereispost_collector status=EMPTY cache_preserved=true")
        return 0

    try:
        fresh, unattempted, collection_status = await collect_batch(
            batch, args.profile, headless=not args.show_browser
        )
    except CollectorLocked as exc:
        _atomic_json(
            args.queue,
            {
                "updated_at": now.isoformat(timespec="seconds"),
                "last_status": "LOCKED",
                "pending": queue,
            },
        )
        print(
            f"whereispost_collector status=LOCKED reason={exc} "
            "cache_preserved=true"
        )
        return 0
    except CollectorError as exc:
        _atomic_json(
            args.queue,
            {
                "updated_at": now.isoformat(timespec="seconds"),
                "last_status": "UNAVAILABLE",
                "pending": queue,
            },
        )
        print(
            f"whereispost_collector status=UNAVAILABLE reason={exc} "
            "cache_preserved=true"
        )
        return 0
    except Exception as exc:
        _atomic_json(
            args.queue,
            {
                "updated_at": now.isoformat(timespec="seconds"),
                "last_status": "UNAVAILABLE",
                "pending": queue,
            },
        )
        print(
            "whereispost_collector status=UNAVAILABLE "
            f"reason=browser_{type(exc).__name__} cache_preserved=true"
        )
        return 0

    merged = merge_rows(existing_rows, fresh, now)
    if fresh:
        payload = {
            "provider": "whereispost_keywordmaster",
            "checked_at": now.isoformat(timespec="seconds"),
            "collection_mode": "browser_ui_bounded",
            "cache_contract_version": 1,
            "max_age_days": ROW_TTL_DAYS,
            "minimum_eligible_rows": 1,
            "rows": merged,
        }
        payload = validate_cache_payload(
            payload, now=now, max_age_days=ROW_TTL_DAYS, min_eligible=1
        )
        _atomic_json(args.cache, payload)

    completed = {row["keyword"].casefold() for row in fresh}
    next_queue = [item for item in queue if item.casefold() not in completed]
    for row in fresh:
        next_queue.extend(row.get("related_keywords", []))
    next_queue.extend(unattempted)
    _atomic_json(
        args.queue,
        {
            "updated_at": now.isoformat(timespec="seconds"),
            "last_status": collection_status,
            "pending": unique_keywords(next_queue),
        },
    )
    print(
        f"whereispost_collector status={collection_status} "
        f"collected={len(fresh)} cache_rows={len(merged)} "
        f"pending={len(unique_keywords(next_queue))}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded Whereispost browser collector")
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument("--show-browser", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not 1 <= args.batch_size <= 10:
        raise SystemExit("batch-size must be between 1 and 10")
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
