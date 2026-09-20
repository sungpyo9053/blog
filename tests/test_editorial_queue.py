"""Queue safety contract tests: fixtures are synthetic, no network or WP writes."""
import json
import logging
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts import editorial_queue as queue


class EditorialQueueTests(unittest.TestCase):
    def test_line_anchor_ranges_use_raw_source_and_preserve_manifest_url_policy(self):
        base='https://github.com/owner/repo/blob/'+'a'*40+'/src/example.py'
        counter=Mock(return_value=10)
        queue.validate_source_line_anchors(f'[a]({base}#L1-L10) [b]({base}#L10)', line_counter=counter)
        counter.assert_called_once_with('https://raw.githubusercontent.com/owner/repo/'+'a'*40+'/src/example.py')
        self.assertEqual(queue.source_urls(f'[a]({base}#L1-L10)',{}),[base])

    def test_invalid_or_missing_source_line_anchor_fails_closed(self):
        base='https://raw.githubusercontent.com/o/r/main/test.py'
        for fragment in ('L11','L1-L11','L0','L5-L2','L2-Lx'):
            with self.subTest(fragment=fragment), self.assertRaises(ValueError):
                queue.validate_source_line_anchors(f'[source]({base}#{fragment})',line_counter=Mock(return_value=10))
        with self.assertRaises(ValueError):
            queue.validate_source_line_anchors(f'[source]({base}#L1)',line_counter=Mock(return_value=0))

    def test_unrelated_html_anchors_do_not_fetch(self):
        counter=Mock()
        queue.validate_source_line_anchors('[a](https://docs.example.test/topic#L5) [b](https://github.com/o/r/blob/main/readme.md#example)',line_counter=counter)
        counter.assert_not_called()

    def test_freeze_anchor_failure_occurs_before_manifest_creation(self):
        doc=SimpleNamespace(markdown='[a](https://github.com/o/r/blob/main/x.py#L99)')
        fetch=Mock()
        with patch('publisher.frontmatter.load_document',return_value=doc), self.assertRaisesRegex(ValueError,'out_of_range'):
            queue.freeze_sources(self.repo/'publish.md',candidate={},destination=self.repo/'baseline.json',fetch=fetch,line_counter=Mock(return_value=5))
        fetch.assert_not_called()
        self.assertFalse((self.repo/'baseline.json').exists())

    def test_source_http_failure_has_safe_diagnostic_and_still_blocks(self):
        url = 'https://example.test/document?token=do-not-log'
        response = Mock(status_code=403)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(queue, 'safe_url'), patch.object(queue.requests, 'get', return_value=response):
            with self.assertRaises(queue.SourceCheckError) as caught:
                queue.source_digest(url)
        diagnostic = caught.exception.diagnostic
        self.assertEqual(diagnostic['http_status'], 403)
        self.assertEqual(diagnostic['reason'], 'source_recheck_http_error')
        self.assertEqual(diagnostic['source_host'], 'example.test')
        self.assertNotIn('do-not-log', json.dumps(diagnostic))
        response.iter_content.assert_not_called()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.now = datetime(2026, 9, 20, 10, 0, tzinfo=queue.KST)
        self.publisher = Mock(return_value={'post_id': 999, 'url': 'https://example.test/post', 'content_verified': True})
        self.auditor = Mock(return_value={'passed': True})
        self.reviewer = Mock(return_value={'verdict': 'APPROVED'})
        network = patch.object(queue.requests, 'get', side_effect=AssertionError('network forbidden'))
        network.start(); self.addCleanup(network.stop)

    def row(self, ident='synthetic', status='queued'):
        row = {'schema_version': 1, 'queue_id': ident, 'status': status,
               'prepared_at': self.now.isoformat(), 'candidate': {'candidate_id': ident},
               'prepared': {}, 'sources': [{'url': 'https://example.test/source', 'sha256': 'old'}]}
        queue.directory(self.repo).mkdir(parents=True, exist_ok=True)
        queue.save(queue.directory(self.repo)/f'{ident}.json', row, new=True)
        return row

    def release(self, *, apply=True, now=None, run='run', count=0, failure=None):
        with patch('scripts.run_evidence_deep_article.published_today', return_value=count), \
             patch.object(queue, 'preflight', side_effect=failure, return_value=SimpleNamespace()):
            return queue.release(run_id=run, inventory_path=self.repo/'inventory', apply=apply,
                                 repo=self.repo, output_root=self.repo/'runs', logger=logging.getLogger(__name__),
                                 now=now or self.now, publisher=self.publisher, auditor=self.auditor, reviewer=self.reviewer)

    def progress(self):
        return json.loads((self.repo/'runs/run/progress.json').read_text())

    def test_outside_ten_does_not_call_publisher(self):
        self.row()
        result = self.release(now=self.now.replace(hour=9))
        self.assertEqual(result['deep_article'], 'outside_publication_window')
        self.publisher.assert_not_called()

    def test_empty_queue_does_not_call_publisher(self):
        self.assertEqual(self.release()['deep_article'], 'no_publishable_topic')
        self.publisher.assert_not_called()

    def test_daily_limit_does_not_call_publisher(self):
        self.row()
        self.assertEqual(self.release(count=1)['deep_article'], 'daily_limit_reached')
        self.publisher.assert_not_called()

    def test_preflight_failure_holds_without_publisher(self):
        self.row()
        self.assertEqual(self.release(failure=ValueError('queue_source_changed'))['deep_article'], 'no_publishable_topic')
        self.assertEqual(queue.rows(self.repo)[0]['status'], 'held')
        self.publisher.assert_not_called()

    def test_independent_release_review_hold_never_calls_publisher(self):
        self.row()
        self.reviewer.side_effect = ValueError('synthetic HOLD')
        self.assertEqual(self.release()['deep_article'], 'no_publishable_topic')
        self.assertEqual(queue.rows(self.repo)[0]['status'], 'held')
        self.publisher.assert_not_called()

    def test_dry_runs_never_change_queue_rows_even_on_hold(self):
        self.row()
        path = queue.directory(self.repo)/'synthetic.json'
        before = path.read_bytes()
        self.assertEqual(self.release(apply=False)['deep_article'], 'ready_not_published')
        self.release(apply=False, run='hold', failure=ValueError('HOLD'))
        self.assertEqual(path.read_bytes(), before)
        self.publisher.assert_not_called()
        self.assertEqual(self.progress()['wordpress_write_count'], 0)

    def test_publisher_timeout_keeps_unknown_barrier_and_blocks_next_call(self):
        self.row()
        self.publisher.side_effect = TimeoutError('synthetic response loss')
        with self.assertRaises(TimeoutError):
            self.release()
        self.assertEqual(self.progress()['wordpress_write_count'], 'unknown')
        self.assertEqual(queue.rows(self.repo)[0]['status'], 'publishing')
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            self.release(run='retry')
        self.publisher.assert_called_once()
        self.auditor.assert_not_called()

    def test_confirmed_post_missing_url_still_consumes_one(self):
        self.row()
        self.publisher.return_value = {'post_id': 999, 'content_verified': True}
        with self.assertRaises(ValueError):
            self.release()
        self.assertEqual(self.progress()['wordpress_write_count'], 1)
        self.publisher.assert_called_once()
        self.auditor.assert_not_called()

    def test_audit_failure_does_not_unconsume_publication(self):
        self.row()
        self.auditor.side_effect = ValueError('synthetic public audit failure')
        with self.assertRaises(ValueError):
            self.release()
        self.assertEqual(self.progress()['wordpress_write_count'], 1)
        self.assertEqual(queue.rows(self.repo)[0]['status'], 'published')
        self.assertEqual(json.loads((self.repo/'runs/run/publication.json').read_text())['wordpress_write_count'], 1)
        self.publisher.assert_called_once()

    def test_malformed_state_fails_closed(self):
        row = self.row()
        for change in ({'schema_version': 3}, {'status': 'approved-ish'}, {'queue_id': 'different'}):
            with self.subTest(change=change):
                queue.save(queue.directory(self.repo)/'synthetic.json', {**row, **change})
                with self.assertRaises(ValueError):
                    queue.rows(self.repo)
        self.publisher.assert_not_called()

    def test_preparation_target_seven_and_unresolved_barrier(self):
        self.assertTrue(queue.preparation_allowed(self.repo))
        for i in range(7):
            self.row(str(i))
        self.assertFalse(queue.preparation_allowed(self.repo))
        self.assertEqual(queue.reserved_candidate_ids(self.repo), {str(i) for i in range(7)})

    def test_preparation_blocks_unresolved_even_below_target(self):
        self.row(status='publishing')
        self.assertFalse(queue.preparation_allowed(self.repo))

    def test_enqueue_hard_cap_seven_before_artifact_or_fetch(self):
        for i in range(7):
            self.row(str(i))
        fetch = Mock()
        with self.assertRaisesRegex(ValueError, 'capacity'):
            queue.enqueue({'candidate_id': 'new'}, {}, repo=self.repo, fetch=fetch)
        fetch.assert_not_called()

    def test_enqueue_duplicate_candidate_including_held(self):
        self.row(status='held')
        with self.assertRaisesRegex(ValueError, 'already_reserved'):
            queue.enqueue({'candidate_id': 'synthetic'}, {}, repo=self.repo)

    def test_source_changed_preflight_rejects_before_inventory_gate(self):
        row = self.row()
        article = self.repo/'output/article'; article.mkdir()
        (article/'physical-ai-quality-review.json').write_text(json.dumps({'reviewed_at': self.now.isoformat()}))
        with patch.object(queue, 'context_for', return_value=SimpleNamespace(directory=article)), \
             patch('scripts.run_daily_pipeline.validate_prepared_artifacts'), \
             patch('scripts.run_daily_pipeline.validate_publish_contract'), \
             patch('scripts.editorial_gate.enforce_prepublication') as gate:
            with self.assertRaisesRegex(ValueError, 'source_changed'):
                queue.preflight(row, repo=self.repo, inventory_path=self.repo/'inventory', now=self.now, fetch=Mock(return_value='new'))
        gate.assert_not_called()
        self.publisher.assert_not_called()

    def test_reservation_preflight_rechecks_anchor_despite_unchanged_source_hash(self):
        row=self.row();article=self.repo/'output/article';article.mkdir()
        (article/'physical-ai-quality-review.json').write_text(json.dumps({'reviewed_at':self.now.isoformat()}))
        (article/'publish.md').write_text('[bad](https://raw.githubusercontent.com/o/r/main/x.py#L99)')
        with patch.object(queue,'context_for',return_value=SimpleNamespace(directory=article)), patch('scripts.run_daily_pipeline.validate_prepared_artifacts'), patch('scripts.run_daily_pipeline.validate_publish_contract'), patch('scripts.editorial_gate.enforce_prepublication') as gate:
            with self.assertRaisesRegex(ValueError,'out_of_range'):
                queue.preflight(row,repo=self.repo,inventory_path=self.repo/'inventory',now=self.now,fetch=Mock(return_value='old'),line_counter=Mock(return_value=4))
        gate.assert_not_called();self.publisher.assert_not_called()

    def test_raw_line_fetch_preserves_count_and_rejects_html_and_oversize(self):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.status_code=200;response.headers={'Content-Type':'text/plain'}
        response.iter_content.return_value=[b'one\r\ntwo\nthree']
        with patch.object(queue,'safe_url') as safe, patch.object(queue.requests,'get',return_value=response) as get:
            self.assertEqual(queue.source_line_count('https://raw.githubusercontent.com/o/r/main/a.py'),3)
            safe.assert_called_once();self.assertFalse(get.call_args.kwargs['allow_redirects'])
            response.headers={'Content-Type':'text/html'}
            with self.assertRaisesRegex(ValueError,'not_raw_text'):queue.source_line_count('https://raw.githubusercontent.com/o/r/main/a.py')
            response.headers={'Content-Type':'text/plain'};response.iter_content.return_value=[b'x'*4000001]
            with self.assertRaisesRegex(ValueError,'too_large'):queue.source_line_count('https://raw.githubusercontent.com/o/r/main/a.py')

    def test_freeze_deduplicates_fragments_excludes_internal_and_checks_pinned_hash(self):
        doc = SimpleNamespace(markdown='[one](https://example.test/source#a) [two](https://example.test/source#b) [home](https://huntlab.app/start)')
        candidate = {'foundation_contract': {'worked_example': {'public_url': 'https://example.test/source', 'sha256': 'expected'}}}
        fetch = Mock(return_value='expected')
        with patch('publisher.frontmatter.load_document', return_value=doc), patch.object(queue, 'rows', return_value=[]):
            payload = queue.freeze_sources(self.repo/'publish.md', candidate=candidate, destination=self.repo/'baseline.json', fetch=fetch)
            self.assertEqual(payload['mode'], 'before_independent_final_review')
            self.assertEqual(payload['sources'], [{'url': 'https://example.test/source', 'sha256': 'expected'}])
            fetch.assert_called_once()
            with self.assertRaisesRegex(ValueError, 'pinned_evidence_mismatch'):
                queue.freeze_sources(self.repo/'publish.md', candidate=candidate, destination=self.repo/'bad.json', fetch=Mock(return_value='changed'))
        self.assertFalse((self.repo/'bad.json').exists())

    def test_enqueue_requires_exact_source_set_hash_and_before_review_baseline(self):
        article = self.repo/'output/article'; article.mkdir(parents=True)
        doc = SimpleNamespace(markdown='[source](https://example.test/source)', metadata={})
        baseline = {'checked_at': self.now.isoformat(), 'sources': [{'url': 'https://example.test/source', 'sha256': 'expected'}]}
        (article/'physical-ai-quality-review.json').write_text(json.dumps({'reviewed_at': self.now.isoformat()}))
        for mutation, digest, reason in (
            ({'sources': []}, 'expected', 'sources_changed_after_review'),
            ({'checked_at': self.now.replace(hour=11).isoformat()}, 'expected', 'not_independently_reviewed'),
            ({}, 'changed', 'source_changed'),
        ):
            with self.subTest(reason=reason):
                (article/'source-baseline.json').write_text(json.dumps({**baseline, **mutation}))
                with patch.object(queue, 'context_for', return_value=SimpleNamespace(directory=article)), \
                     patch('publisher.frontmatter.load_document', return_value=doc), \
                     patch('scripts.run_daily_pipeline.validate_prepared_artifacts'), \
                     patch.object(queue, 'check_queue_overlap'):
                    with self.assertRaisesRegex(ValueError, reason):
                        queue.enqueue({'candidate_id': 'fixture'}, {}, repo=self.repo, now=self.now, fetch=Mock(return_value=digest))
                self.assertEqual(queue.rows(self.repo), [])


if __name__ == '__main__':
    unittest.main()
