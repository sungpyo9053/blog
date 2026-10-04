import unittest
from unittest import mock
from datetime import date

from scripts import operator_snapshot as snap


class EngagementTests(unittest.TestCase):
    def test_average_engagement_per_active_user(self):
        row = {"rows": [{"metricValues": [{"value": v} for v in ("13", "9", "0.24", "300", "6")]}]}
        with mock.patch.dict("os.environ", {"GA4_PROPERTY_ID": "1"}):
            analytics = snap.analytics_yesterday(None, lambda *_: row, date(2026, 10, 4))
        self.assertEqual(analytics["engaged_seconds"], 50)

    def test_no_rows_means_zero_engagement(self):
        with mock.patch.dict("os.environ", {"GA4_PROPERTY_ID": "1"}):
            self.assertEqual(snap.analytics_yesterday(None, lambda *_: {}, date(2026, 10, 4))["engaged_seconds"], 0)

    def test_compose_shows_engagement_line(self):
        message = snap.compose(date(2026, 10, 4), (1, 1), 5,
                               {"views": 13, "sessions": 9, "revenue": 0.24, "engaged_seconds": 50}, None)
        self.assertIn("평균 참여 50초/명", message)
        self.assertLessEqual(len(message), 200)

    def test_midnight_report_counts_todays_scheduled_pair(self):
        rows = [{"status": "scheduled", "scheduled_at": "2026-10-05T10:00:00+09:00", "english": {"post_id": 864}},
                {"status": "scheduled", "scheduled_at": "2026-10-06T10:00:00+09:00", "english": {"post_id": 874}},
                {"status": "published", "scheduled_at": "2026-10-05T10:00:00+09:00", "english": {}}]
        self.assertEqual(snap.due_today(rows, date(2026, 10, 5)), (1, 1))


if __name__ == "__main__":
    unittest.main()
