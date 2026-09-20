import importlib
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
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
        self.save('output/kakao-reports/2026-09-20-07.json', {'status': 'sent'})

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


if __name__ == '__main__':
    unittest.main()
