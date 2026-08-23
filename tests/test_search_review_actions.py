from __future__ import annotations

import json
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import scripts.apply_search_review_actions as search_review_actions
from scripts.apply_search_review_actions import (
    CASE_LINK_MARKER,
    add_reviewed_case_links,
    apply_title_experiment,
    parse_title_experiment,
)


class SearchReviewActionTests(unittest.TestCase):
    def test_title_experiment_backups_do_not_collide_for_shared_timestamp(self):
        class FakeWordPressClient:
            def __init__(self):
                self.posts = {
                    72: {
                        "id": 72,
                        "status": "publish",
                        "slug": "oil-price-cap-8th",
                        "title": {"rendered": "기존 제목 72"},
                        "content": {"raw": "본문 72"},
                    },
                    499: {
                        "id": 499,
                        "status": "publish",
                        "slug": "housing-subscription-first-priority",
                        "title": {"rendered": "기존 제목 499"},
                        "content": {"raw": "본문 499"},
                    },
                }

            def get_post(self, post_id):
                return self.posts[post_id]

            def update_post(self, post_id, payload, *, status):
                self.posts[post_id]["title"] = {"rendered": payload["title"]}
                self.posts[post_id]["status"] = status

        decision = {
            "proposed_title": "새 제목",
            "clicks": 0,
            "impressions": 100,
            "position": 7.0,
            "stop_rule": "14_days_or_1000_impressions",
        }
        timestamp = datetime(2026, 8, 22, 22, 39, 40, 303801, tzinfo=UTC)

        with TemporaryDirectory() as temp_dir, patch.object(
            search_review_actions, "ROOT", Path(temp_dir)
        ):
            client = FakeWordPressClient()
            first = apply_title_experiment(
                client,
                post_id=72,
                expected_current_title="기존 제목 72",
                decision=decision,
                apply=True,
                approved_by="reviewer-test",
                timestamp=timestamp,
            )
            second = apply_title_experiment(
                client,
                post_id=499,
                expected_current_title="기존 제목 499",
                decision=decision,
                apply=True,
                approved_by="reviewer-test",
                timestamp=timestamp,
            )

            self.assertNotEqual(first["backup"], second["backup"])
            self.assertIn("post-72-title-experiment.json", first["backup"])
            self.assertIn("post-499-title-experiment.json", second["backup"])
            first_backup = Path(temp_dir) / first["backup"]
            second_backup = Path(temp_dir) / second["backup"]
            self.assertEqual(
                json.loads(first_backup.read_text(encoding="utf-8"))["post_id"], 72
            )
            self.assertEqual(
                json.loads(second_backup.read_text(encoding="utf-8"))["post_id"], 499
            )

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
