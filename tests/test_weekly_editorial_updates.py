import copy
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from scripts.weekly_editorial_updates import apply_reviewed_update, action_hash, sha256
from scripts.setup_physical_ai_categories import CATEGORIES


class Client:
    def __init__(self, post):
        self.post = copy.deepcopy(post)
        self.max_retries = 3
        self.writes = []
        self.reads = 0
        self.conflict = False
        self.fail_write = False
        self.mutate_metadata = False
        self.render_change = False

    def request(self, method, path, **kwargs):
        if method == 'POST':
            assert self.max_retries == 0
            self.writes.append(kwargs['payload'])
            self.post['content']['raw'] = kwargs['payload']['content']
            if self.mutate_metadata:
                self.post['slug'] = 'changed'
            if self.render_change:
                self.post['aioseo_head'] = '<meta content="changed-modified-date">'
                self.post['title']['rendered'] = 'new render'
                self.post['excerpt'] = {'raw': '', 'rendered': 'new generated excerpt'}
            if self.fail_write:
                raise TimeoutError('secret remote response')
            return copy.deepcopy(self.post)
        if path.startswith('categories?'):
            slug = path.split('slug=')[1].split('&')[0]
            return [{'id': 10, 'slug': slug, 'name': CATEGORIES[slug]}] if slug == 'physical-ai-basics' else []
        self.reads += 1
        value = copy.deepcopy(self.post)
        if self.conflict and self.reads == 2:
            value['modified'] = 'later'
        if self.render_change and self.reads == 2:
            value['_links'] = {'nonce': 'volatile'}
        return value


class WeeklyUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.old = '<p>이 설명에서는 관측과 행동의 관계를 차례대로 살펴봅니다.</p>'
        self.new = '<p>이 설명에서는 관측과 행동의 관계를 순서대로 살펴봅니다.</p>'
        self.raw = '<h2>기초 설명</h2>' + self.old + '<p>다음 절에서는 예제의 구조를 자세히 설명합니다.</p>'
        self.post = {'id': 17, 'status': 'publish', 'title': {'raw': '기초'}, 'slug': 'basics',
                     'content': {'raw': self.raw}, 'categories': [10], 'tags': [2],
                     'featured_media': 3, 'meta': {'seo': 'preserved'}, 'modified': 'now',
                     'link': 'https://huntlab.app/basics/'}
        self.client = Client(self.post)
        self.action = {'post_id': 17, 'before_sha256': sha256(self.raw), 'old_paragraph': self.old,
                       'new_paragraph': self.new, 'reason': '설명 문장의 가독성 개선',
                       'evidence_refs': ['output/weekly/source.json']}
        self.review = {'verdict': 'APPROVED', 'action_sha256': action_hash(self.action),
                       'after_sha256': sha256(self.raw.replace(self.old, self.new)),
                       'writer_id': 'writer', 'reviewer_id': 'reviewer', 'post_id': 17,
                       'title': '기초', 'slug': 'basics', 'gates': {f'gate{i}': True for i in range(1, 9)},
                       'items': [{'id': i, 'score': 5, 'reason': 'reviewed', 'body_location': 'paragraph1',
                                  'evidence_ref': 'source.json'} for i in range(1, 21)], 'total': 100}
        # Synthetic schema fixture; these are not content review findings.
        self.review['naturalness'] = {
            'verdict': 'PASS', 'unresolved_issues': [],
            'comparison_refs': ['synthetic recent-article fixture'],
            'checks': [dict(id=name, passed=True, reason='Synthetic reason',
                            body_location='fixture paragraph', evidence_ref='synthetic fixture')
                       for name in ('structure', 'rhythm', 'restraint', 'judgment', 'honesty')],
        }
        self.inventory = {'metadata': {'complete': True, 'full_content': True,
                                      'collected_at': datetime.now(UTC).isoformat(),
                                      'statuses': {'publish': 1, 'draft': 0}},
                          'posts': [{'post_id': 17, 'status': 'publish', 'content': self.raw}]}

    def run_update(self, apply=True):
        with patch('scripts.weekly_editorial_updates._public_verify', return_value={'http_status': 200}):
            return apply_reviewed_update(self.client, action=self.action, review=self.review,
                                         run_dir=self.directory, inventory=self.inventory, apply=apply)

    def test_dry_run_never_writes(self):
        self.assertEqual(self.run_update(False)['status'], 'dry_run')
        self.assertFalse(self.client.writes)

    def test_verified_update_and_idempotency(self):
        self.assertEqual(self.run_update()['status'], 'updated')
        self.assertEqual(self.run_update()['status'], 'already_updated')
        self.assertEqual(self.run_update(False)['wp_write_count'], 0)
        self.assertEqual(len(self.client.writes), 1)
        self.assertEqual(set(self.client.writes[0]), {'content'})
        self.assertEqual(self.client.max_retries, 3)
        backup = next(self.directory.glob('*.before.json'))
        self.assertEqual(json.loads(backup.read_text()), self.post)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_missing_review(self):
        self.review = {}
        self.assertEqual(self.run_update()['status'], 'rejected')
        self.assertFalse(self.client.writes)

    def test_naturalness_fail_closed_before_any_wordpress_write(self):
        original = copy.deepcopy(self.review)
        invalids = [None, {}, {**original['naturalness'], 'verdict': 'HOLD'}]
        for flag in (False, 1, 'NOT_EVALUATED'):
            invalid = copy.deepcopy(original['naturalness'])
            invalid['checks'][0]['passed'] = flag
            invalids.append(invalid)
        for invalid in invalids:
            with self.subTest(invalid=invalid):
                self.review = copy.deepcopy(original)
                self.review['naturalness'] = invalid
                result = self.run_update()
                self.assertEqual(result['status'], 'rejected')
                self.assertEqual(result['wp_write_count'], 0)
                self.assertFalse(self.client.writes)
        self.review = copy.deepcopy(original)
        del self.review['naturalness']
        self.assertEqual(self.run_update()['status'], 'rejected')
        self.assertFalse(self.client.writes)

    def test_naturalness_item17_four_blocks_otherwise_passing_99(self):
        self.review['items'][16]['score'] = 4
        self.review['total'] = 99
        self.assertEqual(self.run_update()['status'], 'rejected')
        self.assertFalse(self.client.writes)

    def test_mutated_action_rejected(self):
        self.action['reason'] = '다른 이유'
        self.assertEqual(self.run_update()['reason'], 'review_hash_mismatch')

    def test_mutated_target_review(self):
        self.review['title'] = '다른 제목'
        self.assertEqual(self.run_update()['reason'], 'review_target_mismatch')

    def test_source_conflict(self):
        self.client.conflict = True
        self.assertEqual(self.run_update()['reason'], 'concurrent_source_change')
        self.assertFalse(self.client.writes)

    def test_draft_rejected(self):
        self.client.post['status'] = 'draft'
        self.assertEqual(self.run_update()['reason'], 'published_target_required')

    def test_old_category_rejected(self):
        self.client.post['categories'] = [88]
        self.assertEqual(self.run_update()['reason'], 'physical_category_required')

    def test_uncertain_write_never_repeated(self):
        self.client.fail_write = True
        self.assertEqual(self.run_update()['status'], 'update_unconfirmed')
        self.assertEqual(self.run_update()['status'], 'update_unconfirmed')
        self.assertEqual(len(self.client.writes), 1)

    def test_metadata_mutation_unconfirmed(self):
        self.client.mutate_metadata = True
        self.assertEqual(self.run_update()['status'], 'update_unconfirmed')

    def test_secret_rejected(self):
        self.action['reason'] = 'Authorization: Bearer secret-token-value'
        self.assertEqual(self.run_update()['reason'], 'possible_secret')

    def test_duplicate_inventory_rejected(self):
        self.inventory['posts'].append(copy.deepcopy(self.inventory['posts'][0]))
        self.assertEqual(self.run_update()['reason'], 'inventory_or_duplicate_failed')

    def test_technical_term_change_rejected(self):
        self.action['new_paragraph'] = self.new.replace('관측', '상태')
        self.assertEqual(self.run_update()['reason'], 'protected_content_changed')

    def test_html_injection_rejected(self):
        self.action['new_paragraph'] = '<p>스크립트를 넣는 내용입니다.<script>alert(1)</script></p>'
        self.assertEqual(self.run_update()['reason'], 'plain_paragraph_required')

    def test_score_and_self_review_rejected(self):
        self.review['reviewer_id'] = 'writer'
        self.assertEqual(self.run_update()['reason'], 'independent_review_required')

    def test_quality_below_threshold(self):
        self.review['items'][0]['score'] = 3
        self.review['total'] = 98
        self.assertEqual(self.run_update()['reason'], 'quality_below_threshold')

    def test_stale_inventory(self):
        self.inventory['metadata']['collected_at'] = '2020-01-01T00:00:00+00:00'
        self.assertEqual(self.run_update()['reason'], 'inventory_or_duplicate_failed')

    def test_unsafe_url_prevents_write(self):
        self.client.post['link'] = 'https://huntlab.app.evil.example/secret'
        self.assertEqual(self.run_update()['reason'], 'unsafe_public_url')
        self.assertFalse(self.client.writes)

    def test_public_failure_blocks_retry(self):
        with patch('scripts.weekly_editorial_updates._public_verify', side_effect=TimeoutError):
            result = apply_reviewed_update(self.client, action=self.action, review=self.review,
                                           run_dir=self.directory, inventory=self.inventory, apply=True)
        self.assertEqual(result['status'], 'update_unconfirmed')
        self.assertEqual(self.run_update()['status'], 'update_unconfirmed')
        self.assertEqual(len(self.client.writes), 1)

    def test_receipt_save_failure_blocks_retry(self):
        from scripts.weekly_editorial_updates import _save_exclusive
        def save(path, value):
            if path.name.endswith('.result.json'):
                raise OSError('disk full')
            return _save_exclusive(path, value)
        with patch('scripts.weekly_editorial_updates._save_exclusive', side_effect=save):
            self.assertEqual(self.run_update()['status'], 'update_unconfirmed')
        self.assertEqual(self.run_update()['status'], 'update_unconfirmed')
        self.assertEqual(len(self.client.writes), 1)

    def test_raw_inventory_target_required(self):
        self.inventory['posts'][0]['content'] = 'different'
        self.assertEqual(self.run_update()['reason'], 'inventory_target_conflict')

    def test_normalized_actor_identity(self):
        self.review['reviewer_id'] = ' WRITER '
        self.assertEqual(self.run_update()['reason'], 'independent_review_required')

    def test_rendered_derived_metadata_does_not_block(self):
        self.client.render_change = True
        self.client.post['excerpt'] = {'raw': '', 'rendered': 'old excerpt'}
        self.assertEqual(self.run_update()['status'], 'updated')

    def test_action_control_character(self):
        self.action['reason'] += '\u202e'
        self.assertEqual(self.run_update()['reason'], 'action_control_characters')

    def test_oversized_action(self):
        self.action['reason'] = 'x' * 65536
        self.assertEqual(self.run_update()['reason'], 'action_too_large')

    def test_saved_meta_seo_still_frozen(self):
        from scripts.weekly_editorial_updates import _metadata
        before = copy.deepcopy(self.post)
        after = copy.deepcopy(before)
        after['aioseo_meta_data'] = {'title': 'changed'}
        self.assertNotEqual(_metadata(before), _metadata(after))


if __name__ == '__main__':
    unittest.main()
