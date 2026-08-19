from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from scripts.collect_whereispost_cache import (
    CollectorError,
    build_queue,
    load_seed_keywords,
    merge_rows,
    parse_dom_result,
    submit_search,
)


class WhereispostCollectorTests(unittest.TestCase):
    def test_seed_file_is_nonempty_and_unique(self):
        seeds = load_seed_keywords(
            Path(__file__).resolve().parents[1]
            / "config"
            / "search-signals"
            / "whereispost-seeds.txt"
        )
        self.assertGreaterEqual(len(seeds), 30)
        self.assertEqual(len(seeds), len({item.casefold() for item in seeds}))

    def test_queue_keeps_pending_then_expands_related_keywords(self):
        queue = build_queue(
            ["신규 키워드"],
            [
                {
                    "keyword": "기존 키워드",
                    "related_keywords": ["연관 키워드", "신규 키워드"],
                }
            ],
            {"pending": ["대기 키워드", "기존 키워드"]},
        )
        self.assertEqual(
            queue,
            ["대기 키워드", "기존 키워드", "신규 키워드", "연관 키워드"],
        )

    def test_dom_result_requires_exact_totals(self):
        with self.assertRaisesRegex(CollectorError, "total mismatch"):
            parse_dom_result(
                {
                    "cells": ["-", "주택청약", "10", "20", "31", "100", "3.2"],
                    "related": [],
                },
                "주택청약",
                "2026-08-18T19:00:00+09:00",
            )

    def test_dom_result_parses_verified_row(self):
        row = parse_dom_result(
            {
                "cells": ["-", "주택청약", "9,710", "22,800", "32,510", "1,919,563", "59.045"],
                "related": ["주택청약종합저축", "주택청약종합저축"],
            },
            "주택청약",
            "2026-08-18T19:00:00+09:00",
        )
        self.assertEqual(row["total_searches"], 32510)
        self.assertEqual(row["related_keywords"], ["주택청약종합저축"])

    def test_fresh_row_replaces_existing_keyword(self):
        existing = [
            {
                "keyword": "주택청약",
                "pc_searches": 1,
                "mobile_searches": 2,
                "total_searches": 3,
                "documents": 4,
                "competition_ratio": 1.0,
                "related_keywords": [],
                "source_origin": "topic_cluster",
            }
        ]
        fresh = [{**existing[0], "total_searches": 300}]
        rows = merge_rows(
            existing,
            fresh,
            datetime.fromisoformat("2026-08-18T19:00:00+09:00"),
        )
        self.assertEqual(rows[0]["total_searches"], 300)


class WhereispostBrowserFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_is_submitted_before_waiting_for_lazy_result(self):
        events = []
        page = Mock()
        keyword_input = Mock()
        keyword_input.fill = AsyncMock(
            side_effect=lambda value: events.append(("fill", value))
        )
        search_button = Mock()
        search_button.click = AsyncMock(side_effect=lambda: events.append(("click", None)))
        lock_text = Mock()
        lock_text.count = AsyncMock(return_value=0)
        page.locator.return_value = keyword_input
        page.get_by_role.return_value = search_button
        page.get_by_text.return_value = lock_text
        page.wait_for_function = AsyncMock(
            side_effect=lambda *args, **kwargs: events.append(("wait", args[1]))
        )

        status = await submit_search(page, "주택청약")

        self.assertEqual(status, "RESULT")
        self.assertEqual(
            events,
            [("fill", "주택청약"), ("click", None), ("wait", "주택청약")],
        )

    async def test_ad_unlock_after_search_is_reported_as_locked(self):
        page = Mock()
        keyword_input = Mock()
        keyword_input.fill = AsyncMock()
        search_button = Mock()
        search_button.click = AsyncMock()
        lock_text = Mock()
        lock_text.count = AsyncMock(return_value=1)
        page.locator.return_value = keyword_input
        page.get_by_role.return_value = search_button
        page.get_by_text.return_value = lock_text
        page.wait_for_function = AsyncMock()

        self.assertEqual(await submit_search(page, "주택청약"), "LOCKED")


if __name__ == "__main__":
    unittest.main()
