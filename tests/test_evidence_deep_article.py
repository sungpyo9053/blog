from __future__ import annotations

import json, logging, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.run_evidence_deep_article import DAILY_LIMIT, execute, published_today


class EvidenceDeepArticleTests(unittest.TestCase):
    logger = logging.getLogger("evidence-deep-test")
    def inventory(self, root: Path) -> Path:
        path=root/"inventory.json"; path.write_text(json.dumps({"metadata":{"complete":True},"posts":[]}),encoding="utf-8"); return path

    def payload(self, candidates):
        normalized=[]
        for source in candidates:
            row={"candidate_id":"one","title_seed":"title","real_trigger":"trigger","target_reader":"reader","problem":"problem","why_it_matters":"action","evidence_contract":{},"evidence":{"commits":[],"files":[],"tests":[],"logs":[],"public_urls":[]},"before_after":{},"unique_takeaway":"takeaway","existing_post_overlap":{"result":"none"},"recommended_format":"feature_build","publishability":"READY","missing_evidence":[],"rejection_reason":None,"source_anchor":"scripts/x.py"}
            row.update(source); normalized.append(row)
        return ({"date":"2026-09-05","source_head":"a"*40,"candidates":normalized,"status":"ready" if normalized else "no_publishable_topic"},{"processed":[]},{})

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

    def test_ready_dry_run_does_not_advance_global_checkpoint(self):
        candidate={"candidate_id":"one"}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); inventory=self.inventory(root)
            with patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload([candidate])):
                execute(run_id="20260905T010000Z-dddddddddd",inventory_path=inventory,apply=False,topic_runner=Mock(),output_root=root/"runs",miner_root=root/"miner",repo=root)
            self.assertFalse((root/"miner/checkpoint.json").exists())
            self.assertTrue((root/"runs/20260905T010000Z-dddddddddd/miner-checkpoint.json").exists())

    def test_apply_selects_only_one_ready_candidate(self):
        candidates=[{"candidate_id":"one"},{"candidate_id":"two"}]; runner=Mock(return_value={"post_id":999,"url":"https://example.test/post"}); auditor=Mock(return_value={"http_status":200})
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload(candidates)), patch("scripts.run_evidence_deep_article.persist_miner_run"):
                result=execute(run_id="20260905T010000Z-cccccccccc",inventory_path=self.inventory(root),apply=True,topic_runner=runner,public_auditor=auditor,output_root=root/"runs",miner_root=root/"miner",repo=root,logger=self.logger)
        self.assertEqual(result["deep_article"],"published"); self.assertEqual(result["wordpress_write_count"],1); runner.assert_called_once(); self.assertEqual(runner.call_args.args[0]["candidate_id"],"one")

    def test_publisher_failure_does_not_consume_candidate_checkpoint(self):
        candidate={"candidate_id":"one"}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload([candidate])):
                with self.assertRaises(RuntimeError):
                    execute(run_id="20260905T010000Z-eeeeeeeeee",inventory_path=self.inventory(root),apply=True,topic_runner=Mock(side_effect=RuntimeError("publish failed")),output_root=root/"runs",miner_root=root/"miner",repo=root,logger=self.logger)
            self.assertFalse((root/"miner/checkpoint.json").exists())

    def test_daily_limit_is_two_successful_publications(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index in range(DAILY_LIMIT):
                path=root/f"run-{index}"; path.mkdir(); (path/"result.json").write_text(json.dumps({"kst_date":"2026-09-05","deep_article":"published","failed":False}))
            self.assertEqual(published_today(root,"2026-09-05"),2)

    def test_timer_runs_twice_daily(self):
        timer=Path("deploy/huntlab-evidence-deep-article.timer").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* 10:00:00 Asia/Seoul",timer)
        self.assertIn("OnCalendar=*-*-* 22:00:00 Asia/Seoul",timer)
        self.assertIn("Persistent=false",timer)


if __name__ == "__main__": unittest.main()
