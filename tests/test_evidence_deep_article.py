from __future__ import annotations

import hashlib, json, logging, tempfile, unittest
import contextlib, io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.run_evidence_deep_article import DAILY_LIMIT, PipelineError, audit_evidence_links, candidate_plan, execute, published_today, resume_public_audit, run_selected_candidate
from scripts.run_evidence_deep_article import main, candidate_in_editorial_scope
from scripts.run_daily_pipeline import PipelineLock


class EvidenceDeepArticleTests(unittest.TestCase):
    logger = logging.getLogger("evidence-deep-test")

    def test_cli_notifies_only_after_execution_result_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); runs = root / "runs"
            result = {"failed": False, "deep_article": "published", "wordpress_write_count": 1}
            def execution(**kwargs):
                (runs / "fresh").mkdir(parents=True)
                return result
            def notification(value):
                self.assertEqual(json.loads((runs / "fresh/result.json").read_text()), value)
                return {"status": "notification_error"}
            with patch("scripts.run_evidence_deep_article.LOCK", root / "lock"), patch("scripts.run_evidence_deep_article.OUTPUT", runs), patch("scripts.run_evidence_deep_article.execute", side_effect=execution), patch("scripts.run_evidence_deep_article.notify_publication", side_effect=notification) as notify, patch("sys.argv", ["deep", "--apply", "--run-id", "fresh", "--inventory", str(root / "inventory")]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            notify.assert_called_once_with(result)
            self.assertFalse(json.loads((runs / "fresh/result.json").read_text())["failed"])

    def test_cli_audit_recovery_notifies_without_running_publisher(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = {"failed": False, "deep_article": "published", "wordpress_write_count": 1}
            with patch("scripts.run_evidence_deep_article.LOCK", root / "lock"), patch("scripts.run_evidence_deep_article.OUTPUT", root / "runs"), patch("scripts.run_evidence_deep_article.resume_public_audit", return_value=result), patch("scripts.run_evidence_deep_article.execute") as execute_mock, patch("scripts.run_evidence_deep_article.notify_publication", return_value={"status": "sent"}) as notify, patch("sys.argv", ["deep", "--resume-public-audit", "--run-id", "existing"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            notify.assert_called_once_with(result)
            execute_mock.assert_not_called()

    def test_response_loss_after_simulated_post_never_retries_automatically(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); writes=[]
            def lost_response(*args):
                writes.append(999)
                raise TimeoutError('simulated server committed then response lost')
            runner=Mock(side_effect=lost_response)
            with patch('scripts.run_evidence_deep_article.build_payload',return_value=self.payload([{}])):
                with self.assertRaises(TimeoutError):
                    execute(run_id='lost',inventory_path=self.inventory(root),apply=True,topic_runner=runner,output_root=root/'runs',miner_root=root/'miner',repo=root,logger=self.logger)
                with self.assertRaisesRegex(PipelineError,'reconciliation required'):
                    execute(run_id='retry',inventory_path=self.inventory(root),apply=True,topic_runner=runner,output_root=root/'runs',miner_root=root/'miner',repo=root,logger=self.logger)
            self.assertEqual(writes,[999]);runner.assert_called_once()
            self.assertEqual(json.loads((root/'runs/lost/progress.json').read_text())['wordpress_write_count'],'unknown')

    def test_post_success_receipt_storage_failures_keep_duplicate_guard(self):
        from scripts.run_evidence_deep_article import write_progress, write_json_new
        for failure in ('confirmed_progress','publication_receipt'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);runner=Mock(return_value={'post_id':999,'url':'https://example.test/post'})
                def progress(path,**fields):
                    if failure=='confirmed_progress' and fields['stage']=='publisher_completed':raise OSError('simulated disk error')
                    write_progress(path,**fields)
                def receipt(path,payload):
                    if failure=='publication_receipt' and path.name=='publication.json':raise OSError('simulated disk error')
                    write_json_new(path,payload)
                with patch('scripts.run_evidence_deep_article.build_payload',return_value=self.payload([{}])), patch('scripts.run_evidence_deep_article.write_progress',side_effect=progress), patch('scripts.run_evidence_deep_article.write_json_new',side_effect=receipt):
                    with self.assertRaises(OSError):
                        execute(run_id='disk',inventory_path=self.inventory(root),apply=True,topic_runner=runner,output_root=root/'runs',miner_root=root/'miner',repo=root,logger=self.logger)
                    if failure=='confirmed_progress':
                        with self.assertRaisesRegex(PipelineError,'reconciliation required'):
                            execute(run_id='next',inventory_path=self.inventory(root),apply=True,topic_runner=runner,output_root=root/'runs',miner_root=root/'miner',repo=root,logger=self.logger)
                    else:
                        result=execute(run_id='next',inventory_path=self.inventory(root),apply=True,topic_runner=runner,output_root=root/'runs',miner_root=root/'miner',repo=root,logger=self.logger)
                        self.assertEqual(result['deep_article'],'daily_limit_reached')
                runner.assert_called_once()

    def test_failed_readonly_cli_resume_does_not_append_execution_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'runs'/'audit';run.mkdir(parents=True)
            progress=run/'progress.json';progress.write_text('{"wordpress_write_count":1}')
            original=progress.read_bytes()
            with patch('scripts.run_evidence_deep_article.LOCK',root/'lock'), patch('scripts.run_evidence_deep_article.OUTPUT',root/'runs'), patch('scripts.run_evidence_deep_article.resume_public_audit',side_effect=RuntimeError('read-only GET failed')), patch('scripts.run_evidence_deep_article.execute') as runner, patch('sys.argv',['deep','--resume-public-audit','--run-id','audit']), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(),1)
            runner.assert_not_called();self.assertEqual(progress.read_bytes(),original)
            self.assertFalse((run/'result.json').exists())

    def test_concurrent_cli_rejection_does_not_create_unknown_or_touch_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); lock_path=root/'lock'; owner=PipelineLock(lock_path)
            owner.acquire(); original=lock_path.read_bytes()
            try:
                with patch('scripts.run_evidence_deep_article.LOCK',lock_path), patch('scripts.run_evidence_deep_article.OUTPUT',root/'runs'), patch('scripts.run_evidence_deep_article.execute') as runner, patch('scripts.run_evidence_deep_article.refresh_inventory') as inventory, patch('sys.argv',['deep','--apply','--run-id','contender']), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(),1)
                runner.assert_not_called(); inventory.assert_not_called()
                self.assertEqual(lock_path.read_bytes(),original)
                self.assertFalse((root/'runs/contender').exists())
            finally:owner.release()
    def inventory(self, root: Path) -> Path:
        path=root/"inventory.json"; path.write_text(json.dumps({"metadata":{"complete":True},"posts":[]}),encoding="utf-8"); return path

    def payload(self, candidates):
        normalized=[]
        for source in candidates:
            row={"candidate_id":"one","title_seed":"title","real_trigger":"trigger","target_reader":"reader","problem":"problem","why_it_matters":"action","evidence_contract":{},"evidence":{"commits":[],"files":[],"tests":[],"logs":[],"public_urls":[]},"before_after":{},"unique_takeaway":"takeaway","existing_post_overlap":{"result":"none"},"recommended_format":"feature_build","publishability":"READY","missing_evidence":[],"rejection_reason":None,"source_anchor":"scripts/x.py"}
            row["problem"] = "로봇 관측 입력 문제"
            row.update(source); normalized.append(row)
        return ({"date":"2026-09-05","source_head":"a"*40,"candidates":normalized,"status":"ready" if normalized else "no_publishable_topic"},{"processed":[]},{})

    def test_no_topic_is_success_and_never_calls_publisher(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); runner=Mock()
            with patch("scripts.run_evidence_deep_article.build_payload",return_value=self.payload([])), patch("scripts.run_evidence_deep_article.persist_miner_run"):
                result=execute(run_id="20260905T010000Z-aaaaaaaaaa",inventory_path=self.inventory(root),apply=True,topic_runner=runner,output_root=root/"runs",miner_root=root/"miner",repo=root)
        self.assertEqual(result["deep_article"],"no_publishable_topic")
        self.assertFalse(result["failed"]); self.assertEqual(result["wordpress_write_count"],0); runner.assert_not_called()

    def test_supply_runs_only_when_apply_enabled_empty_and_below_limit(self):
        cases = ((True, True, 0, False, True), (False, True, 0, False, False),
                 (True, False, 0, False, False), (True, True, 1, False, False),
                 (True, True, 0, True, False))
        for apply, enabled, count, existing, expected in cases:
            with self.subTest(case=(apply, enabled, count, existing)), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); runner = Mock(return_value={'post_id': 999, 'url': 'https://example.test/post'})
                with patch('scripts.run_evidence_deep_article.build_payload', return_value=self.payload([{}] if existing else [])), \
                     patch('scripts.run_evidence_deep_article.discovery_enabled', return_value=enabled), \
                     patch('scripts.run_evidence_deep_article.published_today', return_value=count), \
                     patch('scripts.run_evidence_deep_article.load_foundation_candidates', return_value=([], [])), \
                     patch('scripts.run_evidence_deep_article.replenish_candidates', return_value={'status': 'no_candidate'}) as supply:
                    execute(run_id='supply-policy', inventory_path=self.inventory(root), apply=apply,
                            topic_runner=runner, public_auditor=Mock(return_value={'http_status': 200}),
                            output_root=root/'runs', miner_root=root/'miner', repo=root)
                self.assertEqual(supply.call_count, int(expected))
                if not existing or not apply:
                    runner.assert_not_called()

    def test_existing_foundation_ready_does_not_invoke_supply(self):
        candidate = self.payload([{'candidate_origin': 'foundation_concept'}])[0]['candidates'][0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch('scripts.run_evidence_deep_article.build_payload', return_value=self.payload([])), \
                 patch('scripts.run_evidence_deep_article.load_foundation_candidates', return_value=([candidate], [])), \
                 patch('scripts.run_evidence_deep_article.discovery_enabled', return_value=True), \
                 patch('scripts.run_evidence_deep_article.foundation_activation_ready', return_value=False), \
                 patch('scripts.run_evidence_deep_article.replenish_candidates') as supply:
                result = execute(run_id='existing', inventory_path=self.inventory(root), apply=True,
                                 output_root=root/'runs', miner_root=root/'miner', repo=root)
            supply.assert_not_called()
            self.assertEqual(result['deep_article'], 'foundation_activation_required')

    def test_unknown_write_history_blocks_supply_before_provider_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); previous = root/'runs/previous'; previous.mkdir(parents=True)
            (previous/'progress.json').write_text(json.dumps({'wordpress_write_count': 'unknown'}))
            runner = Mock()
            with patch('scripts.run_evidence_deep_article.build_payload', return_value=self.payload([])), \
                 patch('scripts.run_evidence_deep_article.discovery_enabled', return_value=True), \
                 patch('scripts.run_evidence_deep_article.load_foundation_candidates', return_value=([], [])), \
                 patch('scripts.run_evidence_deep_article.replenish_candidates') as supply:
                with self.assertRaisesRegex(PipelineError, 'reconciliation required'):
                    execute(run_id='blocked', inventory_path=self.inventory(root), apply=True,
                            topic_runner=runner, output_root=root/'runs', miner_root=root/'miner', repo=root)
            supply.assert_not_called()
            runner.assert_not_called()

    def test_producer_ready_is_reloaded_through_candidate_contract(self):
        candidate = self.payload([{'candidate_origin': 'foundation_concept'}])[0]['candidates'][0]
        for accepted in (True, False):
            with self.subTest(accepted=accepted), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); runner = Mock(return_value={'post_id': 999, 'url': 'https://example.test/post'})
                reloaded = ([candidate], []) if accepted else ([], [{'reason': 'invalid manifest'}])
                with patch('scripts.run_evidence_deep_article.build_payload', return_value=self.payload([])), \
                     patch('scripts.run_evidence_deep_article.load_foundation_candidates', side_effect=[([], []), reloaded]) as loader, \
                     patch('scripts.run_evidence_deep_article.discovery_enabled', return_value=True), \
                     patch('scripts.run_evidence_deep_article.foundation_activation_ready', return_value=True), \
                     patch('scripts.run_evidence_deep_article.replenish_candidates', return_value={'status': 'ready'}) as supply:
                    args = dict(run_id='reload', inventory_path=self.inventory(root), apply=True,
                                topic_runner=runner, public_auditor=Mock(return_value={'http_status': 200}),
                                output_root=root/'runs', miner_root=root/'miner', repo=root)
                    if accepted:
                        self.assertEqual(execute(**args)['deep_article'], 'published')
                        runner.assert_called_once()
                    else:
                        with self.assertRaisesRegex(PipelineError, 'discovery_candidate_contract_rejected'):
                            execute(**args)
                        runner.assert_not_called()
                    supply.assert_called_once()
                    self.assertEqual(loader.call_count, 2)

    def test_supply_provider_failure_is_not_empty_topic_success(self):
        for output in (None, {'status': 'provider_failed'}, TimeoutError('synthetic provider outage')):
            with self.subTest(output=output), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); runner = Mock()
                supply = Mock(side_effect=output) if isinstance(output, Exception) else Mock(return_value=output)
                with patch('scripts.run_evidence_deep_article.build_payload', return_value=self.payload([])), \
                     patch('scripts.run_evidence_deep_article.discovery_enabled', return_value=True), \
                     patch('scripts.run_evidence_deep_article.load_foundation_candidates', return_value=([], [])), \
                     patch('scripts.run_evidence_deep_article.replenish_candidates', supply):
                    with self.assertRaises((PipelineError, TimeoutError)):
                        execute(run_id='outage', inventory_path=self.inventory(root), apply=True,
                                topic_runner=runner, output_root=root/'runs', miner_root=root/'miner', repo=root)
                runner.assert_not_called()
                progress = json.loads((root/'runs/outage/progress.json').read_text())
                self.assertEqual(progress['stage'], 'discovery_started')
                self.assertEqual(progress['wordpress_write_count'], 0)

    def test_cli_supply_failure_reports_candidate_supply_and_zero_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); runs = root/'runs'; stdout = io.StringIO()
            def failed_execution(**kwargs):
                run = runs/kwargs['run_id']; run.mkdir(parents=True)
                (run/'progress.json').write_text(json.dumps({'stage': 'discovery_started', 'wordpress_write_count': 0}))
                raise TimeoutError('synthetic provider error')
            with patch('scripts.run_evidence_deep_article.OUTPUT', runs), \
                 patch('scripts.run_evidence_deep_article.LOCK', root/'lock'), \
                 patch('scripts.run_evidence_deep_article.execute', side_effect=failed_execution), \
                 patch('scripts.run_evidence_deep_article.notify_publication') as notify, \
                 patch('sys.argv', ['deep', '--apply', '--run-id', 'supply-cli', '--inventory', str(root/'inventory')]), \
                 contextlib.redirect_stdout(stdout):
                self.assertEqual(main(), 1)
            result = json.loads(stdout.getvalue())
            self.assertTrue(result['failed'])
            self.assertEqual(result['deep_article'], 'failed')
            self.assertEqual(result['failure_stage'], 'candidate_supply')
            self.assertEqual(result['wordpress_write_count'], 0)
            self.assertEqual(json.loads((runs/'supply-cli/result.json').read_text()), result)
            notify.assert_not_called()

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

    def test_foundation_route_uses_shared_limit_and_requires_draft_activation(self):
        candidate = self.payload([{"candidate_origin": "foundation_concept", "candidate_id": "foundation-one"}])[0]["candidates"][0]
        self.assertEqual(candidate_plan(candidate)["content_type"], "foundation_concept")
        for mode, active, count, expected in ((False, False, 0, "ready_not_published"),
                                              (True, False, 0, "foundation_activation_required"),
                                              (True, True, 1, "daily_limit_reached"),
                                              (True, True, 0, "published")):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); runner = Mock(return_value={"post_id": 999, "url": "https://example.test/post"})
                with patch('scripts.run_evidence_deep_article.build_payload', return_value=self.payload([])), patch('scripts.run_evidence_deep_article.load_foundation_candidates', return_value=([candidate], [])), patch('scripts.run_evidence_deep_article.foundation_activation_ready', return_value=active), patch('scripts.run_evidence_deep_article.published_today', return_value=count):
                    result = execute(run_id='foundation-run', inventory_path=self.inventory(root), apply=mode,
                                     topic_runner=runner, public_auditor=Mock(return_value={"http_status": 200}),
                                     output_root=root/'runs', miner_root=root/'miner', repo=root, logger=self.logger)
                self.assertEqual(result['deep_article'], expected)
                self.assertEqual(runner.call_count, int(expected == 'published'))

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
        from scripts.run_daily_pipeline import EDITOR_CATEGORIES as PIPELINE_CATEGORIES
        for title, category in (("피지컬 AI 용어 입문", "피지컬 AI 기초"),
                                ("로봇 제어 원리", "원리·알고리즘"),
                                ("MuJoCo 첫 실행", "프레임워크·라이브러리"),
                                ("MuJoCo 지연시간 실험", "실습·실험")):
            candidate = self.payload([{"title_seed": title, "problem": title}])[0]["candidates"][0]
            plan = candidate_plan(candidate)
            self.assertEqual(plan["category"], category)
            self.assertIn(category, EDITOR_CATEGORIES)
            self.assertIn(category, PIPELINE_CATEGORIES)

    def test_physical_scope_requires_ready_and_reader_problem_not_incidental_evidence(self):
        for subject in ("피지컬AI 입문", "로봇 관측", "MuJoCo 예제", "ROS 2 시작", "embodied AI", "에이전트 루프 원리", "agent memory", "tool calling"):
            self.assertTrue(candidate_in_editorial_scope({"publishability": "READY", "title_seed": subject}))
            self.assertFalse(candidate_in_editorial_scope({"publishability": "NEEDS_EVIDENCE", "title_seed": subject}))
        for subject in ("WordPress REST 발행", "강화학습 뉴스", "AI 신제품", "rosary", "policy update", "에이전트 신제품 뉴스"):
            self.assertFalse(candidate_in_editorial_scope({
                "publishability": "READY", "title_seed": subject,
                "unique_takeaway": "나중에 로봇에 적용", "evidence": {"files": ["mujoco.py"]}}))

    def test_physical_plan_requires_beginner_context_and_real_execution_evidence(self):
        plan = candidate_plan(self.payload([{}])[0]["candidates"][0])
        for requirement in ("선수 지식", "한국어 뜻과 영문", "공식 문서", "확인일", "검증한 버전", "실제 결과", "시뮬레이션", "하드웨어", "근거 부족은 보류"):
            self.assertIn(requirement, plan["research_focus"])
        self.assertIn("피지컬 AI", plan["tags"])

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
                                 topic_runner=runner, output_root=root / "runs", miner_root=root / "miner", repo=root)
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
