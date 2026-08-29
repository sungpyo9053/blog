import json
import logging
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from publisher.config import ConfigurationError
from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient
from scripts.briefing_manifest import (
    _editorial_source_summary,
    atomic_write_manifest,
    build_briefing_manifest,
    collect_run_publications,
)
from scripts.run_daily_pipeline import PipelineError, write_and_sync_briefing_manifest


RUN_ID = "20260827T170000Z-1234567890"


def candidate(title: str, category: str) -> dict[str, object]:
    return {
        "title": title,
        "category": category,
        "primary_keyword": title.split()[0],
        "reason": f"{title}의 실제 생활 영향을 확인해야 합니다.",
        "reader_action": "공식 적용 시점을 다시 확인하세요.",
        "life_impact": "신청 조건과 지출 판단이 달라질 수 있습니다.",
        "effective_date": "2026-09-01",
        "selection_track": "public_signal",
        "google_trends_approx_traffic": 5_000,
        "whereispost_total_searches": 0,
        "sources": "https://www.gov.kr/a https://news.example.com/b?utm_source=x",
        "evidence_plan": "공식 원문과 독립 보도를 교차 확인",
    }


class BriefingManifestTests(unittest.TestCase):
    def test_editorial_source_summary_balances_all_reference_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "editorial.json"
            categories = [
                "AI/ML 핵심",
                "개발 트렌드",
                "AI 공식 블로그",
                "국내 IT",
                "국내 시사",
            ]
            rows = []
            for category_index, category in enumerate(reversed(categories)):
                for item_index in range(20):
                    rows.append(
                        {
                            "category": category,
                            "source": f"source-{category_index}",
                            "title": f"{category}-{item_index}",
                            "url": f"https://example.com/{category_index}/{item_index}",
                            "published_at": "2026-08-27T12:00:00+00:00",
                        }
                    )
            cache.write_text(
                json.dumps(
                    {
                        "provider": "hunt_news_editorial_sources",
                        "checked_at": "2026-08-27T12:00:00+00:00",
                        "successful_source_count": 5,
                        "source_count": 5,
                        "rows": rows,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            summary = _editorial_source_summary(cache)

            self.assertEqual(len(summary["items"]), 60)
            self.assertEqual(
                [item["category"] for item in summary["items"][:5]], categories
            )
            self.assertEqual(
                {item["category"] for item in summary["items"]}, set(categories)
            )

            preferred_url = "https://example.com/0/19"
            preferred = _editorial_source_summary(cache, preferred_urls={preferred_url})
            self.assertEqual(len(preferred["items"]), 60)
            self.assertIn(preferred_url, {item["url"] for item in preferred["items"]})

    def test_wordpress_client_uses_authenticated_custom_manifest_route(self):
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = b'{"stored":true}'
        response.__enter__.return_value = response
        with mock.patch("publisher.wordpress.urlopen", return_value=response) as urlopen:
            result = WordPressClient(
                WordPressConfig(
                    base_url="https://huntlab.app",
                    username="editor",
                    app_password="secret",
                )
            ).sync_briefing_manifest({"contract_version": "briefing-manifest.v1"})
        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://huntlab.app/?rest_route=/hunt-news/v1/briefing-run",
        )
        self.assertTrue(request.headers["Authorization"].startswith("Basic "))
        self.assertEqual(result, {"stored": True})

    def test_manifest_joins_observation_selection_and_verified_publications(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trends = root / "trends.json"
            shadow = root / "shadow.json"
            fallback = root / "fallback.json"
            trends.write_text(
                json.dumps(
                    {
                        "provider": "google_trends_kr_rss",
                        "checked_at": "2026-08-27T16:10:00+00:00",
                        "retention_hours": 48,
                        "rows": [
                            {
                                "topic": "정책 발표",
                                "approx_traffic": 10_000,
                                "last_seen_at": "2026-08-27T16:00:00+00:00",
                                "news_source_count": 3,
                            },
                            {
                                "topic": "생활 지원",
                                "approx_traffic": 5_000,
                                "last_seen_at": "2026-08-27T15:00:00+00:00",
                                "news_source_count": 2,
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            shadow.write_text(
                json.dumps(
                    {
                        "status": "success",
                        "shadow_top2": ["주제 B", "주제 A"],
                        "overlap_count": 2,
                        "source_snapshot_hash": "abc",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            fallback.write_text("{}", encoding="utf-8")
            plans = [candidate("주제 A", "생활"), candidate("주제 B", "경제")]
            payload = build_briefing_manifest(
                run_id=RUN_ID,
                plan_document={"candidates": plans, "top2": plans},
                publications=[
                    {
                        "topic_id": "topic-a",
                        "post_id": 11,
                        "url": "https://huntlab.app/a/",
                        "published_at": "2026-08-27T17:20:00+00:00",
                        "title": "주제 A",
                        "category": "생활",
                    },
                    {
                        "topic_id": "topic-b",
                        "post_id": 12,
                        "url": "https://huntlab.app/b/",
                        "published_at": "2026-08-27T17:21:00+00:00",
                        "title": "주제 B",
                        "category": "경제",
                    },
                ],
                trends_cache_path=trends,
                shadow_path=shadow,
                fallback_path=fallback,
                generated_at=datetime(2026, 8, 27, 17, 30, tzinfo=UTC),
            )

            self.assertFalse(payload["complete"])
            self.assertEqual(
                payload["completion"],
                {
                    "analysis_complete": False,
                    "publications_complete": True,
                    "published_count": 2,
                },
            )
            self.assertEqual(payload["collection"]["observed_topic_count"], 2)
            self.assertEqual(payload["collection"]["status"], "fresh")
            self.assertEqual(payload["collection"]["age_minutes"], 80)
            self.assertEqual(payload["selection"]["candidate_count"], 2)
            self.assertEqual(payload["selection"]["overlap_count"], 2)
            self.assertEqual(payload["published"][0]["source_count"], 2)
            self.assertEqual(
                payload["published"][0]["source_domains"],
                ["gov.kr", "news.example.com"],
            )
            self.assertEqual(len(payload["source_snapshot_hash"]), 64)

            destination = root / "briefing-manifest.json"
            atomic_write_manifest(destination, payload)
            self.assertEqual(json.loads(destination.read_text()), payload)

    def test_publication_collector_requires_success_audit_and_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            topic = run / "topic-a"
            topic.mkdir()
            (topic / "planner-context.json").write_text(
                json.dumps(
                    {
                        "run_id": RUN_ID,
                        "topic_id": "topic-a",
                        "title": "주제 A",
                        "category": "생활",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            events = [
                {"event": "validation", "status": "passed"},
                {
                    "event": "post_published",
                    "status": "Success",
                    "post_id": 11,
                    "published_url": "https://huntlab.app/a/",
                    "timestamp": "2026-08-27T17:20:00+00:00",
                },
            ]
            (topic / "publisher-audit.jsonl").write_text(
                "\n".join(json.dumps(item) for item in events) + "\n",
                encoding="utf-8",
            )
            rows = collect_run_publications(run)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["post_id"], 11)
            self.assertEqual(rows[0]["topic_id"], "topic-a")

    def test_wordpress_manifest_sync_failure_fails_required_report_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            plans = [candidate("주제 A", "생활"), candidate("주제 B", "경제")]
            for index, plan in enumerate(plans, start=1):
                topic = run / f"topic-{index}"
                topic.mkdir()
                (topic / "planner-context.json").write_text(
                    json.dumps(
                        {
                            "run_id": RUN_ID,
                            "topic_id": f"topic-{index}",
                            "title": plan["title"],
                            "category": plan["category"],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                (topic / "publisher-audit.jsonl").write_text(
                    json.dumps(
                        {
                            "event": "post_published",
                            "status": "Success",
                            "post_id": index,
                            "published_url": f"https://huntlab.app/{index}/",
                            "timestamp": f"2026-08-27T17:2{index}:00+00:00",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
            logger = logging.getLogger("briefing-manifest-test")
            complete_payload = {
                "complete": True,
                "completion": {
                    "analysis_complete": True,
                    "publications_complete": True,
                    "published_count": 2,
                },
                "published": [{"post_id": 1}, {"post_id": 2}],
            }
            with mock.patch(
                "scripts.run_daily_pipeline.build_briefing_manifest",
                return_value=complete_payload,
            ), mock.patch(
                "scripts.run_daily_pipeline.WordPressConfig.from_environment",
                side_effect=ConfigurationError("missing credentials"),
            ), self.assertRaises(PipelineError):
                write_and_sync_briefing_manifest(
                    run_id=RUN_ID,
                    run_directory=run,
                    plan_document={"candidates": plans, "top2": plans},
                    logger=logger,
                )
            artifact = run / "briefing-manifest.json"
            self.assertTrue(artifact.is_file())
            self.assertTrue(json.loads(artifact.read_text())["complete"])

    def test_incomplete_manifest_never_reaches_wordpress(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            payload = {
                "complete": False,
                "completion": {
                    "analysis_complete": False,
                    "publications_complete": True,
                    "published_count": 2,
                },
                "published": [{"post_id": 1}, {"post_id": 2}],
            }
            with mock.patch(
                "scripts.run_daily_pipeline.build_briefing_manifest",
                return_value=payload,
            ), mock.patch(
                "scripts.run_daily_pipeline.WordPressClient.sync_briefing_manifest"
            ) as sync, self.assertRaises(PipelineError):
                write_and_sync_briefing_manifest(
                    run_id=RUN_ID,
                    run_directory=run,
                    plan_document={},
                    logger=logging.getLogger("briefing-incomplete-test"),
                )
            sync.assert_not_called()

    def test_wordpress_must_confirm_manifest_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            payload = {
                "complete": True,
                "completion": {
                    "analysis_complete": True,
                    "publications_complete": True,
                    "published_count": 2,
                },
                "published": [{"post_id": 1}, {"post_id": 2}],
            }
            with mock.patch(
                "scripts.run_daily_pipeline.build_briefing_manifest",
                return_value=payload,
            ), mock.patch(
                "scripts.run_daily_pipeline.WordPressConfig.from_environment"
            ), mock.patch(
                "scripts.run_daily_pipeline.WordPressClient.sync_briefing_manifest",
                return_value={"stored": False},
            ), self.assertRaises(PipelineError):
                write_and_sync_briefing_manifest(
                    run_id=RUN_ID,
                    run_directory=run,
                    plan_document={},
                    logger=logging.getLogger("briefing-storage-test"),
                )


if __name__ == "__main__":
    unittest.main()
