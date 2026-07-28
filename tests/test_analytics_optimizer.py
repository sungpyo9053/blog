from __future__ import annotations

import unittest

from scripts.run_analytics_optimizer import analyze


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


if __name__ == "__main__":
    unittest.main()
