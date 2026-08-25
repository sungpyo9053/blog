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
    RELATED_LINK_MARKER,
    add_related_article_links,
    add_reviewed_case_links,
    apply_title_experiment,
    parse_ctr_queue_decision,
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

    def test_ctr_queue_decision_requires_current_review_candidate(self):
        with TemporaryDirectory() as temporary:
            queue = Path(temporary) / "queue.json"
            queue.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-08-25T01:00:00+09:00",
                        "items": [
                            {
                                "post_id": 72,
                                "status": "REVIEW_REQUIRED",
                                "top_query": "석유 최고가격제 8차",
                                "baseline": {
                                    "clicks": 0,
                                    "impressions": 176,
                                    "position": 8.1,
                                },
                                "stop_rule": "14_days_or_1000_impressions",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            decision = parse_ctr_queue_decision(
                queue,
                post_id=72,
                proposed_title="새 제목",
                expected_date=date(2026, 8, 25),
            )

            self.assertEqual(decision["impressions"], 176)
            self.assertEqual(decision["top_query"], "석유 최고가격제 8차")

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

    def test_related_article_link_is_added_to_existing_section_idempotently(self):
        target = {
            "id": 10,
            "link": "https://huntlab.app/target/",
            "title": {"rendered": "관련 대상"},
        }
        original = (
            f"<p>{RELATED_LINK_MARKER}</p>\n"
            '<section class="huntlab-related-articles"><h2>함께 읽으면 좋은 글</h2>'
            "<ul><li>기존 링크</li></ul></section>"
        )

        updated = add_related_article_links(original, [target])

        self.assertIn("https://huntlab.app/target/", updated)
        self.assertEqual(add_related_article_links(updated, [target]), updated)


if __name__ == "__main__":
    unittest.main()
