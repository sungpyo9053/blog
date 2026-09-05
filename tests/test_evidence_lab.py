from __future__ import annotations

import unittest

from scripts.run_evidence_lab import run_experiment


class EvidenceLabTests(unittest.TestCase):
    def test_rest_experiment_has_real_fail_pass_and_zero_wordpress_writes(self):
        result = run_experiment("rest-html-200-response")
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["before"]["exit_code"], 1)
        self.assertEqual(result["after"]["exit_code"], 0)
        self.assertEqual(result["environment"]["wordpress_writes"], 0)

    def test_indexability_experiment_has_real_fail_pass_and_zero_wordpress_writes(self):
        result = run_experiment("noindex-sitemap-consistency")
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["before"]["exit_code"], 1)
        self.assertEqual(result["after"]["exit_code"], 0)
        self.assertEqual(result["environment"]["wordpress_writes"], 0)
