import unittest
from datetime import date

import tempfile
from pathlib import Path

from scripts.goal_report import last_revenue, message, target_for


class GoalReportTests(unittest.TestCase):
    def test_picks_next_milestone_and_caps_after_last(self):
        self.assertEqual(target_for(date(2026, 10, 12)), (date(2026, 10, 24), 70))
        self.assertEqual(target_for(date(2026, 10, 25)), (date(2026, 11, 30), 210))
        self.assertEqual(target_for(date(2028, 1, 1)), (date(2027, 6, 30), 7000))

    def test_message_fits_kakao_and_flags_shortfall(self):
        text = message(date(2026, 10, 12), 34, 61, 13, 0, 5, "10/13 확인 애드센스 $0.00·쿠팡 0원")
        self.assertLessEqual(len(text), 200)
        self.assertIn("미달(48%)", text)
        self.assertIn("실수익(10/13 확인 애드센스 $0.00·쿠팡 0원)", text)

    def test_last_revenue_reads_newest_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "r.tsv"
            log.write_text("date\tadsense_usd\tcoupang_krw\n2026-10-13\t0.00\t0\n2026-11-02\t1.5\t12300\n")
            self.assertEqual(last_revenue(log), "11/02 확인 애드센스 $1.50·쿠팡 12,300원")


if __name__ == "__main__":
    unittest.main()
