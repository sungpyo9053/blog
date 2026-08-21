import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.report_news_worthiness_shadow import aggregate, load_window


class NewsWorthinessReportTest(unittest.TestCase):
    def test_window_separates_success_empty_and_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            runs = Path(temporary)
            payloads = (
                ("a", "news-worthiness-shadow.json", {"selected_at": "2026-08-21T17:00:00+00:00", "shadow_top2": ["A"], "overlap_count": 1, "candidates": [], "ranking": []}),
                ("b", "news-worthiness-shadow.json", {"selected_at": "2026-08-22T17:00:00+00:00", "shadow_top2": [], "overlap_count": 0, "candidates": [], "ranking": []}),
                ("c", "news-worthiness-shadow-error.json", {"recorded_at": "2026-08-23T17:00:00+00:00", "status": "failed"}),
            )
            for run_id, filename, payload in payloads:
                directory = runs / run_id
                directory.mkdir()
                (directory / filename).write_text(json.dumps(payload), encoding="utf-8")
            rows = load_window(runs, date(2026, 8, 22), date(2026, 8, 24))
            report = aggregate(rows, date(2026, 8, 22), date(2026, 8, 24))

        self.assertEqual(report["status_counts"], {"empty": 1, "error": 1, "success": 1})
        self.assertEqual(report["observed_day_count"], 3)
        self.assertTrue(report["window_complete"])

    def test_decay_reversal_is_recorded(self):
        payload = {
            "selected_at": "2026-08-21T17:00:00+00:00",
            "shadow_top2": ["B", "A"],
            "overlap_count": 0,
            "candidates": [],
            "ranking": [
                {"candidate_id": "b", "title": "B", "base_score": 8, "rank": 1, "topic_decay_applied": False},
                {"candidate_id": "a", "title": "A", "base_score": 10, "rank": 2, "topic_decay_applied": True, "topic_decay": {"factor": 0.7}},
            ],
        }
        report = aggregate([(Path("run/news-worthiness-shadow.json"), payload)], date(2026, 8, 22), date(2026, 8, 22))
        self.assertEqual(len(report["topic_decay_rank_reversals"]), 1)


if __name__ == "__main__":
    unittest.main()
