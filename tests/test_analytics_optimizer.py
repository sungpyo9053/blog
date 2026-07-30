from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.run_analytics_optimizer import analyze, write_reports


class AnalyticsOptimizerTests(unittest.TestCase):
    def test_analyze_returns_refresh_and_gap_candidates(self):
        rows = [
            {
                "keys": ["대표 검색어", "https://huntlab.app/post/"],
                "clicks": 0,
                "impressions": 80,
                "ctr": 0,
                "position": 12,
            }
        ]

        refresh, gaps = analyze(rows)

        self.assertEqual(refresh[0]["reason"], "high_impressions_low_ctr")
        self.assertEqual(gaps[0]["reason"], "visible_query_without_clicks")

    def test_analyze_ignores_small_samples(self):
        refresh, gaps = analyze(
            [
                {
                    "keys": ["작은 표본", "https://huntlab.app/small/"],
                    "clicks": 0,
                    "impressions": 10,
                    "ctr": 0,
                    "position": 30,
                }
            ]
        )
        self.assertEqual(refresh, [])
        self.assertEqual(gaps, [])

    def test_write_reports_keeps_latest_and_dated_snapshot(self):
        with TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            now = datetime(2026, 7, 31, 1, 0, tzinfo=timezone.utc)

            latest, dated = write_reports("daily report\n", now, report_dir)

            self.assertEqual(latest, report_dir / "latest.md")
            self.assertEqual(dated, report_dir / "2026-07-31.md")
            self.assertEqual(latest.read_text(encoding="utf-8"), "daily report\n")
            self.assertEqual(dated.read_text(encoding="utf-8"), "daily report\n")
            self.assertEqual(list(report_dir.glob(".*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
