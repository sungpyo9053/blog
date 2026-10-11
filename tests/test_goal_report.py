import unittest
from datetime import date

from scripts.goal_report import message, target_for


class GoalReportTests(unittest.TestCase):
    def test_picks_next_milestone_and_caps_after_last(self):
        self.assertEqual(target_for(date(2026, 10, 12)), (date(2026, 10, 24), 70))
        self.assertEqual(target_for(date(2026, 10, 25)), (date(2026, 11, 30), 210))
        self.assertEqual(target_for(date(2028, 1, 1)), (date(2027, 6, 30), 7000))

    def test_message_fits_kakao_and_flags_shortfall(self):
        text = message(date(2026, 10, 12), 34, 61, 13, 0, 5)
        self.assertLessEqual(len(text), 200)
        self.assertIn("미달(48%)", text)
        self.assertIn("$0.78", text)


if __name__ == "__main__":
    unittest.main()
