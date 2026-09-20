import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.publication_notification import notify_publication


class PublicationNotificationTests(unittest.TestCase):
    def test_deep_service_uses_approved_report_mcp_installation(self):
        root = Path(__file__).resolve().parents[1]
        deep = (root / 'deploy/huntlab-evidence-deep-article.service').read_text()
        report = (root / 'deploy/huntlab-kakao-report.service').read_text()
        mcp = '/home/ubuntu/.local/share/huntlab-mcp/node_modules/.bin'
        for unit in (deep, report):
            self.assertIn(f'Environment=PATH={mcp}:', unit)
            self.assertIn(f'Environment=MCPORTER_BIN={mcp}/mcporter', unit)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.sender = Mock()
        self.result = {
            'run_id': '20260917T010000Z-example', 'failed': False,
            'deep_article': 'published', 'wordpress_write_count': 1,
            'publication': {'post_id': 800, 'url': 'https://huntlab.app/robotics/',
                            'title': '피지컬 AI 첫 실습'},
            'public_audit': {'url': 'https://huntlab.app/robotics/',
                             'http_status': 200, 'title_present': True,
                             'evidence_links_present': True},
        }

    def notify(self, **kwargs):
        return notify_publication(self.result, root=self.root, sender=self.sender, **kwargs)

    def receipt(self):
        return json.loads((self.root / 'output/kakao-publications/post-800.json').read_text())

    def test_verified_publication_sends_only_once_even_across_run_ids(self):
        self.assertEqual(self.notify()['status'], 'sent')
        self.result['run_id'] = 'different-run'
        self.assertEqual(self.notify()['status'], 'already_sent')
        self.sender.assert_called_once()
        self.assertIn('https://huntlab.app/robotics/', self.sender.call_args.args[0])
        self.assertEqual(self.receipt()['attempt'], 1)

    def test_actual_pipeline_topic_field_becomes_notification_title(self):
        # read_publish_result returns topic, not title; preserve that live contract.
        publication = self.result['publication']
        publication['topic'] = publication.pop('title')
        publication.update(run_id=self.result['run_id'], topic_id='robotics', image_count=1)
        self.assertEqual(self.notify()['status'], 'sent')
        message = self.sender.call_args.args[0]
        self.assertIn(publication['topic'], message)
        self.assertIn(publication['url'], message)

    def test_weekly_routine_policy_suppresses_success_but_preserves_receipt(self):
        config = self.root/'config/operations-notifications.json'
        config.parent.mkdir()
        config.write_text('{"schema_version":1,"routine_reports":"weekly"}')
        self.assertEqual(self.notify()['status'], 'suppressed_healthy')
        self.assertEqual(self.notify()['status'], 'suppressed_healthy')
        self.assertEqual(self.receipt()['post_id'], 800)
        self.sender.assert_not_called()

    def test_quiet_policy_never_erases_uncertain_delivery(self):
        self.sender.side_effect = RuntimeError()
        self.notify()
        before = self.receipt()
        config = self.root/'config/operations-notifications.json'
        config.parent.mkdir()
        config.write_text('{"schema_version":1,"routine_reports":"weekly"}')
        self.assertEqual(self.notify()['status'], 'delivery_unconfirmed')
        self.assertEqual(self.receipt(), before)

    def test_explicit_title_takes_precedence_over_topic(self):
        self.result['publication']['topic'] = 'Older planner topic'
        self.assertEqual(self.notify()['status'], 'sent')
        self.assertIn(self.result['publication']['title'], self.sender.call_args.args[0])
        self.assertNotIn('Older planner topic', self.sender.call_args.args[0])

    def test_unverified_states_never_send(self):
        changes = [
            {'failed': True}, {'deep_article': 'no_publishable_topic'},
            {'deep_article': 'ready_not_published'}, {'wordpress_write_count': 0},
            {'public_audit': {}}, {'publication': {'post_id': True}},
        ]
        original = copy.deepcopy(self.result)
        for change in changes:
            self.result = {**original, **change}
            self.assertEqual(self.notify()['status'], 'not_eligible')
        self.sender.assert_not_called()

    def test_each_public_audit_gate_required(self):
        original = copy.deepcopy(self.result['public_audit'])
        for key, value in [('url', 'https://other.test/'), ('http_status', 404),
                           ('title_present', False), ('evidence_links_present', False)]:
            self.result['public_audit'] = {**original, key: value}
            self.assertEqual(self.notify()['status'], 'not_eligible')
        self.sender.assert_not_called()

    def test_external_or_credential_or_query_links_rejected(self):
        for url in ['https://huntlab.app.evil.test/post/', 'https://user@huntlab.app/post/',
                    'http://huntlab.app/post/', 'https://huntlab.app/post/?token=secret']:
            self.result['publication']['url'] = url
            self.result['public_audit']['url'] = url
            self.assertEqual(self.notify()['status'], 'not_eligible')
        self.sender.assert_not_called()

    def test_ambiguous_delivery_does_not_change_publication_or_auto_retry(self):
        original = copy.deepcopy(self.result)
        self.sender.side_effect = RuntimeError('secret oauth token')
        self.assertEqual(self.notify()['status'], 'delivery_unconfirmed')
        self.assertEqual(self.notify()['status'], 'delivery_unconfirmed')
        self.sender.assert_called_once()
        self.assertEqual(self.result, original)
        self.assertNotIn('secret', json.dumps(self.receipt()))
        self.sender.side_effect = None
        self.assertEqual(self.notify(retry_unconfirmed=True)['status'], 'sent')
        self.assertEqual(self.receipt()['attempt'], 2)

    def test_missing_executable_can_retry_without_republishing(self):
        self.sender.side_effect = FileNotFoundError()
        self.assertEqual(self.notify()['status'], 'not_sent')
        self.sender.side_effect = None
        self.assertEqual(self.notify()['status'], 'sent')

    def test_preflight_runtime_failure_is_definite_not_sent(self):
        from scripts.send_kakao_report import KakaoNotSent
        self.sender.side_effect = KakaoNotSent('runtime failed before call')
        self.assertEqual(self.notify()['status'], 'not_sent')
        self.sender.side_effect = None
        self.assertEqual(self.notify()['status'], 'sent')

    def test_process_interruption_attempting_receipt_blocks_duplicate(self):
        self.sender.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.notify()
        self.assertEqual(self.receipt()['status'], 'attempting')
        self.sender.side_effect = None
        self.assertEqual(self.notify()['status'], 'delivery_unconfirmed')
        self.sender.assert_called_once()

    def test_long_title_and_encoded_slug_fit_complete_link(self):
        self.result['publication']['title'] = '아주 긴 제목 ' * 100
        url = 'https://huntlab.app/' + '%ED%95%9C' * 100 + '/'
        self.result['publication']['url'] = url
        self.result['public_audit']['url'] = url
        self.assertEqual(self.notify()['status'], 'sent')
        message = self.sender.call_args.args[0]
        self.assertLessEqual(len(message), 200)
        self.assertTrue(message.endswith('https://huntlab.app/?p=800'))

    def test_disk_error_is_nonfatal_and_prevents_send(self):
        with patch('scripts.publication_notification._save', side_effect=OSError()):
            self.assertEqual(self.notify()['status'], 'notification_error')
        self.sender.assert_not_called()

    def test_receipt_persistence_failure_after_send_blocks_duplicate(self):
        from scripts.publication_notification import _save
        counter = 0
        def failing_save(path, payload):
            nonlocal counter
            counter += 1
            if counter == 2:
                raise OSError()
            _save(path, payload)
        with patch('scripts.publication_notification._save', side_effect=failing_save):
            self.assertEqual(self.notify()['status'], 'notification_error')
        self.assertEqual(self.notify()['status'], 'delivery_unconfirmed')
        self.sender.assert_called_once()


if __name__ == '__main__':
    unittest.main()
