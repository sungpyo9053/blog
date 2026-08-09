import unittest
from datetime import date

from scripts.run_quality_remediation_schedule import phase


class QualityRemediationScheduleTests(unittest.TestCase):
    def test_phases_are_dated_and_non_mutating_by_contract(self):
        self.assertEqual(phase(date(2026, 8, 9)), ("SCHEDULED", "wait_for_2026-08-10"))
        self.assertEqual(phase(date(2026, 8, 10))[1], "select_and_backup_up_to_five_candidates")
        self.assertEqual(phase(date(2026, 8, 12))[1], "review_and_enrich_one_candidate_at_a_time")
        self.assertEqual(phase(date(2026, 8, 13))[1], "review_empty_politics_category_and_navigation")
        self.assertEqual(phase(date(2026, 8, 14))[1], "run_public_audit_after_approved_changes")


if __name__ == "__main__":
    unittest.main()
