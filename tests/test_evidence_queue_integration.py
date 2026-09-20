"""Queue routing and zero-WordPress preparation contracts (mocked integration)."""
import contextlib
import io
import json
import logging
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import run_evidence_deep_article as deep
from tests import test_evidence_deep_article as fixtures


class QueueIntegrationTests(unittest.TestCase):
    def queue(self):
        module = types.ModuleType('scripts.editorial_queue')
        module.enabled = Mock(return_value=True)
        module.preparation_allowed = Mock(return_value=True)
        module.reserved_candidate_ids = Mock(return_value=set())
        module.enqueue = Mock(return_value={'status': 'queued'})
        module.release = Mock()
        return module

    def run_prepare(self, root, queue, *, candidates=None, runner=None):
        fixture = fixtures.EvidenceDeepArticleTests()
        with patch.dict('sys.modules', {'scripts.editorial_queue': queue}), \
             patch('scripts.editorial_queue', queue, create=True), \
             patch.object(deep, 'build_payload', return_value=fixture.payload([{}] if candidates is None else candidates)), \
             patch.object(deep, 'published_today', side_effect=AssertionError('preparation must not consult publish quota')):
            return deep.execute(run_id='prepare', inventory_path=fixture.inventory(root), apply=True,
                                prepare_only=True, topic_runner=runner or Mock(return_value={'status':'prepared','wordpress_write_count':0}),
                                public_auditor=Mock(side_effect=AssertionError('no public audit in preparation')),
                                repo=root, output_root=root/'runs', miner_root=root/'miner', logger=logging.getLogger('queue-test'))

    def test_preparation_ignores_publication_limit_and_enqueues_before_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue(); runner=Mock(return_value={'status':'prepared','wordpress_write_count':0})
            def enqueue(*args, **kwargs):
                self.assertFalse((root/'miner/checkpoint.json').exists())
                self.assertEqual(json.loads((root/'runs/prepare/progress.json').read_text())['wordpress_write_count'],0)
                return {'status':'queued'}
            queue.enqueue.side_effect=enqueue
            result=self.run_prepare(root,queue,runner=runner)
            self.assertEqual(result['deep_article'],'prepared')
            self.assertEqual(result['wordpress_write_count'],0)
            self.assertTrue(runner.call_args.kwargs['prepare_only'])
            self.assertTrue((root/'miner/checkpoint.json').exists())
            self.assertFalse((root/'runs/prepare/publication.json').exists())

    def test_enqueue_failure_preserves_zero_progress_and_does_not_advance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue(); queue.enqueue.side_effect=ValueError('rejected')
            with self.assertRaisesRegex(ValueError,'rejected'):
                self.run_prepare(root,queue)
            self.assertFalse((root/'miner/checkpoint.json').exists())
            self.assertEqual(json.loads((root/'runs/prepare/progress.json').read_text())['wordpress_write_count'],0)

    def test_reserved_candidate_is_not_prepared_again(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue(); queue.reserved_candidate_ids.return_value={'one'}; runner=Mock()
            result=self.run_prepare(root,queue,runner=runner)
            self.assertEqual(result['deep_article'],'no_publishable_topic')
            runner.assert_not_called(); queue.enqueue.assert_not_called()

    def test_publication_shaped_preparation_result_is_rejected_without_enqueue(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue()
            runner=Mock(return_value={'status':'prepared','wordpress_write_count':1,'post_id':999})
            with self.assertRaisesRegex(deep.PipelineError,'invalid_preparation_result'):
                self.run_prepare(root,queue,runner=runner)
            queue.enqueue.assert_not_called()
            self.assertFalse((root/'miner/checkpoint.json').exists())

    def test_discovery_still_runs_after_daily_publication_in_prepare_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue()
            with patch.object(deep,'discovery_enabled',return_value=True), \
                 patch.object(deep,'replenish_candidates',return_value={'status':'no_candidate'}) as supply:
                result=self.run_prepare(root,queue,candidates=[])
            supply.assert_called_once()
            self.assertEqual(result['wordpress_write_count'],0)

    def test_reserved_foundation_returned_by_discovery_is_normal_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue(); queue.reserved_candidate_ids.return_value={'one'}
            candidate=fixtures.EvidenceDeepArticleTests().payload([{'candidate_origin':'foundation_concept'}])[0]['candidates'][0]
            with patch.object(deep,'discovery_enabled',return_value=True), \
                 patch.object(deep,'load_foundation_candidates',return_value=([candidate],[])), \
                 patch.object(deep,'replenish_candidates',return_value={'status':'ready'}):
                result=self.run_prepare(root,queue,candidates=[])
            self.assertEqual(result['deep_article'],'no_publishable_topic')
            queue.enqueue.assert_not_called()

    def test_queue_enabled_main_only_releases_and_never_inline_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue()
            def release(**kwargs):
                (root/'runs/release').mkdir(parents=True)
                return {'failed':False,'deep_article':'no_publishable_topic','wordpress_write_count':0}
            queue.release.side_effect=release
            with patch.dict('sys.modules', {'scripts.editorial_queue':queue}), patch('scripts.editorial_queue',queue,create=True), \
                 patch.object(deep,'ROOT',root), patch.object(deep,'OUTPUT',root/'runs'), patch.object(deep,'LOCK',root/'lock'), \
                 patch.object(deep,'execute') as execution, patch.object(deep,'notify_publication'), \
                 patch('sys.argv',['deep','--apply','--run-id','release','--inventory',str(root/'inventory')]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(deep.main(),0)
            queue.release.assert_called_once(); execution.assert_not_called()

    def test_prepare_capacity_skip_no_release_no_notification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue(); queue.preparation_allowed.return_value=False
            with patch.dict('sys.modules', {'scripts.editorial_queue':queue}), patch('scripts.editorial_queue',queue,create=True), \
                 patch.object(deep,'ROOT',root), patch.object(deep,'OUTPUT',root/'runs'), patch.object(deep,'LOCK',root/'lock'), \
                 patch.object(deep,'execute') as execution, patch.object(deep,'notify_publication') as notify, \
                 patch('sys.argv',['deep','--apply','--prepare-only','--run-id','capacity','--inventory',str(root/'inventory')]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(deep.main(),0)
            queue.release.assert_not_called(); execution.assert_not_called(); notify.assert_not_called()
            self.assertEqual(json.loads((root/'runs/capacity/result.json').read_text())['wordpress_write_count'],0)

    def test_release_failure_does_not_fall_back_to_inline_pipeline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue(); queue.release.side_effect=ValueError('source_changed')
            with patch.dict('sys.modules', {'scripts.editorial_queue':queue}), patch('scripts.editorial_queue',queue,create=True), \
                 patch.object(deep,'ROOT',root), patch.object(deep,'OUTPUT',root/'runs'), patch.object(deep,'LOCK',root/'lock'), \
                 patch.object(deep,'execute') as execution, patch.object(deep,'notify_publication') as notify, \
                 patch('sys.argv',['deep','--apply','--run-id','rejected','--inventory',str(root/'inventory')]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(deep.main(),1)
            execution.assert_not_called(); notify.assert_not_called()

    def test_preparation_source_failure_records_safe_cause(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); queue=self.queue()
            queue.preparation_allowed.return_value=True
            def fail(**kwargs):
                (root/'runs/source-failure').mkdir(parents=True)
                raise deep.SourceCheckError('source_recheck_http_error',
                                            'https://example.test/doc?token=secret', status=403)
            with patch.dict('sys.modules', {'scripts.editorial_queue':queue}), patch('scripts.editorial_queue',queue,create=True), \
                 patch.object(deep,'ROOT',root), patch.object(deep,'OUTPUT',root/'runs'), patch.object(deep,'LOCK',root/'lock'), \
                 patch.object(deep,'execute',side_effect=fail), patch.object(deep,'notify_publication') as notify, \
                 patch('sys.argv',['deep','--apply','--prepare-only','--run-id','source-failure','--inventory',str(root/'inventory')]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(deep.main(),1)
            result=json.loads((root/'runs/source-failure/result.json').read_text())
            self.assertEqual(result['http_status'],403)
            self.assertEqual(result['failure_stage'],'source_recheck')
            self.assertEqual(result['wordpress_write_count'],0)
            self.assertNotIn('secret',json.dumps(result))
            notify.assert_not_called()


if __name__ == '__main__':
    unittest.main()
