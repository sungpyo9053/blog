import json
import tempfile
import unittest
import contextlib
import io
from pathlib import Path
from unittest.mock import patch, Mock

from scripts.send_kakao_report import deep_status, message_for, run_day, send


class KakaoReportTests(unittest.TestCase):
    def test_preparation_is_not_reported_as_daily_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run=root/'output/evidence-deep-article-runs/20260920T050000Z-prepare'
            run.mkdir(parents=True)
            (run/'result.json').write_text(json.dumps({'run_kind':'preparation','deep_article':'prepared','failed':False}))
            self.assertIn('실행 결과 없음',deep_status(root,'2026-09-20')[0])

    def test_held_queue_is_not_reported_as_no_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); run=root/'output/evidence-deep-article-runs/20260920T010000Z-release'
            run.mkdir(parents=True)
            (run/'result.json').write_text(json.dumps({'deep_article':'no_publishable_topic','held':[{'queue_id':'one'}],'failed':False}))
            self.assertIn('대기 원고 1건 재검수 필요',deep_status(root,'2026-09-20')[0])

    def test_transport_checks_runtime_before_attempting_send(self):
        with patch('scripts.send_kakao_report.subprocess.run', return_value=Mock(returncode=1, stdout='', stderr='private')) as run:
            with self.assertRaises(RuntimeError):
                send('test', '/approved/bin/mcporter')
            self.assertEqual(run.call_args.args[0], ['/approved/bin/mcporter', '--version'])
            self.assertEqual(run.call_count, 1)

    def test_failure_report_is_not_silenced_by_routine_policy(self):
        from scripts.send_kakao_report import routine_status
        self.assertFalse(routine_status(('조회 실패(발행 여부 미확인)',''), None))
        self.assertFalse(routine_status(('발행 완료',''), ('발행 1건(발행 기록) / 후속 처리 실패','')))
        self.assertTrue(routine_status(('발행 완료',''), ('미발행: READY 0건(정상 종료)','')))

    def test_transport_uses_companion_node_path(self):
        with patch('scripts.send_kakao_report.subprocess.run', return_value=Mock(returncode=0, stdout='메시지를 성공적으로 보냈습니다')) as run:
            send('test', '/approved/bin/mcporter')
            self.assertTrue(run.call_args.kwargs['env']['PATH'].startswith('/approved/bin:'))

    def test_quiet_daily_success_is_recorded_without_message(self):
        from scripts import send_kakao_report as report
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'config').mkdir()
            (root/'config/operations-notifications.json').write_text('{"schema_version":1,"routine_reports":"weekly"}')
            with patch.object(report, 'ROOT', root), patch.object(report, 'briefing_status', return_value=('발행 완료','')), \
                    patch.object(report, 'send') as sender, patch('sys.argv', ['report','--slot','07','--send']), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(report.main(), 0)
            sender.assert_not_called()
            receipt = next((root/'output/kakao-reports').glob('*.json'))
            self.assertEqual(json.loads(receipt.read_text())['status'], 'suppressed_healthy')

    def test_quiet_daily_error_is_queued_for_watchdog_not_discarded(self):
        from scripts import send_kakao_report as report
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'config').mkdir()
            (root/'config/operations-notifications.json').write_text('{"schema_version":1,"routine_reports":"weekly"}')
            with patch.object(report, 'ROOT', root), patch.object(report, 'briefing_status', return_value=('조회 실패','')), \
                    patch.object(report, 'send') as sender, patch('sys.argv', ['report','--slot','07','--send']), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(report.main(), 0)
            sender.assert_not_called()
            receipt = next((root/'output/kakao-reports').glob('*.json'))
            self.assertEqual(json.loads(receipt.read_text())['status'], 'queued_issue')

    def test_verified_recovery_supersedes_but_preserves_failed_result(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = '20260920T010000Z-test'
            run = root/'output/evidence-deep-article-runs'/run_id
            run.mkdir(parents=True)
            failed = {'failed': True, 'error_type': 'PipelineError', 'wordpress_write_count': 1}
            (run/'result.json').write_text(json.dumps(failed))
            publication = {'post_id': 777, 'url': 'https://huntlab.app/lesson/'}
            receipt = {'run_id': run_id, 'kst_date': '2026-09-20',
                       'wordpress_write_count': 1, 'publication': publication}
            (run/'publication.json').write_text(json.dumps(receipt))
            recovery = {**receipt, 'failed': False, 'deep_article': 'published',
                        'public_audit': {'url': publication['url'], 'http_status': 200,
                                         'title_present': True, 'evidence_links_present': True}}
            path = run/'public-audit-recovery.json'
            path.write_text(json.dumps(recovery))
            self.assertEqual(deep_status(root, '2026-09-20')[0], '발행 1건(공개 확인 완료)')
            self.assertEqual(json.loads((run/'result.json').read_text()), failed)
            for key, value in [('run_id', 'other'), ('publication', {'post_id': 999}),
                               ('public_audit', {'http_status': 200})]:
                with self.subTest(key=key):
                    path.write_text(json.dumps({**recovery, key: value}))
                    self.assertIn('실패:', deep_status(root, '2026-09-20')[0])

    def test_failure_message_explains_stage_without_raw_internal_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root/'output/evidence-deep-article-runs/20260920T010000Z-test'
            run.mkdir(parents=True)
            for writes, phrase in [('unknown','저장 결과 미확인'), (1,'저장 후 공개 내용 확인'), (0,'작성·검수 단계')]:
                (run/'result.json').write_text(json.dumps({
                    'failed':True,'wordpress_write_count':writes,'error_type':'PrivateInternalException'}))
                message = deep_status(root, '2026-09-20')[0]
                self.assertIn(phrase, message)
                self.assertNotIn('PrivateInternalException', message)

    def test_candidate_supply_failure_and_researched_empty_are_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root/'output/evidence-deep-article-runs/20260920T010000Z-test'
            run.mkdir(parents=True)
            result = run/'result.json'
            result.write_text(json.dumps({'failed': True, 'failure_stage': 'candidate_supply'}))
            self.assertEqual(deep_status(root, '2026-09-20')[0], '실패: 새 주제 조사·후보 공급 단계')
            result.write_text(json.dumps({'failed': False, 'deep_article': 'no_publishable_topic',
                                         'discovery': {'status': 'no_candidate'}}))
            self.assertIn('새 주제 조사 후 READY 0건', deep_status(root, '2026-09-20')[0])

    def test_publication_result_requires_public_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root/'output/evidence-deep-article-runs/20260920T010000Z-test'
            run.mkdir(parents=True)
            payload = {'failed': False, 'deep_article': 'published', 'wordpress_write_count': 1,
                       'publication': {'url': 'https://huntlab.app/lesson/'}}
            result = run/'result.json'
            result.write_text(json.dumps(payload))
            self.assertEqual(deep_status(root, '2026-09-20')[0], '발행 결과 확인 필요')
            payload['public_audit'] = {'url': payload['publication']['url'], 'http_status': 200,
                                     'title_present': True, 'evidence_links_present': True}
            result.write_text(json.dumps(payload))
            self.assertEqual(deep_status(root, '2026-09-20'),
                             ('발행 1건(공개 확인 완료)', 'https://huntlab.app/lesson/'))

    def test_seven_includes_today_briefing_only(self):
        message=message_for('2026-09-13','07',('발행 완료','https://huntlab.app/briefing/2026-09-13/'))
        self.assertIn('브리핑: 발행 완료',message)
        self.assertNotIn('심층글',message)

    def test_eleven_includes_in_progress_not_success(self):
        message=message_for('2026-09-13','11',('발행 완료',''),('진행 중',''))
        self.assertIn('심층글: 진행 중',message)

    def test_run_day_uses_kst_not_utc_filename(self):
        self.assertEqual(run_day('20260912T190001Z-test'),'2026-09-13')

    def test_missing_result_and_no_topic_are_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.assertIn('실행 결과 없음',deep_status(root,'2026-09-13')[0])
            run=root/'output/evidence-deep-article-runs/20260913T010000Z-test'
            run.mkdir(parents=True)
            (run/'result.json').write_text(json.dumps({'failed':False,'deep_article':'no_publishable_topic'}))
            self.assertIn('READY 0건',deep_status(root,'2026-09-13')[0])
            self.assertEqual(deep_status(root,'2026-09-13',True)[0],'진행 중')

    def test_unconfirmed_send_never_counts_as_success(self):
        with patch('scripts.send_kakao_report.subprocess.run') as run:
            run.return_value.returncode=0
            run.return_value.stdout='{"isError":true,"message":"auth required"}'
            with self.assertRaises(RuntimeError):
                send('test','mcporter')

    def test_no_topic_does_not_hide_unresolved_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            run=root/'output/evidence-deep-article-runs/20260916T010000Z-test'
            run.mkdir(parents=True)
            (run/'result.json').write_text(json.dumps({
                'failed':False,'deep_article':'no_publishable_topic',
                'reconciliation_required':True}))
            status=deep_status(root,'2026-09-16')[0]
            self.assertIn('READY 0건',status)
            self.assertIn('과거 발행 결과 대조 필요',status)
            self.assertNotIn('정상 종료',status)

    def test_links_omitted_without_corrupting_status_or_limit(self):
        message=message_for('2026-09-13','11',('조회 실패(발행 여부 미확인)','https://huntlab.app/'+'x'*200),('실행 결과 없음(누락/중단 확인 필요)',''))
        self.assertLessEqual(len(message),200)
        self.assertNotIn('https://',message)
