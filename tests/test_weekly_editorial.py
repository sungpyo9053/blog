import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import run_weekly_editorial as weekly


class WeeklyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'config').mkdir()
        (self.root / 'config/weekly-editorial.json').write_text(json.dumps({'schema_version': 1, 'anchor_sunday': '2026-09-20'}))
        self.now = datetime(2026, 9, 20, 20, 0, tzinfo=weekly.KST)
        self.client = Mock()
        self.client.request.return_value = []
        self.snapshot = Mock(return_value={'metadata': {'complete': True}, 'posts': []})
        self.metrics = Mock(return_value={'sources': {'search_console': {'status': 'INCOMPLETE'}, 'ga4': {'status': 'INCOMPLETE'}}})
        self.agent = Mock(return_value={'summary': '검토 완료; 데이터 부족', 'proposals': [{'title': '좌표계', 'reader_question': '좌표란?', 'reason': '기초 연결'}], 'action': None})
        self.updater = Mock(return_value={'status': 'updated', 'wp_write_count': 1, 'post_id': 10})
        self.sender = Mock()

    def run_week(self, **kwargs):
        options = dict(root=self.root, now=self.now, client=self.client, snapshot_builder=self.snapshot,
                       metrics_collector=self.metrics, agent=self.agent, updater=self.updater, sender=self.sender)
        options.update(kwargs)
        return weekly.run(**options)

    def test_empty_inventory_still_plans_without_writes(self):
        result = self.run_week()
        self.assertFalse(result['failed'])
        self.assertEqual(result['metrics_status'], 'INCOMPLETE')
        self.assertEqual(result['feedback'], 'NOT_CONNECTED')
        self.agent.assert_called_once()
        self.updater.assert_not_called()

    def test_schedule_rejects_weekday_and_wrong_hour(self):
        for now in [datetime(2026, 9, 21, 20, tzinfo=weekly.KST), datetime(2026, 9, 20, 19, tzinfo=weekly.KST)]:
            self.assertEqual(self.run_week(apply=True, now=now)['reason'], 'outside_scheduled_window')
        self.agent.assert_not_called()

    def test_week_and_four_week_boundaries_cross_year(self):
        config = {'schema_version': 1, 'anchor_sunday': '2026-09-20'}
        self.assertEqual(weekly.week_info(self.now, config), ('2026-09-20', False))
        self.assertEqual(weekly.week_info(datetime(2026, 10, 18, tzinfo=weekly.KST), config), ('2026-10-18', True))
        self.assertEqual(weekly.week_info(datetime(2027, 1, 3, tzinfo=weekly.KST), config), ('2027-01-03', False))
        self.assertEqual(weekly.week_info(datetime(2027, 1, 10, tzinfo=weekly.KST), config), ('2027-01-10', True))

    def test_dryrun_does_not_consume_week(self):
        dry = self.run_week()
        applied = self.run_week(apply=True)
        self.assertNotEqual(dry['run_dir'], applied['run_dir'])
        self.assertEqual(self.agent.call_count, 2)

    def test_completed_apply_deduplicates(self):
        first = self.run_week(apply=True)
        second = self.run_week(apply=True)
        self.assertEqual(first, second)
        self.agent.assert_called_once()

    def test_unfinished_prior_apply_requires_reconciliation(self):
        directory = self.root / 'output/weekly-editorial/2026-09-20'
        weekly.save(directory / 'started.json', {})
        self.assertEqual(self.run_week(apply=True)['reason'], 'prior_run_requires_reconciliation')
        self.agent.assert_not_called()

    def test_agent_failure_recorded_safely_and_not_retried(self):
        self.agent.side_effect = RuntimeError('password=supersecret')
        result = self.run_week(apply=True, notify=True)
        self.assertTrue(result['failed'])
        self.assertNotIn('supersecret', json.dumps(result))
        self.assertEqual(result['notification']['status'], 'sent')
        self.run_week(apply=True, notify=True)
        self.agent.assert_called_once()
        self.sender.assert_called_once()

    def test_notification_unclear_not_retried(self):
        self.sender.side_effect = TimeoutError('secret')
        result = self.run_week(apply=True, notify=True)
        self.assertEqual(result['notification']['status'], 'unconfirmed')
        self.run_week(apply=True, notify=True)
        self.sender.assert_called_once()

    def test_assessment_deferred_if_one_source_missing(self):
        self.metrics.return_value['sources']['ga4'] = {'status': 'COMPLETE', 'comparison_sufficient': True}
        result = self.run_week(now=datetime(2026, 10, 18, 20, tzinfo=weekly.KST))
        self.assertEqual(result['assessment'], 'DEFERRED_INSUFFICIENT_DATA')

    def test_assessment_adequacy_requires_both_sources(self):
        self.metrics.return_value['sources'] = {key: {'status': 'COMPLETE', 'comparison_sufficient': True} for key in ('search_console', 'ga4')}
        result = self.run_week(now=datetime(2026, 10, 18, 20, tzinfo=weekly.KST))
        self.assertEqual(result['assessment'], 'DUE_SUFFICIENT_FOR_REVIEW')

    def prepare_action(self):
        raw = '<p>설명을 더 쉽게 읽을 수 있도록 표현을 정리하는 예시입니다.</p>'
        target = {'post_id': 10, 'title': '관측', 'slug': 'observation', 'content': raw}
        action = dict(post_id=10, before_sha256=weekly.sha256(raw), old_paragraph=raw,
                      new_paragraph='<p>관측 개념을 쉽게 읽을 수 있도록 표현을 정리하는 예시입니다.</p>', reason='명확화', evidence_refs=['본문'])
        self.agent.side_effect = [{'summary': '명확화', 'proposals': [], 'action': action}, {'verdict': 'APPROVED', 'action_sha256': 'model-hash'}]
        return target

    def test_one_action_independent_review_then_fresh_inventory(self):
        target = self.prepare_action()
        with patch.object(weekly, 'eligible_posts', return_value=[target]):
            result = self.run_week(apply=True)
        self.assertEqual(result['wp_write_count'], 1)
        self.assertEqual(self.agent.call_count, 2)
        self.assertEqual(self.snapshot.call_count, 2)
        self.updater.assert_called_once()
        kwargs = self.updater.call_args.kwargs
        self.assertTrue(kwargs['apply'])
        self.assertNotEqual(kwargs['review']['writer_id'], kwargs['review']['reviewer_id'])
        self.assertEqual(kwargs['review']['action_sha256'], 'model-hash')

    def test_review_hold_never_calls_updater(self):
        target = self.prepare_action()
        plan = self.agent.side_effect
        # Mock converts a list side_effect to an iterator.
        first = next(plan)
        self.agent.side_effect = [first, {'verdict': 'HOLD', 'reason': '근거 부족'}]
        with patch.object(weekly, 'eligible_posts', return_value=[target]):
            result = self.run_week(apply=True)
        self.assertEqual(result['update']['status'], 'review_hold')
        self.updater.assert_not_called()

    def test_dryrun_passes_apply_false_to_updater(self):
        target = self.prepare_action()
        self.updater.return_value = {'status': 'dry_run', 'wp_write_count': 0}
        with patch.object(weekly, 'eligible_posts', return_value=[target]):
            self.run_week()
        self.assertFalse(self.updater.call_args.kwargs['apply'])

    def test_rejects_multiple_actions_and_unknown_fields(self):
        for plan in ({'summary': '', 'proposals': [], 'action': []}, {'summary': '', 'proposals': [], 'action': None, 'extra': True}):
            with self.assertRaises(ValueError):
                weekly.validate_plan(plan)

    def test_parse_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):
            weekly.parse_json('{"action":null,"action":{}}')

    def test_private_artifacts(self):
        result = self.run_week()
        directory = Path(result['run_dir'])
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        for path in directory.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_model_process_is_input_only_and_no_credentials_inherited(self):
        for name in ('agents/weekly-editorial-agent.md', 'guides/physical-ai-quality.md', 'guides/weekly-editorial-operations.md'):
            path = self.root / name
            path.parent.mkdir(exist_ok=True)
            path.write_text('Policy')
        def process(command, **kwargs):
            self.assertIn('--ignore-rules', command)
            self.assertIn('--ignore-user-config', command)
            self.assertIn('features.shell_tool=false', command)
            self.assertIn('web_search="disabled"', command)
            self.assertNotIn('WORDPRESS_APP_PASSWORD', kwargs['env'])
            self.assertNotIn('secret-content', kwargs['input'])
            self.assertIn('untrusted data', kwargs['input'])
            Path(command[command.index('--output-last-message') + 1]).write_text('{"summary":"safe"}')
            return Mock(returncode=0)
        with patch.dict('os.environ', {'WORDPRESS_APP_PASSWORD': 'secret-content'}), patch.object(weekly.subprocess, 'run', side_effect=process):
            answer = weekly.invoke_agent(self.root, 'agent', {'value': 'secret-content'}, self.root / 'private')
        self.assertEqual(answer, {'summary': 'safe'})

    def test_published_archive_and_drafts_are_not_targets(self):
        inventory = {'posts': [{'post_id': 10, 'status': 'publish'}, {'post_id': 11, 'status': 'draft'}]}
        def request(method, route):
            if route.startswith('categories?'):
                return []
            self.assertEqual(route, 'posts/10?context=edit')
            return {'id': 10, 'status': 'publish', 'categories': [123]}
        self.client.request.side_effect = request
        self.assertEqual(weekly.eligible_posts(self.client, inventory), [])

    def test_discovery_inventory_omits_full_bodies(self):
        result = weekly.inventory_summary({'metadata': {'complete': True}, 'posts': [
            {'post_id': 1, 'status': 'draft', 'title': 'title', 'slug': 'slug', 'content': 'PRIVATE BODY', 'excerpt': 'x' * 500}]})
        self.assertNotIn('PRIVATE BODY', json.dumps(result))
        self.assertEqual(len(result['posts'][0]['excerpt']), 300)


if __name__ == '__main__':
    unittest.main()
