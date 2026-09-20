import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

from publisher.wordpress import WordPressError
from scripts.snapshot_topic_inventory import build_snapshot, fetch_status


class SnapshotInventoryTests(unittest.TestCase):
    def row(self, post_id=1, status="publish"):
        return {"id":post_id, "status":status, "content":{"raw":"<pre>code</pre>body"}}

    def test_exact_hundred_ends_only_on_explicit_invalid_page(self):
        client = Mock()
        rows = [self.row(i + 1) for i in range(100)]
        client.request.side_effect = [rows, WordPressError("api", "end", 400, "rest_post_invalid_page_number")]
        self.assertEqual(fetch_status(client, "publish"), rows)
        self.assertEqual(client.request.call_count, 2)

    def test_other_400_or_first_page_failure_is_not_complete_inventory(self):
        for responses in ([WordPressError("api", "error", 400, "rest_post_invalid_page_number")],
                          [[self.row(i + 1) for i in range(100)], WordPressError("api", "error", 400, "rest_invalid_param")]):
            client = Mock()
            client.request.side_effect = responses
            with self.assertRaises(WordPressError):
                fetch_status(client, "publish")

    def test_missing_content_null_content_and_duplicate_identity_fail_closed(self):
        for rows in ([{"id":1,"status":"publish"}],
                     [{"id":1,"status":"publish","content":{"raw":None}}],
                     [self.row(), self.row()]):
            client = Mock()
            client.request.side_effect = [rows, [], []]
            with self.assertRaises(ValueError):
                build_snapshot(client)

    def test_html_is_preserved_to_exclude_code_in_prose_comparison(self):
        client = Mock()
        client.request.side_effect = [[self.row()], [], []]
        self.assertEqual(build_snapshot(client)["posts"][0]["content"], "<pre>code</pre>body")

    def test_post_moving_between_status_pages_requires_refresh(self):
        client = Mock()
        client.request.side_effect = [[self.row()], [self.row(status="draft")], []]
        with self.assertRaises(ValueError):
            build_snapshot(client)

    def test_future_posts_include_full_content_and_exact_dates_get_only(self):
        client = Mock()
        future = {**self.row(3, 'future'), 'date': '2026-09-21T10:00:00', 'date_gmt': '2026-09-21T01:00:00'}
        client.request.side_effect = [[self.row()], [self.row(2, 'draft')], [future]]
        snapshot = build_snapshot(client)
        self.assertEqual(snapshot['metadata']['statuses'], {'publish': 1, 'draft': 1, 'future': 1})
        scheduled = snapshot['posts'][2]
        self.assertEqual(scheduled['content'], future['content']['raw'])
        self.assertEqual(scheduled['date'], future['date'])
        self.assertEqual(scheduled['date_gmt'], future['date_gmt'])
        statuses = []
        for call in client.request.call_args_list:
            self.assertEqual(call.args[0], 'GET')
            query = parse_qs(urlparse(call.args[1]).query)
            statuses += query['status']
            self.assertTrue({'content', 'date', 'date_gmt'} <= set(query['_fields'][0].split(',')))
        self.assertEqual(statuses, ['publish', 'draft', 'future'])

    def test_future_failure_does_not_return_partial_snapshot(self):
        client = Mock()
        client.request.side_effect = [[], [], WordPressError('api', 'denied', 403, 'forbidden')]
        with self.assertRaises(WordPressError):
            build_snapshot(client)

    def test_duplicate_id_between_draft_and_future_is_rejected(self):
        client = Mock()
        client.request.side_effect = [[], [self.row(3, 'draft')], [self.row(3, 'future')]]
        with self.assertRaises(ValueError):
            build_snapshot(client)


if __name__ == "__main__":
    unittest.main()
