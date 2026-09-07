from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


class EvidenceManifestTests(unittest.TestCase):
    def test_manifest_matches_current_schedule_limit_and_test_log(self):
        manifest = json.loads(
            Path(
                "evidence/topic-events/2026-09-05-evidence-deep-article-feature.json"
            ).read_text(encoding="utf-8")
        )

        self.assertIn("매일 오전 10시", manifest["contract_fields"]["requirement"])
        self.assertIn(
            "하루 발행 상한은 한 건",
            manifest["contract_fields"]["completion_result"],
        )
        self.assertIn(
            "tests.test_evidence_deep_article.EvidenceDeepArticleTests."
            "test_daily_limit_is_one_successful_publication",
            manifest["tests"],
        )
        self.assertIn(
            "tests.test_evidence_deep_article.EvidenceDeepArticleTests."
            "test_timer_runs_daily_at_ten",
            manifest["tests"],
        )
        log_path = Path(manifest["logs"][0])
        digest = hashlib.sha256(log_path.read_bytes()).hexdigest()
        self.assertEqual(manifest["test_runs"][0]["output_sha256"], digest)
        source_revision = manifest["test_runs"][0]["source_revision"]
        self.assertEqual(source_revision, manifest["fix_commit"])
        self.assertTrue(
            any(
                "/evidence/test-results/evidence-lane-tests.log" in url
                and "/blob/" in url
                for url in manifest["public_urls"]
            )
        )


if __name__ == "__main__":
    unittest.main()
