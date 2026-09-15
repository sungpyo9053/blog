import copy
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from scripts.apply_editorial_corrections import CorrectionError, apply_corrections, sha


class FakeClient:
    max_retries = 0

    def __init__(self, posts):
        self.posts = copy.deepcopy(posts)
        self.writes = []
        self.lose_response = False
        self.reject = False

    def get_post(self, post_id):
        return copy.deepcopy(self.posts[post_id])

    def request(self, method, path, *, payload, expected):
        assert method == 'POST'
        self.writes.append((path, payload))
        if self.reject:
            raise TimeoutError('Do not disclose credentials')
        self.posts[int(path.split('/')[-1])]['content']['raw'] = payload['content']
        if 'title' in payload:
            self.posts[int(path.split('/')[-1])]['title'] = {'raw': payload['title']}
        if self.lose_response:
            raise TimeoutError('Response lost after saving')


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'manifest.json'
        self.approval = self.root / 'approval.md'
        self.receipts = self.root / 'receipts'
        self.posts = {}
        rows = []
        for post_id in (50, 290):
            before = '<p>Original case ' + str(post_id) + '</p>'
            after = '<p>Corrected case ' + str(post_id) + '</p>'
            (self.root / f'{post_id}.before.html').write_text(before)
            (self.root / f'{post_id}.after.html').write_text(after)
            self.posts[post_id] = {
                'id': post_id, 'slug': f'case-{post_id}', 'title': {'raw': f'Case {post_id}'},
                'status': 'publish', 'categories': [1], 'tags': [2], 'featured_media': 3,
                'author': 1, 'date': '2026-09-01', 'date_gmt': '2026-09-01',
                'excerpt': {'raw': 'Excerpt'}, 'meta': {}, 'link': f'https://huntlab.app/case-{post_id}/',
                'content': {'raw': before},
            }
            rows.append({'post_id': post_id, 'slug': f'case-{post_id}', 'title': f'Case {post_id}',
                         'before_file': f'{post_id}.before.html', 'after_file': f'{post_id}.after.html',
                         'before_sha256': sha(before), 'after_sha256': sha(after)})
        self.manifest.write_text(json.dumps({'posts': rows}))
        self.approval.write_text('status: APPROVED\nmanifest_sha256: ' + sha(self.manifest.read_text()) + '\n')
        self.inventory = {'metadata': {'complete': True, 'full_content': True,
                                      'collected_at': datetime.now(UTC).isoformat(),
                                      'statuses': {'publish': 2, 'draft': 0}},
                          'posts': [{'post_id': i, 'slug': p['slug'], 'title': p['title']['raw'],
                                     'status': 'publish', 'content': p['content']['raw']}
                                    for i, p in self.posts.items()]}
        self.client = FakeClient(self.posts)

    def run_apply(self, apply=True):
        return apply_corrections(self.client, self.manifest, self.approval, self.receipts,
                                 apply=apply, inventory=self.inventory)

    def test_dry_run_has_no_writes_or_receipts(self):
        self.assertEqual(self.run_apply(False)['status'], 'preflight_passed')
        self.assertFalse(self.receipts.exists())
        self.assertEqual(self.client.writes, [])

    def test_body_only_write_backups_and_idempotent_readback(self):
        self.assertEqual(self.run_apply()['wordpress_writes'], 2)
        self.assertTrue((self.receipts / '50.before.json').exists())
        self.assertTrue((self.receipts / '290.verified.json').exists())
        self.assertTrue(all(set(payload) == {'content'} for _, payload in self.client.writes))
        self.assertEqual(self.run_apply()['wordpress_writes'], 0)
        self.assertEqual(len(self.client.writes), 2)

    def test_all_preflight_before_first_write(self):
        self.client.posts[290]['content']['raw'] = 'Concurrent edit'
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(self.client.writes, [])
        self.assertFalse(self.receipts.exists())

    def test_approval_or_content_tamper_fails_before_writes(self):
        self.approval.write_text('status: REJECTED\n')
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(self.client.writes, [])

    def test_after_hash_tamper_fails(self):
        (self.root / '50.after.html').write_text('Changed after approval')
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(self.client.writes, [])

    def test_response_loss_resolved_by_get_without_retry(self):
        self.client.lose_response = True
        self.assertEqual(self.run_apply()['status'], 'verified')
        self.assertEqual(len(self.client.writes), 2)

    def test_unknown_outcome_blocks_rerun(self):
        self.client.reject = True
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(len(self.client.writes), 1)
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(len(self.client.writes), 1)

    def test_client_retries_forbidden(self):
        self.client.max_retries = 3
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(self.client.writes, [])

    def test_identity_collision_fails(self):
        self.inventory['posts'].append({'post_id': 800, 'title': 'Case 50', 'slug': 'other',
                                        'status': 'draft', 'content': 'Another document'})
        self.inventory['metadata']['statuses']['draft'] = 1
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(self.client.writes, [])

    def test_final_combined_content_overlap_fails(self):
        repeated = 'This is the same long editorial paragraph. ' * 10
        manifest = json.loads(self.manifest.read_text())
        for row in manifest['posts']:
            (self.root / row['after_file']).write_text(repeated)
            row['after_sha256'] = sha(repeated)
        self.manifest.write_text(json.dumps(manifest))
        self.approval.write_text('status: APPROVED\nmanifest_sha256: ' + sha(self.manifest.read_text()) + '\n')
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(self.client.writes, [])

    def change_titles(self, values):
        manifest = json.loads(self.manifest.read_text())
        for row, title in zip(manifest['posts'], values):
            row['new_title'] = title
        self.manifest.write_text(json.dumps(manifest))
        self.approval.write_text('status: APPROVED\nmanifest_sha256: ' + sha(self.manifest.read_text()) + '\n')

    def test_explicit_reviewed_title_update_and_response_loss_recovery(self):
        self.change_titles(['Reader problem A', 'Reader problem B'])
        self.client.lose_response = True
        self.assertEqual(self.run_apply()['wordpress_writes'], 2)
        self.assertEqual(self.client.posts[50]['title']['raw'], 'Reader problem A')
        self.assertEqual(self.client.posts[50]['slug'], 'case-50')
        self.assertEqual(self.run_apply()['wordpress_writes'], 0)

    def test_proposed_title_collision_in_final_state_blocks_all_writes(self):
        self.change_titles(['Same proposed title', 'Same proposed title'])
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(self.client.writes, [])

    def test_unapproved_title_cannot_be_injected(self):
        manifest = json.loads(self.manifest.read_text())
        manifest['posts'][0]['new_title'] = 'Changed after review'
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(self.client.writes, [])

    def test_title_change_still_requires_exact_old_identity(self):
        self.change_titles(['Reader problem A', 'Reader problem B'])
        self.client.posts[50]['title']['raw'] = 'Concurrent edit'
        with self.assertRaises(CorrectionError):
            self.run_apply()
        self.assertEqual(self.client.writes, [])


if __name__ == '__main__':
    unittest.main()
