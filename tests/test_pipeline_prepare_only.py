import hashlib
import json
import logging
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from scripts import run_daily_pipeline as p


class PrepareOnly(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name)/'run'/'topic'
        self.directory.mkdir(parents=True)
        self.context=p.TopicContext('title','run','topic',self.directory)
        for name in ['publish.md','review.md','final.md','final.html','research.md','planner-context.json','source-baseline.json','queue-inventory.json','images/thumbnail.png','images/body.png']:
            path=self.directory/name; path.parent.mkdir(exist_ok=True); path.write_text(name)
        self.digest=hashlib.sha256((self.directory/'publish.md').read_bytes()).hexdigest()
        self.contract=patch.object(p,'validate_publish_contract',return_value=self.digest)
        self.contract.start(); self.addCleanup(self.contract.stop)

    def freeze(self):
        return p.persist_prepared_result(self.context,self.digest)

    def test_prepared_receipt_and_manifest(self):
        result=self.freeze()
        self.assertEqual(result['status'],'prepared')
        self.assertNotIn('post_id',result)
        self.assertNotIn('url',result)
        self.assertEqual(result['context']['directory'],str(self.directory))
        self.assertIn('images/body.png',result['artifacts'])
        self.assertEqual(p.validate_prepared_artifacts(self.context),result)

    def test_all_frozen_files_reject_change(self):
        result=self.freeze()
        for name in result['artifacts']:
            path=self.directory/name; before=path.read_bytes();path.write_bytes(before+b'changed')
            with self.subTest(name=name),self.assertRaises(p.PipelineError):
                p.validate_prepared_artifacts(self.context)
            path.write_bytes(before)

    def test_path_escape_rejected(self):
        result=self.freeze();result['artifacts']['../escape']='a'*64
        (self.directory/'prepared-result.json').write_text(json.dumps(result))
        with self.assertRaises(p.PipelineError):p.validate_prepared_artifacts(self.context)

    def test_symlink_rejected(self):
        target=self.directory/'images/body.png';target.unlink();target.symlink_to(self.directory/'publish.md')
        with self.assertRaises(p.PipelineError):self.freeze()

    def test_prepare_pipeline_stops_before_publisher(self):
        with (
            patch('scripts.editorial_epoch.reject_legacy_run'),
            patch('scripts.editorial_epoch.reject_retired_publication'),
            patch.object(p,'has_successful_publish',return_value=False),
            patch.object(p,'write_planner_context'),patch.object(p,'write_recent_style_context'),
            patch.object(p,'topic_stages',return_value=[p.Stage('Reviewer Agent',None,''),p.Stage('Publisher Agent',None,'')]),
            patch.object(p,'read_review_decision',return_value='APPROVED'),
            patch.object(p,'validate_stage_artifacts'),
            patch.object(p,'run_review_repair_cycle') as repair,
            patch.object(p,'load_document',return_value=Mock(metadata={})),
            patch.object(p,'run_stage') as stage,
            patch.object(p,'read_publish_result') as publication,
        ):
            result=p.run_topic_pipeline('codex',self.context,{},logging.getLogger('test'),timeout_seconds=1,resume=True,publish_lock=threading.Lock(),humanize_lock=threading.Lock(),prepare_only=True)
        self.assertEqual(result['status'],'prepared');repair.assert_not_called()
        self.assertEqual([c.args[1].name for c in stage.call_args_list],['Reviewer Agent'])
        publication.assert_not_called()

    def test_contract_failure_never_reaches_publisher(self):
        with patch.object(p,'validate_publish_contract',side_effect=p.PipelineError('HOLD')):
            with self.assertRaises(p.PipelineError):self.freeze()

    def test_frozen_resume_does_not_rewrite_context(self):
        self.freeze()
        with patch('scripts.editorial_epoch.reject_legacy_run'),patch.object(p,'write_planner_context') as write,patch.object(p,'run_stage') as stage:
            result=p.run_topic_pipeline('codex',self.context,{},logging.getLogger('test'),timeout_seconds=1,resume=True,publish_lock=threading.Lock(),humanize_lock=threading.Lock(),prepare_only=True)
            self.assertEqual(result['status'],'prepared');write.assert_not_called();stage.assert_not_called()
            with self.assertRaises(p.PipelineError):
                p.run_topic_pipeline('codex',self.context,{},logging.getLogger('test'),timeout_seconds=1,resume=True,publish_lock=threading.Lock(),humanize_lock=threading.Lock())

    def test_frozen_publish_is_deterministic_zero_retry(self):
        self.freeze(); service=Mock()
        def factory(client,**kwargs):
            def publish(*args,**kwargs):
                client.create_post({'content':'exact approved HTML'},status='publish')
                return Mock(status='Success',published_url='https://example.test/post',publish_summary={'body_media_ids':[]})
            service.publish_file.side_effect=publish
            return service
        with (
            patch('scripts.editorial_epoch.reject_legacy_run'),patch('scripts.editorial_epoch.reject_retired_publication'),
            patch('scripts.editorial_gate.enforce_prepublication') as preflight,
            patch.object(p,'load_document',return_value=Mock(metadata={})),
            patch.object(p,'has_successful_publish',return_value=False),patch.object(p,'WordPressConfig'),
            patch.object(p,'WordPressClient') as client,patch('publisher.service.DraftPublisher',side_effect=factory),
            patch.object(p,'validate_stage_artifacts'),patch.object(p,'read_publish_result',return_value={'post_id':1}),
            patch.object(p,'run_stage') as stage,
        ):
            args=dict(inventory_path=Path('/fresh/inventory.json'))
            client.return_value.create_post.return_value={'id':1,'status':'publish','link':'https://example.test/post'}
            client.return_value.get_post.return_value={'id':1,'status':'publish','content':{'raw':'exact approved HTML'},'featured_media':2}
            client.return_value.request.return_value={'id':2,'alt_text':'diagram','source_url':'https://example.test/image.png'}
            result=p.publish_prepared_topic(self.context,logging.getLogger('test'),**args)
            self.assertEqual(result['post_id'],1);self.assertTrue(result['content_verified']);self.assertEqual(client.call_args.kwargs['max_retries'],0)
            preflight.assert_called_once_with(self.directory/'publish.md',Path('/fresh/inventory.json'))
            self.assertEqual(service.publish_file.call_args.kwargs['expected_identity']['source_id'],self.context.source_id)
            self.assertEqual(service.publish_file.call_args.kwargs['expected_identity']['category'],self.context.category)
            stage.assert_not_called()
            self.assertEqual(p.publish_prepared_topic(self.context,logging.getLogger('test'),**args),result)
            service.publish_file.assert_called_once()

    def test_confirmed_post_readback_failure_retains_identity(self):
        self.freeze()
        def factory(client,**kwargs):
            service=Mock()
            def publish(*args,**kwargs):
                client.create_post({'content':'approved'},status='publish')
                raise RuntimeError('post-write failure')
            service.publish_file.side_effect=publish
            return service
        with (
            patch('scripts.editorial_epoch.reject_legacy_run'),patch('scripts.editorial_epoch.reject_retired_publication'),
            patch('scripts.editorial_gate.enforce_prepublication'),patch.object(p,'load_document',return_value=Mock(metadata={})),
            patch.object(p,'has_successful_publish',return_value=False),patch.object(p,'WordPressConfig'),
            patch.object(p,'WordPressClient') as client,patch('publisher.service.DraftPublisher',side_effect=factory),
        ):
            client.return_value.create_post.return_value={'id':777,'status':'publish','link':'https://example.test/post'}
            client.return_value.get_post.side_effect=RuntimeError('network failure')
            result=p.publish_prepared_topic(self.context,logging.getLogger('test'),inventory_path=Path('/fresh'))
            self.assertEqual(result['status'],'audit_failed')
            self.assertEqual(result['post_id'],777)
            self.assertTrue(result['confirmed_publication'])
            self.assertFalse(result['content_verified'])
            self.assertEqual(result['expected_html_sha256'],hashlib.sha256(b'approved').hexdigest())

    def test_uncertain_attempt_cannot_retry(self):
        self.freeze(); (self.directory/'prepared-publisher-attempt.json').write_text('{}')
        with (
            patch('scripts.editorial_epoch.reject_legacy_run'),patch('scripts.editorial_epoch.reject_retired_publication'),
            patch('scripts.editorial_gate.enforce_prepublication'),patch.object(p,'load_document',return_value=Mock(metadata={})),
            patch.object(p,'has_successful_publish',return_value=False),patch('publisher.service.DraftPublisher') as publisher,
        ):
            with self.assertRaisesRegex(p.PipelineError,'requires_reconciliation'):
                p.publish_prepared_topic(self.context,logging.getLogger('test'),inventory_path=Path('/fresh'))
            publisher.assert_not_called()

    def test_fresh_inventory_failure_precedes_attempt(self):
        self.freeze()
        with (
            patch('scripts.editorial_epoch.reject_legacy_run'),patch('scripts.editorial_epoch.reject_retired_publication'),
            patch.object(p,'load_document',return_value=Mock(metadata={})),
            patch('scripts.editorial_gate.enforce_prepublication',side_effect=p.PipelineError('stale')),
            patch('publisher.service.DraftPublisher') as publisher,
        ):
            with self.assertRaises(p.PipelineError):
                p.publish_prepared_topic(self.context,logging.getLogger('test'),inventory_path=Path('/fresh'))
            self.assertFalse((self.directory/'prepared-publisher-attempt.json').exists())
            publisher.assert_not_called()

    def test_real_publisher_identity_validation_includes_category(self):
        from publisher.service import DraftPublisher
        from publisher.models import ValidationReport
        metadata={'publish_mode':'publish','title':self.context.title,'run_id':self.context.run_id,
                  'topic_id':self.context.topic_id,'source_id':self.context.source_id,'category':self.context.category}
        (self.directory/'review.md').write_text('APPROVED '+self.digest+' run topic')
        self.freeze()
        report=ValidationReport()
        def create(service,**kwargs):
            service.client.create_post({'content':'approved'},status='publish')
            return Mock(status='Success',published_url='https://example.test/post',publish_summary={'body_media_ids':[]})
        with (
            patch('scripts.editorial_epoch.reject_legacy_run'),patch('scripts.editorial_epoch.reject_retired_publication'),
            patch('scripts.editorial_gate.enforce_prepublication'),patch.object(p,'load_document',return_value=Mock(metadata=metadata)),
            patch.object(p,'has_successful_publish',return_value=False),patch.object(p,'WordPressConfig'),
            patch.object(p,'WordPressClient') as client,
            patch('publisher.service.load_document',return_value=Mock(metadata=metadata)),
            patch('publisher.service.validate_document',return_value=report),
            patch('publisher.foundation_links.enforce_foundation_links'),
            patch.object(DraftPublisher,'_create_post',autospec=True,side_effect=create) as write,
        ):
            client.return_value.create_post.return_value={'id':777,'status':'publish','link':'https://example.test/post'}
            client.return_value.get_post.return_value={'id':777,'status':'publish','content':{'raw':'approved'},'featured_media':2}
            client.return_value.request.return_value={'id':2,'alt_text':'diagram','source_url':'https://example.test/image.png'}
            result=p.publish_prepared_topic(self.context,logging.getLogger('test'),inventory_path=Path('/fresh'))
            self.assertEqual(report.checks['publish_identity'],'passed')
            self.assertEqual(result['status'],'published');write.assert_called_once()

    def test_source_baseline_is_required(self):
        (self.directory/'source-baseline.json').unlink()
        with self.assertRaises(p.PipelineError):self.freeze()

    def test_actual_source_freeze_without_network(self):
        from scripts.editorial_queue import freeze_sources
        (self.directory/'source-baseline.json').unlink()
        (self.directory/'queue-inventory.json').unlink()
        digest='a'*64
        with patch('publisher.frontmatter.load_document',return_value=Mock(markdown='[source](https://example.test/source)')),patch('scripts.editorial_queue.rows',return_value=[]):
            fetch=Mock(return_value=digest)
            result=freeze_sources(self.directory/'final.md',candidate={},destination=self.directory/'source-baseline.json',fetch=fetch)
        self.assertEqual(result['mode'],'before_independent_final_review')
        self.assertEqual(result['sources'],[{'url':'https://example.test/source','sha256':digest}])
        self.assertEqual(json.loads((self.directory/'queue-inventory.json').read_text()),{'items':[]})
        receipt=self.freeze()
        self.assertIn('queue-inventory.json',receipt['artifacts'])

if __name__=='__main__':unittest.main()
