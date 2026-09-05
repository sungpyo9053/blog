from __future__ import annotations

import json, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.run_evidence_deep_article import DAILY_LIMIT, execute, published_today


class EvidenceDeepArticleTests(unittest.TestCase):
    def inventory(self, root: Path) -> Path:
        path=root/"inventory.json"; path.write_text(json.dumps({"metadata":{"complete":True},"posts":[]}),encoding="utf-8"); return path

    def payload(self, candidates):
        return ({"candidates":candidates,"status":"ready" if candidates else "no_publishable_topic"},{"processed":[]},{})

    def test_no_topic_is_success_and_never_calls_publisher(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); runner=Mock()
            with patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload([])), patch("scripts.run_evidence_deep_article.persist_miner_run"):
                result=execute(run_id="20260905T010000Z-aaaaaaaaaa",inventory_path=self.inventory(root),apply=True,topic_runner=runner,output_root=root/"runs",miner_root=root/"miner",repo=root)
        self.assertEqual(result["deep_article"],"no_publishable_topic")
        self.assertFalse(result["failed"]); self.assertEqual(result["wordpress_write_count"],0); runner.assert_not_called()

    def test_ready_dry_run_has_zero_wordpress_writes(self):
        candidate={"candidate_id":"one"}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); runner=Mock()
            with patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload([candidate])), patch("scripts.run_evidence_deep_article.persist_miner_run"):
                result=execute(run_id="20260905T010000Z-bbbbbbbbbb",inventory_path=self.inventory(root),apply=False,topic_runner=runner,output_root=root/"runs",miner_root=root/"miner",repo=root)
        self.assertEqual(result["deep_article"],"ready_not_published"); self.assertEqual(result["wordpress_write_count"],0); runner.assert_not_called()

    def test_apply_selects_only_one_ready_candidate(self):
        candidates=[{"candidate_id":"one"},{"candidate_id":"two"}]; runner=Mock(return_value={"post_id":999,"url":"https://example.test/post"}); auditor=Mock(return_value={"http_status":200})
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload(candidates)), patch("scripts.run_evidence_deep_article.persist_miner_run"):
                result=execute(run_id="20260905T010000Z-cccccccccc",inventory_path=self.inventory(root),apply=True,topic_runner=runner,public_auditor=auditor,output_root=root/"runs",miner_root=root/"miner",repo=root)
        self.assertEqual(result["deep_article"],"published"); self.assertEqual(result["wordpress_write_count"],1); runner.assert_called_once(); self.assertEqual(runner.call_args.args[0]["candidate_id"],"one")

    def test_daily_limit_is_two_successful_publications(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index in range(DAILY_LIMIT):
                path=root/f"run-{index}"; path.mkdir(); (path/"result.json").write_text(json.dumps({"kst_date":"2026-09-05","deep_article":"published","failed":False}))
            self.assertEqual(published_today(root,"2026-09-05"),2)

    def test_timer_runs_twice_daily(self):
        timer=Path("deploy/huntlab-evidence-deep-article.timer").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* 10,22:00:00 Asia/Seoul",timer)
        self.assertIn("Persistent=false",timer)


if __name__ == "__main__": unittest.main()
