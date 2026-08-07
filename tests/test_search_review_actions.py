from __future__ import annotations

import unittest
from datetime import date

from scripts.apply_search_review_actions import (
    CASE_LINK_MARKER,
    add_reviewed_case_links,
    parse_title_experiment,
)


class SearchReviewActionTests(unittest.TestCase):
    def test_title_experiment_requires_matching_date_and_eligible_status(self):
        report = (
            "- generated_at: `2026-08-07T01:00:00+09:00`\n"
            "- resident_title_experiment: `ELIGIBLE_REVIEW`\n"
            "- resident_title_metrics: `clicks=0, impressions=40, position=11.2`\n"
            "- proposed_single_change: `title_only` → `새 제목`\n"
            "- experiment_stop_rule: `14_days_or_1000_impressions`\n"
        )
        decision = parse_title_experiment(report, date(2026, 8, 7))
        self.assertEqual(decision["proposed_title"], "새 제목")
        self.assertEqual(decision["impressions"], 40)
        with self.assertRaises(ValueError):
            parse_title_experiment(report, date(2026, 8, 8))

    def test_reviewed_links_require_source_mention_and_are_idempotent(self):
        targets = [
            {
                "id": 10,
                "status": "publish",
                "slug": "amazon-bedrock-openai-api-migration",
                "link": "https://huntlab.app/amazon-bedrock-openai-api-migration/",
                "title": {"rendered": "Amazon Bedrock OpenAI API 마이그레이션"},
            },
            {
                "id": 11,
                "status": "publish",
                "slug": "wordpress-rest-api-pagination",
                "link": "https://huntlab.app/wordpress-rest-api-pagination/",
                "title": {"rendered": "WordPress REST API Pagination"},
            },
        ]
        original = (
            "<p>amazon-bedrock-openai-api-migration 및 "
            "wordpress-rest-api-pagination을 검사했다.</p>\n"
            "<h2>참고 링크</h2>"
        )
        updated = add_reviewed_case_links(original, targets)
        self.assertIn(CASE_LINK_MARKER, updated)
        self.assertEqual(updated.count("https://huntlab.app/"), 2)
        self.assertEqual(add_reviewed_case_links(updated, targets), updated)

    def test_reviewed_link_rejects_unmentioned_target(self):
        target = {
            "id": 10,
            "slug": "unmentioned",
            "link": "https://huntlab.app/unmentioned/",
            "title": {"rendered": "언급되지 않은 글"},
        }
        with self.assertRaises(ValueError):
            add_reviewed_case_links("<p>다른 글</p>", [target])


if __name__ == "__main__":
    unittest.main()
