from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.audit_editorial_release import (
    AuditError, BASE, CATEGORY_SLUGS, KEEP, check_archived_sitemap,
    fetch_collection, validate_public_posts,
)


def response(rows, total=None, pages=None):
    total = len(rows) if total is None else total
    return {'status': 200, 'body': json.dumps(rows), 'headers': {
        'x-wp-total': str(total),
        'x-wp-totalpages': str((total + 99) // 100 if pages is None else pages),
    }}


def posts():
    return [{'id': i, 'link': BASE + str(i) + '/', 'status': 'publish',
             'categories': [1], 'meta': {}} for i in sorted(KEEP)]


CATEGORIES = [{'id': i, 'slug': slug} for i, slug in enumerate(sorted(CATEGORY_SLUGS), 1)]


class PublicInventoryTests(unittest.TestCase):
    def test_fetches_all_pages(self):
        fetcher = Mock(side_effect=[response([{'id': i} for i in range(1, 101)], 101),
                                    response([{'id': 101}], 101)])
        self.assertEqual(len(fetch_collection('posts', 'id', fetcher)), 101)
        self.assertIn('page=2', fetcher.call_args.args[0])

    def test_exact_full_page_needs_no_invalid_page_probe(self):
        fetcher = Mock(return_value=response([{'id': i} for i in range(1, 101)]))
        self.assertEqual(len(fetch_collection('posts', 'id', fetcher)), 100)
        self.assertEqual(fetcher.call_count, 1)

    def test_empty_collection(self):
        self.assertEqual(fetch_collection('posts', 'id', Mock(return_value=response([]))), [])

    def test_rejects_incomplete_or_untrusted_pages(self):
        invalid = [
            {'status': 500},
            {'status': 200, 'body': '[]', 'headers': {}},
            response([], 1), response([], -1), response([], 101, 1),
            response([{'id': 1}, {'id': 1}]), response([{'id': True}]),
            response([{'id': -1}]), response([{}]), response({'error': 'bad'}),
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(AuditError):
                fetch_collection('posts', 'id', Mock(return_value=value))

    def test_rejects_changed_totals_and_repeated_ids_between_pages(self):
        first = response([{'id': i} for i in range(1, 101)], 101)
        for second in [response([{'id': 101}], 102), response([{'id': 1}], 101)]:
            with self.subTest(second=second), self.assertRaises(AuditError):
                fetch_collection('posts', 'id', Mock(side_effect=[first, second]))


class PublicEligibilityTests(unittest.TestCase):
    def test_original_baseline_passes(self):
        self.assertEqual(validate_public_posts(posts(), CATEGORIES), [])

    def test_new_evidence_article_in_scoped_category_passes(self):
        rows = posts() + [{'id': 800, 'link': BASE + 'new-case/', 'status': 'publish',
                           'categories': [2], 'meta': {'_hunt_news_content_type': 'evidence_deep_article'}}]
        self.assertEqual(validate_public_posts(rows, CATEGORIES), [])

    def test_untyped_or_legacy_additional_post_is_not_silently_accepted(self):
        for meta in [{}, None, {'_hunt_news_content_type': 'verified_case'}]:
            rows = posts() + [{'id': 800, 'link': BASE + 'new-case/', 'status': 'publish',
                               'categories': [2], 'meta': meta}]
            self.assertIn('unexpected_public_post:800', validate_public_posts(rows, CATEGORIES))

    def test_missing_baseline_fails(self):
        self.assertIn('missing_curated_baseline', validate_public_posts(posts()[1:], CATEGORIES))

    def test_incorrect_category_status_or_link_fails(self):
        for field, value, failure in [
            ('categories', [999], 'post_editorial_category'),
            ('categories', [1, 999], 'post_editorial_category'),
            ('categories', [], 'post_editorial_category'),
            ('status', 'draft', 'post_status'),
            ('link', 'https://example.com/post/', 'post_link'),
            ('link', None, 'post_link'),
        ]:
            rows = posts(); rows[0][field] = value
            with self.subTest(field=field, value=value):
                self.assertIn(failure + ':' + str(rows[0]['id']), validate_public_posts(rows, CATEGORIES))

    def test_missing_category_contract_fails(self):
        self.assertIn('editorial_categories_missing_or_ambiguous', validate_public_posts(posts(), CATEGORIES[:2]))


class ArchivedSitemapTests(unittest.TestCase):
    def test_missing_baseline_fails_instead_of_skipping(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(check_archived_sitemap(Path(directory) / 'absent.json', set()),
                             ['archive_baseline_unavailable_or_invalid'])

    def test_archived_url_is_rejected_and_kept_url_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / 'plan.json'
            plan.write_text(json.dumps({'changes': [
                {'id': 8, 'status': 'draft', 'before': {'link': BASE + 'archived/'}},
                {'id': 50, 'status': 'publish', 'before': {'link': BASE + 'kept/'}},
            ]}))
            self.assertEqual(check_archived_sitemap(plan, {BASE + 'kept/'}), [])
            self.assertEqual(check_archived_sitemap(plan, {BASE + 'archived/'}), ['archived_in_sitemap:8'])

    def test_invalid_or_empty_baseline_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = Path(directory) / 'plan.json'
            for body in ['invalid', '{}', '{"changes": []}']:
                plan.write_text(body)
                self.assertEqual(check_archived_sitemap(plan, set()), ['archive_baseline_unavailable_or_invalid'])


if __name__ == '__main__':
    unittest.main()
