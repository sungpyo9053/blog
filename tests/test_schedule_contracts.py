from __future__ import annotations

import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ScheduleContractTests(unittest.TestCase):
    def test_production_pipeline_runs_at_0730_kst(self):
        timer = (ROOT / "deploy/huntlab-daily-pipeline.timer").read_text(
            encoding="utf-8"
        )
        self.assertIn("OnCalendar=*-*-* 07:30:00 Asia/Seoul", timer)
        self.assertNotIn("OnCalendar=*-*-* 02:00:00", timer)
        self.assertIn("Persistent=false", timer)

    def test_retry_runs_at_1700_kst(self):
        timer = (ROOT / "deploy/huntlab-daily-retry.timer").read_text(
            encoding="utf-8"
        )
        self.assertIn("OnCalendar=*-*-* 17:00:00 Asia/Seoul", timer)
        self.assertIn("Persistent=false", timer)

    def test_legacy_macos_schedule_matches_production_start(self):
        with (ROOT / "deploy/com.huntlab.daily-pipeline.plist").open("rb") as handle:
            schedule = plistlib.load(handle)["StartCalendarInterval"]
        self.assertEqual(schedule, {"Hour": 7, "Minute": 30})


if __name__ == "__main__":
    unittest.main()
