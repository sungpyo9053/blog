from __future__ import annotations

import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ScheduleContractTests(unittest.TestCase):
    def test_production_pipeline_runs_at_0200_kst(self):
        timer = (ROOT / "deploy/huntlab-daily-pipeline.timer").read_text(
            encoding="utf-8"
        )
        self.assertIn("OnCalendar=*-*-* 02:00:00 Asia/Seoul", timer)
        self.assertNotIn("OnCalendar=*-*-* 07:30:00", timer)
        self.assertIn("Persistent=false", timer)

    def test_retry_runs_at_1700_kst(self):
        timer = (ROOT / "deploy/huntlab-daily-retry.timer").read_text(
            encoding="utf-8"
        )
        self.assertIn("OnCalendar=*-*-* 17:00:00 Asia/Seoul", timer)
        self.assertIn("Persistent=false", timer)

    def test_whereispost_collector_runs_every_two_hours_at_minute_30(self):
        timer = (ROOT / "deploy/huntlab-whereispost-collector.timer").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "OnCalendar=*-*-* 00,02,04,06,08,10,12,14,16,18,20,22:30:00 Asia/Seoul",
            timer,
        )
        self.assertIn("Persistent=false", timer)

        service = (ROOT / "deploy/huntlab-daily-pipeline.service").read_text(
            encoding="utf-8"
        )
        self.assertIn("--use-whereispost-cache", service)
        self.assertNotIn("--require-whereispost-cache", service)

    def test_google_trends_collector_runs_hourly_and_daily_pipeline_consumes_it(self):
        timer = (ROOT / "deploy/huntlab-google-trends-collector.timer").read_text(
            encoding="utf-8"
        )
        self.assertIn("OnCalendar=*-*-* *:10:00 Asia/Seoul", timer)
        self.assertIn("Persistent=false", timer)

        service = (ROOT / "deploy/huntlab-daily-pipeline.service").read_text(
            encoding="utf-8"
        )
        self.assertIn("--use-google-trends-cache", service)
        self.assertIn("--topic-workers 2", service)

    def test_legacy_macos_schedule_matches_production_start(self):
        with (ROOT / "deploy/com.huntlab.daily-pipeline.plist").open("rb") as handle:
            schedule = plistlib.load(handle)["StartCalendarInterval"]
        self.assertEqual(schedule, {"Hour": 2, "Minute": 0})


if __name__ == "__main__":
    unittest.main()
