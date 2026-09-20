import importlib
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
import contextlib
import io
from zoneinfo import ZoneInfo


class OperationsWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 9, 20, 9, 0, tzinfo=ZoneInfo('Asia/Seoul'))
        self.run_id = '20260919T225542Z-example'
        self.directory = self.root/'output/evidence-deep-article-runs'/self.run_id
        self.directory.mkdir(parents=True)
        self.publication = {'post_id': 777, 'url': 'https://huntlab.app/lesson/'}
        self.verified = {'run_id': self.run_id, 'kst_date': '2026-09-20',
                         'failed': False, 'deep_article': 'published', 'wordpress_write_count': 1,
                         'publication': self.publication,
                         'public_audit': {'url': self.publication['url'], 'http_status': 200,
                                          'title_present': True, 'evidence_links_present': True}}
        self.recover = Mock(return_value=self.verified)
        self.notify = Mock(return_value={'status': 'sent'})
        self.sender = Mock()
        self.health = Mock(return_value=True)
        self.active = Mock(return_value=False)
        self.confirm = Mock(return_value=True)
        self.save('output/kakao-reports/2026-09-20-07.json', {'status': 'sent'})
        self.save_collection('2026-09-20T04:00:00+09:00')

    def save_collection(self, checked_at):
        self.save('output/search-signals/editorial-sources.json', {
            'provider': 'hunt_news_editorial_sources',
            'contract_version': 'editorial-source-cache.v1',
            'checked_at': checked_at, 'rows': [{'url':'https://example.org/news'}]})

    def test_stale_collector_is_detected_without_publishing_or_retrying_collection(self):
        self.save_collection('2026-09-05T04:00:00+09:00')
        self.save(str((self.directory/'result.json').relative_to(self.root)),
                  {'failed': False, 'deep_article': 'no_publishable_topic', 'wordpress_write_count': 0})
        for _ in range(3):
            result = self.execute()
        self.assertIn({'key':'editorial_collection','reason':'news_collection_stale'}, result['issues'])
        self.assertEqual(result['checks']['editorial_collection']['status'], 'stale')
        self.assertEqual(result['wordpress_write_count'], 0)
        self.assertIn('뉴스 수집 갱신 지연', self.sender.call_args.args[0])
        self.recover.assert_not_called()
        self.notify.assert_not_called()

    def test_daily_collection_deadline_and_invalid_records(self):
        from scripts.operations_watchdog import editorial_collection_status
        self.save_collection('2026-09-19T04:00:00+09:00')
        self.assertEqual(editorial_collection_status(self.root, self.now.replace(hour=4, minute=29))['status'], 'fresh')
        self.assertEqual(editorial_collection_status(self.root, self.now.replace(hour=4, minute=30))['status'], 'stale')
        self.save_collection('2026-09-20T04:00:00+09:00')
        self.assertEqual(editorial_collection_status(self.root, self.now.replace(hour=23))['status'], 'fresh')
        for stamp in ('bad-time','2026-09-20T04:00:00','2026-09-21T04:00:00+09:00'):
            self.save_collection(stamp)
            self.assertEqual(editorial_collection_status(self.root, self.now)['status'], 'invalid')

    def test_collection_recovery_clears_observation_without_false_success(self):
        self.save_collection('2026-09-05T04:00:00+09:00')
        self.execute()
        self.save_collection('2026-09-20T04:00:00+09:00')
        result = self.execute()
        self.assertFalse(any(i['key']=='editorial_collection' for i in result['issues']))
        self.assertEqual(result['recovered'], [])
        self.sender.assert_not_called()

    def save(self, path, data):
        target = self.root/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data))

    def failed_publication(self):
        self.save(str((self.directory/'result.json').relative_to(self.root)),
                  {'failed': True, 'wordpress_write_count': 1, 'error_type': 'PipelineError'})
        self.save(str((self.directory/'publication.json').relative_to(self.root)),
                  {'run_id': self.run_id, 'kst_date': '2026-09-20',
                   'wordpress_write_count': 1, 'publication': self.publication})

    def execute(self, apply=True):
        module = importlib.import_module('scripts.operations_watchdog')
        with patch.object(module, 'confirm_publication', self.confirm, create=True):
            return module.run_watchdog(self.root, self.now, apply=apply, recover=self.recover,
                                      notify=self.notify, sender=self.sender,
                                      health=self.health, active=self.active)

    def test_dry_run_does_not_recover_notify_or_persist(self):
        self.failed_publication()
        result = self.execute(False)
        self.assertTrue(result['dry_run'])
        self.recover.assert_not_called()
        self.notify.assert_not_called()
        self.sender.assert_not_called()
        self.assertFalse((self.root/'output/operations-watchdog').exists())

    def test_confirmed_publication_recovers_readonly_then_notifies(self):
        self.failed_publication()
        before = (self.directory/'result.json').read_bytes()
        result = self.execute()
        self.recover.assert_called_once_with(self.run_id)
        self.notify.assert_called_once_with(self.verified)
        self.assertEqual((self.directory/'result.json').read_bytes(), before)
        self.assertIn(self.run_id, result['recovered'])

    def test_unknown_publication_never_retries_publisher(self):
        self.save(str((self.directory/'result.json').relative_to(self.root)),
                  {'failed': True, 'wordpress_write_count': 'unknown'})
        result = self.execute()
        self.assertTrue(any(x['reason'] == 'publication_unknown' for x in result['issues']))
        self.recover.assert_not_called()
        self.notify.assert_not_called()

    def test_no_topic_is_not_failure(self):
        self.save(str((self.directory/'result.json').relative_to(self.root)),
                  {'failed': False, 'deep_article': 'no_publishable_topic', 'wordpress_write_count': 0})
        self.assertEqual(self.execute()['issues'], [])
        self.recover.assert_not_called()
        self.sender.assert_not_called()

    def test_audit_retries_are_bounded_across_executions(self):
        self.failed_publication()
        self.recover.side_effect = RuntimeError('private secret must not be logged')
        for _ in range(5):
            result = self.execute()
        self.assertEqual(self.recover.call_count, 3)
        self.assertNotIn('private secret', json.dumps(result))
        self.assertLessEqual(self.sender.call_count, 2)

    def test_uncertain_notification_is_never_retried(self):
        self.save(str((self.directory/'result.json').relative_to(self.root)), self.verified)
        self.save('output/kakao-publications/post-777.json', {'status': 'delivery_unconfirmed'})
        self.assertTrue(any(x['reason'] == 'notification_unknown' for x in self.execute()['issues']))
        self.notify.assert_not_called()

    def test_missing_notification_can_be_sent_once(self):
        self.save(str((self.directory/'result.json').relative_to(self.root)), self.verified)
        self.execute()
        self.notify.assert_called_once()

    def test_sent_notification_is_not_repeated(self):
        self.save(str((self.directory/'result.json').relative_to(self.root)), self.verified)
        self.save('output/kakao-publications/post-777.json', {'status': 'sent'})
        self.assertEqual(self.execute()['issues'], [])
        self.notify.assert_not_called()

    def test_not_sent_retry_budget_and_uncertain_incident_alert(self):
        self.save(str((self.directory/'result.json').relative_to(self.root)), self.verified)
        self.save('output/kakao-publications/post-777.json', {'status': 'not_sent'})
        self.notify.return_value = {'status': 'not_sent'}
        self.sender.side_effect = RuntimeError('secret')
        for _ in range(5):
            self.execute()
        self.assertEqual(self.notify.call_count, 3)
        self.assertEqual(self.sender.call_count, 1)

    def test_corrupt_record_is_reported_not_hidden(self):
        (self.directory/'result.json').write_text('{invalid')
        self.assertTrue(any(x['reason'] == 'record_invalid' for x in self.execute()['issues']))
        self.recover.assert_not_called()

    def test_active_pipeline_defers_recovery(self):
        self.failed_publication()
        self.active.return_value = True
        self.execute()
        self.recover.assert_not_called()

    def test_external_url_cannot_become_recovery_fetch(self):
        self.publication['url'] = 'https://evil.test/path'
        self.failed_publication()
        self.assertTrue(self.execute()['issues'])
        self.recover.assert_not_called()

    def test_old_records_are_not_replayed(self):
        old = self.root/'output/evidence-deep-article-runs/20260801T010000Z-old'
        old.mkdir()
        (old/'result.json').write_text('{invalid')
        self.assertEqual(self.execute()['issues'], [])

    def test_missing_schedules_and_website_failure_are_reported(self):
        self.directory.rmdir()
        self.now = self.now.replace(hour=22)
        self.health.side_effect = TimeoutError()
        result = self.execute()
        reasons = {x['reason'] for x in result['issues']}
        self.assertTrue({'deep_run_missing', 'weekly_run_missing', 'report_missing', 'public_site_unreachable'} <= reasons)

    def test_bad_recovery_is_not_used_for_notification(self):
        self.failed_publication()
        self.recover.return_value = {**self.verified, 'run_id': 'different'}
        self.execute()
        self.notify.assert_not_called()

    def test_live_process_without_result_is_not_a_failure(self):
        self.active.return_value = True
        self.assertEqual(self.execute()['issues'], [])

    def test_dry_run_record_does_not_hide_missing_scheduled_execution(self):
        self.now = self.now.replace(hour=13)
        self.save(str((self.directory/'result.json').relative_to(self.root)),
                  {'failed': False, 'deep_article': 'ready_not_published'})
        self.assertTrue(any(x['reason'] == 'deep_run_missing' for x in self.execute()['issues']))

    def test_persisted_recovery_is_used_without_repeat_audit(self):
        self.failed_publication()
        self.save(str((self.directory/'public-audit-recovery.json').relative_to(self.root)), self.verified)
        self.execute()
        self.recover.assert_not_called()
        self.notify.assert_called_once()

    def test_cli_locks_release_on_success_busy_and_failure(self):
        module = importlib.import_module('scripts.operations_watchdog')
        from scripts.run_daily_pipeline import PipelineError
        for error, expected in ((None, 0), (PipelineError('busy'), 0), (ValueError('bad'), 1)):
            with self.subTest(error=error), patch.object(module, 'PipelineLock') as factory, \
                    patch.object(module, 'run_watchdog', return_value={}, side_effect=error), \
                    patch('sys.argv', ['watchdog', '--apply']), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), expected)
                self.assertEqual(factory.return_value.release.call_count, 2)

    def test_system_service_and_public_probe(self):
        module = importlib.import_module('scripts.operations_watchdog')
        with patch.object(module.subprocess, 'run') as run:
            run.return_value.stdout = 'activating\n'
            self.assertTrue(module.service_active(module.DEEP))
            run.return_value.stdout = 'inactive\n'
            self.assertFalse(module.service_active(module.DEEP))
        with patch.object(module, 'build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 200
            self.assertTrue(module.site_healthy())

    def test_weekly_failure_and_corrupt_report_are_reported(self):
        self.now = self.now.replace(hour=22)
        self.save('output/weekly-editorial/2026-09-20/result.json',
                  {'failed': True, 'metrics_status': 'INCOMPLETE'})
        self.save('output/kakao-reports/2026-09-20-11.json', {'status': 'delivery_unconfirmed'})
        reasons = {x['reason'] for x in self.execute()['issues']}
        self.assertTrue({'weekly_needs_repair', 'analytics_incomplete', 'report_delivery_unknown'} <= reasons)

    def test_naive_time_rejected_and_invalid_recovery_not_trusted(self):
        self.now = self.now.replace(tzinfo=None)
        with self.assertRaises(ValueError):
            self.execute()
        self.now = self.now.replace(tzinfo=ZoneInfo('Asia/Seoul'))
        self.failed_publication()
        self.save(str((self.directory/'public-audit-recovery.json').relative_to(self.root)), {'failed': False})
        self.assertTrue(any(x['reason'] == 'record_invalid' for x in self.execute()['issues']))
        self.notify.assert_not_called()

    def test_transient_incident_gets_three_checks_before_interrupting(self):
        self.health.return_value = False
        self.execute()
        self.execute()
        self.sender.assert_not_called()
        self.execute()
        self.sender.assert_called_once()
        self.assertIn('조치 필요', self.sender.call_args.args[0])

    def test_persistent_same_incident_not_repeated_next_day(self):
        self.failed_publication()
        self.recover.side_effect = RuntimeError()
        for _ in range(3):
            self.execute()
        self.assertEqual(self.sender.call_count, 1)
        self.now = self.now.replace(day=21)
        self.save('output/kakao-reports/2026-09-21-07.json', {'status':'sent'})
        self.execute()
        self.assertEqual(self.sender.call_count, 1)

    def test_suppressed_healthy_daily_receipt_is_not_missing_delivery(self):
        self.save('output/kakao-reports/2026-09-20-07.json', {'status':'suppressed_healthy'})
        self.assertEqual(self.execute()['issues'], [])

    def test_retired_individual_notification_does_not_interrupt_weekly_mode(self):
        self.save('config/operations-notifications.json', {'schema_version':1,'routine_reports':'weekly'})
        self.save(str((self.directory/'result.json').relative_to(self.root)), self.verified)
        self.save('output/kakao-publications/post-777.json', {'status':'delivery_unconfirmed'})
        for _ in range(4):
            result = self.execute()
        self.assertEqual(result['issues'][0]['reason'], 'notification_unknown')
        self.assertEqual(result['action_required'], [])
        self.sender.assert_not_called()
        self.notify.assert_not_called()

    def test_transient_daily_check_is_rechecked_without_touching_original(self):
        from scripts import operations_watchdog as watchdog
        relative = 'output/kakao-reports/2026-09-20-07.json'
        self.save(relative, {'status':'queued_issue','day':'2026-09-20','slot':'07'})
        original = (self.root/relative).read_bytes()
        with patch.object(watchdog, 'confirm_scheduled_report', return_value=True, create=True) as check:
            self.assertEqual(self.execute()['issues'], [])
            check.assert_called_once()
        self.assertEqual((self.root/relative).read_bytes(), original)
        self.sender.assert_not_called()

    def test_no_historical_notification_backfill(self):
        old_id = '20260915T183332Z-older'
        old = self.root/'output/evidence-deep-article-runs'/old_id
        old.mkdir()
        (old/'result.json').write_text(json.dumps({**self.verified, 'run_id': old_id, 'kst_date': '2026-09-16'}))
        self.assertEqual(self.execute()['issues'], [])
        self.notify.assert_not_called()

    def test_notification_requires_fresh_public_confirmation(self):
        self.save(str((self.directory/'result.json').relative_to(self.root)), self.verified)
        self.confirm.return_value = False
        self.assertTrue(self.execute()['issues'])
        self.notify.assert_not_called()

    def test_fresh_confirmation_is_bound_to_saved_publication(self):
        module = importlib.import_module('scripts.operations_watchdog')
        path = str((self.directory/'publication.json').relative_to(self.root))
        self.save(path, {'publication': self.publication, 'candidate': {}})
        with patch.object(module, 'audit_public', return_value=self.verified['public_audit']) as audit:
            self.assertTrue(module.confirm_publication(self.directory, self.verified))
            audit.assert_called_once_with(self.publication, {})
            self.save(path, {'publication': {'post_id': 999}, 'candidate': {}})
            self.assertFalse(module.confirm_publication(self.directory, self.verified))
            self.assertEqual(audit.call_count, 1)


if __name__ == '__main__':
    unittest.main()
