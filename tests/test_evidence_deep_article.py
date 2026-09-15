from __future__ import annotations

import hashlib, json, logging, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.run_evidence_deep_article import DAILY_LIMIT, PipelineError, audit_evidence_links, candidate_plan, execute, published_today, resume_public_audit, run_selected_candidate


class EvidenceDeepArticleTests(unittest.TestCase):
    logger = logging.getLogger("evidence-deep-test")
    def inventory(self, root: Path) -> Path:
        path=root/"inventory.json"; path.write_text(json.dumps({"metadata":{"complete":True},"posts":[]}),encoding="utf-8"); return path

    def payload(self, candidates):
        normalized=[]
        for source in candidates:
            row={"candidate_id":"one","title_seed":"title","real_trigger":"trigger","target_reader":"reader","problem":"problem","why_it_matters":"action","evidence_contract":{},"evidence":{"commits":[],"files":[],"tests":[],"logs":[],"public_urls":[]},"before_after":{},"unique_takeaway":"takeaway","existing_post_overlap":{"result":"none"},"recommended_format":"feature_build","publishability":"READY","missing_evidence":[],"rejection_reason":None,"source_anchor":"scripts/x.py"}
            row["problem"] = "WordPress 발행 문제"
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

    def test_candidate_primary_keyword_is_present_in_fixed_title(self):
        candidate = self.payload([{"candidate_id": "one"}])[0]["candidates"][0]
        plan = candidate_plan(candidate)
        self.assertIn(plan["primary_keyword"].casefold(), plan["title"].casefold())

    def test_missing_required_public_commit_link_is_rejected_before_writes(self):
        candidate = {"evidence": {"commits": ["a" * 40], "files": [], "tests": [], "logs": [],
                     "public_urls": ["https://github.com/example/repo/blob/" + "a" * 40 + "/source.py"]}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); runner = Mock()
            with patch("scripts.run_evidence_deep_article.build_payload", return_value=self.payload([candidate])):
                with self.assertRaisesRegex(PipelineError, "public sources"):
                    execute(run_id="20260916T010000Z-sources", inventory_path=self.inventory(root),
                            apply=True, topic_runner=runner, output_root=root/"runs", miner_root=root/"miner", repo=root)
            runner.assert_not_called()
            progress = json.loads((root/"runs/20260916T010000Z-sources/progress.json").read_text())
            self.assertEqual(progress["wordpress_write_count"], 0)

    def test_candidate_uses_reader_problem_taxonomy_accepted_by_publisher(self):
        from publisher.validation import EDITOR_CATEGORIES
        for title, category in (("WordPress REST API 재시도", "REST API 발행"),
                                ("WordPress 사이트맵 검증", "WordPress 운영"),
                                ("READY 파이프라인 테스트", "자동화·테스트")):
            candidate = self.payload([{"title_seed": title, "problem": title}])[0]["candidates"][0]
            plan = candidate_plan(candidate)
            self.assertEqual(plan["category"], category)
            self.assertIn(category, EDITOR_CATEGORIES)

    def test_out_of_scope_ready_candidate_has_no_wordpress_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = Mock()
            payload = self.payload([{"title_seed":"AI 신제품 뉴스", "problem":"범용 뉴스"}])
            with patch("scripts.run_evidence_deep_article.build_payload", return_value=payload), patch("scripts.run_evidence_deep_article.persist_miner_run"):
                result = execute(run_id="scope-test", inventory_path=self.inventory(root), apply=True, topic_runner=runner, output_root=root/"runs", miner_root=root/"miner", repo=root)
            self.assertEqual(result["deep_article"], "no_publishable_topic")
            self.assertEqual(result["scope_rejections"], ["one"])
            runner.assert_not_called()

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

    def test_selected_candidate_creates_daily_pipeline_run_directory(self):
        candidate=self.payload([{"candidate_id":"one"}])[0]["candidates"][0]
        with tempfile.TemporaryDirectory() as directory:
            runs=Path(directory)/"runs"
            runner=Mock(return_value={"post_id":999,"url":"https://example.test/post"})
            with patch("scripts.run_daily_pipeline.RUNS_DIR",runs), patch("scripts.run_evidence_deep_article.resolve_codex",return_value="codex"), patch("scripts.run_evidence_deep_article.run_topic_pipeline",runner):
                result=run_selected_candidate(candidate,"20260907T010017Z-2619e2d463",self.logger)
            self.assertEqual(result["post_id"],999)
            context=runner.call_args.args[1]
            self.assertTrue(context.directory.parent.is_dir())

    def test_publisher_failure_does_not_consume_candidate_checkpoint(self):
        candidate={"candidate_id":"one"}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload([candidate])):
                with self.assertRaises(RuntimeError):
                    execute(run_id="20260905T010000Z-eeeeeeeeee",inventory_path=self.inventory(root),apply=True,topic_runner=Mock(side_effect=RuntimeError("publish failed")),output_root=root/"runs",miner_root=root/"miner",repo=root,logger=self.logger)
            self.assertFalse((root/"miner/checkpoint.json").exists())

    def test_public_audit_failure_after_publish_consumes_candidate_checkpoint(self):
        candidate={"candidate_id":"one"}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload([candidate])):
                with self.assertRaises(RuntimeError):
                    execute(run_id="20260905T010000Z-auditfailed",inventory_path=self.inventory(root),apply=True,topic_runner=Mock(return_value={"post_id":999,"url":"https://example.test/post"}),public_auditor=Mock(side_effect=RuntimeError("audit failed")),output_root=root/"runs",miner_root=root/"miner",repo=root,logger=self.logger)
            self.assertTrue((root/"miner/checkpoint.json").is_file())

    def test_public_evidence_audit_requires_representative_link_per_kind(self):
        evidence={
            "commits":["abc"],
            "files":["scripts/run.py"],
            "tests":["tests.test_run.RunTests.test_ok"],
            "logs":["evidence/test-results/run.log"],
            "public_urls":[
                "https://github.com/example/repo/commit/abc",
                "https://github.com/example/repo/blob/abc/scripts/run.py",
                "https://github.com/example/repo/blob/def/tests/test_run.py",
                "https://github.com/example/repo/blob/def/evidence/test-results/run.log",
                "https://github.com/example/repo/commit/not-cited",
            ],
        }
        body=" ".join(evidence["public_urls"][:4])
        result=audit_evidence_links(body,evidence)
        self.assertTrue(result["passed"])
        self.assertEqual(result["matched_count"],4)

    def test_failed_run_with_confirmed_wordpress_write_counts_toward_daily_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); run=root/"partial"; run.mkdir()
            (run/"result.json").write_text(json.dumps({"kst_date":"2026-09-05","deep_article":"failed","failed":True,"wordpress_write_count":1}))
            self.assertEqual(published_today(root,"2026-09-05"),1)

    def test_daily_limit_is_one_successful_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index in range(DAILY_LIMIT):
                path=root/f"run-{index}"; path.mkdir(); (path/"result.json").write_text(json.dumps({"kst_date":"2026-09-05","deep_article":"published","failed":False}))
            self.assertEqual(published_today(root,"2026-09-05"),1)

    def test_unknown_write_requires_reconciliation_even_on_later_day(self):
        for filename in ("result.json", "progress.json"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); run = root / "timeout"; run.mkdir()
                (run / filename).write_text(json.dumps({"kst_date": "2026-09-05", "wordpress_write_count": "unknown"}))
                for day in ("2026-09-05", "2026-09-06"):
                    with self.assertRaisesRegex(PipelineError, "reconciliation required"):
                        published_today(root, day)

    def reconciliation(self, run, count=0):
        evidence = []
        for kind in ("pipeline_trace", "wordpress_inventory"):
            p = run / (kind + ".json")
            p.write_text(json.dumps({"kind": kind, "reviewed_write_count": count}))
            evidence.append({"kind": kind, "path": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        return {"schema_version": 1, "run_id": run.name, "wordpress_write_count": count,
                "kst_date": "2026-09-05", "checked_at": "2026-09-16T00:00:00+09:00", "reviewed_by": "operator",
                "original_state_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in (run / "result.json", run / "progress.json") if p.exists()},
                "evidence": evidence}

    def test_reconciliation_preserves_original_and_resolves_unknown(self):
        for count in (0, 1):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); run = root / "unknown"; run.mkdir()
                p = run / "progress.json"; p.write_text(json.dumps({"wordpress_write_count": "unknown"}))
                original = p.read_bytes()
                (run / "reconciliation.json").write_text(json.dumps(self.reconciliation(run, count)))
                self.assertEqual(published_today(root, "2026-09-05"), count)
                self.assertEqual(published_today(root, "2026-09-06"), 0)
                self.assertEqual(p.read_bytes(), original)

    def test_reconciliation_rejects_stale_state_evidence_and_unknown_count(self):
        for mutation in ("state", "evidence", "unknown", "bool", "missing_inventory", "wrong_run", "traversal"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); run = root / "unknown"; run.mkdir()
                p = run / "progress.json"; p.write_text(json.dumps({"wordpress_write_count": "unknown"}))
                receipt = self.reconciliation(run)
                if mutation == "state": p.write_text(json.dumps({"wordpress_write_count": "unknown", "stage": "changed"}))
                elif mutation == "evidence": (run / "pipeline_trace.json").write_text("changed")
                elif mutation == "unknown": receipt["wordpress_write_count"] = "unknown"
                elif mutation == "bool": receipt["wordpress_write_count"] = False
                elif mutation == "missing_inventory": receipt["evidence"].pop()
                elif mutation == "wrong_run": receipt["run_id"] = "another"
                elif mutation == "traversal": receipt["evidence"][0]["path"] = "../outside.json"
                (run / "reconciliation.json").write_text(json.dumps(receipt))
                with self.assertRaisesRegex(PipelineError, "Invalid publication reconciliation"):
                    published_today(root, "2026-09-06")

    def test_reconciliation_cannot_erase_confirmed_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / "confirmed"; run.mkdir()
            (run / "progress.json").write_text(json.dumps({"wordpress_write_count": 1}))
            (run / "reconciliation.json").write_text(json.dumps(self.reconciliation(run, 0)))
            with self.assertRaisesRegex(PipelineError, "contradicts confirmed write"):
                published_today(root, "2026-09-05")

    def test_orphan_confirmed_progress_consumes_daily_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / "killed"; run.mkdir()
            record = {"kst_date": "2026-09-05", "wordpress_write_count": 1}
            (run / "progress.json").write_text(json.dumps(record))
            self.assertEqual(published_today(root, "2026-09-05"), 1)
            (run / "result.json").write_text(json.dumps(record))
            self.assertEqual(published_today(root, "2026-09-05"), 1)
            self.assertEqual(published_today(root, "2026-09-06"), 0)

    def test_corrupt_receipt_is_not_assumed_zero_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / "corrupt"; run.mkdir()
            (run / "result.json").write_text("{")
            with self.assertRaisesRegex(PipelineError, "Unreadable publication state"):
                published_today(root, "2026-09-05")

    def test_reused_run_id_cannot_erase_unknown_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / "runs" / "same"; run.mkdir(parents=True)
            progress = run / "progress.json"
            original = json.dumps({"wordpress_write_count": "unknown"})
            progress.write_text(original)
            runner = Mock()
            with self.assertRaises(FileExistsError):
                execute(run_id="same", inventory_path=self.inventory(root), apply=True,
                        topic_runner=runner, output_root=root / "runs", miner_root=root / "miner")
            self.assertEqual(progress.read_text(), original)
            runner.assert_not_called()

    def test_unknown_prior_write_prevents_new_publisher_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / "runs" / "previous"; run.mkdir(parents=True)
            (run / "progress.json").write_text(json.dumps({"wordpress_write_count": "unknown"}))
            runner = Mock()
            with patch("scripts.run_evidence_deep_article.build_payload", return_value=self.payload([{}])):
                with self.assertRaisesRegex(PipelineError, "reconciliation required"):
                    execute(run_id="next", inventory_path=self.inventory(root), apply=True,
                            topic_runner=runner, output_root=root / "runs", miner_root=root / "miner")
            runner.assert_not_called()

    def test_no_candidate_with_unknown_history_is_zero_write_without_checkpoint_advance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / "runs" / "previous"; run.mkdir(parents=True)
            (run / "progress.json").write_text(json.dumps({"wordpress_write_count": "unknown"}))
            runner = Mock()
            with patch("scripts.run_evidence_deep_article.build_payload", return_value=self.payload([])):
                result = execute(run_id="empty", inventory_path=self.inventory(root), apply=True,
                                 topic_runner=runner, output_root=root / "runs", miner_root=root / "miner")
            self.assertFalse(result["failed"])
            self.assertEqual(result["deep_article"], "no_publishable_topic")
            self.assertTrue(result["reconciliation_required"])
            self.assertFalse(result["checkpoint_advanced"])
            self.assertFalse((root / "miner/checkpoint.json").exists())
            runner.assert_not_called()

    def test_audit_failure_can_resume_without_publisher_or_candidate_mining(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = Mock(return_value={"post_id": 999, "url": "https://example.test/post"})
            with patch("scripts.run_evidence_deep_article.build_payload", return_value=self.payload([{}])):
                with self.assertRaisesRegex(RuntimeError, "audit failed"):
                    execute(run_id="audit-retry", inventory_path=self.inventory(root), apply=True,
                            topic_runner=runner, public_auditor=Mock(side_effect=RuntimeError("audit failed")),
                            output_root=root / "runs", miner_root=root / "miner")
            auditor = Mock(return_value={"http_status": 200})
            with patch("scripts.run_evidence_deep_article.build_payload") as miner:
                result = resume_public_audit("audit-retry", output_root=root / "runs", public_auditor=auditor)
                miner.assert_not_called()
            runner.assert_called_once()
            self.assertEqual(result["publication"]["post_id"], 999)
            self.assertEqual(result["deep_article"], "published")
            self.assertFalse(result["failed"])
            self.assertTrue((root / "runs/audit-retry/public-audit-recovery.json").exists())

    def test_second_ready_candidate_on_same_day_is_not_published(self):
        candidate={"candidate_id":"two"}; runner=Mock()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); previous=root/"previous"; previous.mkdir(parents=True)
            (previous/"result.json").write_text(json.dumps({"kst_date":"2026-09-05","deep_article":"published","failed":False}))
            with patch("scripts.run_evidence_deep_article.datetime") as clock, patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload([candidate])), patch("scripts.run_evidence_deep_article.persist_miner_run"):
                clock.now.return_value=datetime(2026,9,5,10,0,tzinfo=timezone(timedelta(hours=9)))
                result=execute(run_id="20260905T020000Z-fffffffffff",inventory_path=self.inventory(root),apply=True,topic_runner=runner,output_root=root,miner_root=root/"miner",repo=root)
        self.assertEqual(result["deep_article"],"daily_limit_reached")
        self.assertEqual(result["wordpress_write_count"],0)
        runner.assert_not_called()

    def test_timer_runs_daily_at_ten(self):
        timer=Path("deploy/huntlab-evidence-deep-article.timer").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* 10:00:00 Asia/Seoul",timer)
        self.assertNotIn("OnCalendar=*-*-* 22:00:00 Asia/Seoul",timer)
        self.assertIn("Persistent=false",timer)


if __name__ == "__main__": unittest.main()
