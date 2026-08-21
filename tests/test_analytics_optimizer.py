from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.run_analytics_optimizer import (
    allocate_index_inspection_targets,
    aggregate_page_rows,
    analyze,
    aug7_review_decisions,
    build_ctr_experiment_queue,
    build_index_recovery_queue,
    known_query_breakdown,
    hunt_news_performance_funnel,
    measurement_warnings,
    mature_content_funnel,
    render,
    select_index_checkpoint_urls,
    select_mature_recovery_urls,
    update_index_checkpoint_state,
    write_reports,
)


class AnalyticsOptimizerTests(unittest.TestCase):
    def test_performance_funnel_preserves_zero_and_na_semantics(self):
        funnel = hunt_news_performance_funnel(
            {
                "search_period": {"start": "2026-08-13", "end": "2026-08-19"},
                "search_totals": {
                    "impressions": "0",
                    "clicks": "0",
                    "position": "0",
                },
                "search_queries": [],
                "ga4_events": [],
            }
        )

        self.assertEqual(funnel["impression"]["impressions"], 0)
        self.assertEqual(funnel["click"]["clicks"], 0)
        self.assertEqual(funnel["click"]["ctr"], 0)
        self.assertEqual(funnel["engagement"]["page_view"], 0)
        self.assertEqual(funnel["engagement"]["huntlab_engaged_read"], 0)
        self.assertIsNone(funnel["indexing"]["source"])
        self.assertIsNone(funnel["engagement"]["article_complete"])
        self.assertIsNone(funnel["engagement"]["share"])
        self.assertIsNone(funnel["engagement"]["return_visit"])
        self.assertIsNone(funnel["cross_source_conversion"])

    def test_performance_funnel_is_na_when_measurement_input_is_missing(self):
        funnel = hunt_news_performance_funnel({})

        self.assertIsNone(funnel["impression"]["impressions"])
        self.assertIsNone(funnel["click"]["clicks"])
        self.assertIsNone(funnel["engagement"]["page_view"])

    def test_render_keeps_public_audit_independent(self):
        body = render([], [], datetime(2026, 8, 3, tzinfo=timezone.utc))
        self.assertIn("Analytics Optimization Report", body)
        self.assertNotIn("Public Site Quality Audit", body)
        self.assertIn("| INDEXING | N/A | N/A | Technical SEO |", body)
        self.assertIn("page_view=N/A", body)
        self.assertIn("cross_source_conversion: `N/A`", body)

    def test_aug7_review_selects_one_title_and_one_discovery_action(self):
        decision = aug7_review_decisions(
            [
                {
                    "page": "/resident-registration-survey/",
                    "clicks": 0,
                    "impressions": 38,
                    "position": 11.4,
                }
            ],
            [
                {
                    "url": "https://huntlab.app/unindexed/",
                    "status": "COMPLETE",
                    "verdict": "FAIL",
                    "coverage_state": "Discovered - currently not indexed",
                },
                {
                    "url": "https://huntlab.app/also-unindexed/",
                    "status": "COMPLETE",
                    "verdict": "FAIL",
                },
            ],
            datetime(2026, 8, 7, 1, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(
            decision["title_experiment"]["status"], "ELIGIBLE_REVIEW"
        )
        self.assertEqual(
            decision["title_experiment"]["single_change"], "title_only"
        )
        self.assertEqual(
            decision["index_discovery"]["target_url"],
            "https://huntlab.app/unindexed/",
        )
        self.assertEqual(
            decision["index_discovery"]["single_change"],
            "one_relevant_internal_link",
        )

    def test_aug7_review_waits_before_review_date(self):
        decision = aug7_review_decisions(
            [],
            [],
            datetime(2026, 8, 6, 1, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(decision["title_experiment"]["status"], "SCHEDULED")
        self.assertEqual(decision["index_discovery"]["status"], "SCHEDULED")

    def test_analyze_returns_refresh_and_gap_candidates(self):
        rows = [
            {
                "keys": ["대표 검색어", "https://huntlab.app/post/"],
                "clicks": 0,
                "impressions": 80,
                "ctr": 0,
                "position": 12,
            }
        ]

        refresh, gaps = analyze(rows)

        self.assertEqual(refresh[0]["reason"], "high_impressions_low_ctr")
        self.assertEqual(gaps[0]["reason"], "visible_query_without_clicks")

    def test_analyze_ignores_small_samples(self):
        refresh, gaps = analyze(
            [
                {
                    "keys": ["작은 표본", "https://huntlab.app/small/"],
                    "clicks": 0,
                    "impressions": 10,
                    "ctr": 0,
                    "position": 30,
                }
            ]
        )
        self.assertEqual(refresh, [])
        self.assertEqual(gaps, [])

    def test_aggregate_page_rows_collapses_protocol_www_and_query(self):
        rows = [
            {
                "keys": ["http://www.huntlab.app/post/?utm_source=rss"],
                "clicks": 0,
                "impressions": 3,
                "position": 12,
            },
            {
                "keys": ["https://huntlab.app/post/"],
                "clicks": 1,
                "impressions": 2,
                "position": 6,
            },
        ]

        aggregated = aggregate_page_rows(rows)

        self.assertEqual(len(aggregated), 1)
        self.assertEqual(aggregated[0]["page"], "/post/")
        self.assertEqual(aggregated[0]["clicks"], 1)
        self.assertEqual(aggregated[0]["impressions"], 5)
        self.assertAlmostEqual(aggregated[0]["position"], 9.6)

    def test_query_breakdown_keeps_privacy_hidden_clicks_separate(self):
        diagnostics = {
            "search_totals": {"clicks": 10, "impressions": 50},
            "search_queries": [
                {"keys": ["huntlab"], "clicks": 4, "impressions": 5},
                {"keys": ["fastapi timeout"], "clicks": 2, "impressions": 10},
            ],
        }

        breakdown = known_query_breakdown(diagnostics)

        self.assertEqual(breakdown["known_brand_clicks"], 4)
        self.assertEqual(breakdown["known_nonbrand_clicks"], 2)
        self.assertEqual(breakdown["privacy_hidden_clicks"], 4)

    def test_measurement_warnings_detect_inconsistent_ga4_data(self):
        diagnostics = {
            "ga4_summary": {
                "yesterday": {"screenPageViews": "20", "engagedSessions": "0"},
                "last7days": {"sessions": "10", "screenPageViews": "100"},
            },
            "ga4_channels": [{"sessions": "14"}],
        }
        ga_rows = [{"page": "/", "screenPageViews": "60"}]

        warnings = measurement_warnings(diagnostics, ga_rows)

        self.assertEqual(len(warnings), 3)

    def test_render_records_early_candidates_without_auto_refresh(self):
        diagnostics = {
            "search_period": {"start": "2026-07-28", "end": "2026-08-03"},
            "search_totals": {"clicks": 1, "impressions": 8},
            "search_queries": [],
            "search_pages": [
                {
                    "keys": ["https://huntlab.app/observed-post/"],
                    "clicks": 0,
                    "impressions": 8,
                    "position": 9,
                }
            ],
            "ga4_summary": {},
            "ga4_channels": [],
        }
        site_audit = {
            "counts": {"post": 2},
            "pages": [
                {
                    "url": "https://huntlab.app/observed-post/",
                    "status": 200,
                    "published_at": "2026-07-30T02:00:00+09:00",
                },
                {
                    "url": "https://huntlab.app/fresh-post/",
                    "status": 200,
                    "published_at": "2026-08-03T02:00:00+09:00",
                },
            ],
        }

        body = render(
            [],
            [],
            datetime(2026, 8, 5, tzinfo=timezone.utc),
            diagnostics=diagnostics,
            site_audit=site_audit,
            public_post_metadata=[
                {
                    "link": "https://huntlab.app/observed-post/",
                    "date": "2026-07-30T02:00:00",
                    "status": "publish",
                },
                {
                    "link": "https://huntlab.app/fresh-post/",
                    "date": "2026-08-03T02:00:00",
                    "status": "publish",
                },
            ],
        )

        self.assertIn("mature_posts_eligible: `1`", body)
        self.assertIn("mature_posts_with_search_impressions: `1`", body)
        self.assertIn("mature_posts_without_observed_impressions: `0`", body)
        self.assertIn("fresh_posts_excluded: `1`", body)
        self.assertIn("`/observed-post/`", body)
        self.assertIn("disabled_review_required", body)
        self.assertIn("자동 Refresh 금지", body)
        self.assertIn("8월 7일 운영 결정", body)
        self.assertIn("Naver·Whereispost Shadow Mode", body)

    def test_mature_content_funnel_excludes_fresh_posts(self):
        rows = [
            {"page": "/old/", "clicks": 1, "impressions": 5},
            {"page": "/fresh/", "clicks": 0, "impressions": 0},
        ]
        public_posts = [
            {
                "link": "https://huntlab.app/old/",
                "status": "publish",
                "date": "2026-08-01T02:00:00",
            },
            {
                "link": "https://huntlab.app/old-unseen/",
                "status": "publish",
                "date": "2026-07-31T02:00:00",
            },
            {
                "link": "https://huntlab.app/fresh/",
                "status": "publish",
                "date": "2026-08-03T02:00:00",
            },
        ]

        funnel = mature_content_funnel(
            rows,
            public_posts,
            {"start": "2026-07-29", "end": "2026-08-04"},
        )

        self.assertEqual(funnel["eligible"], 2)
        self.assertEqual(funnel["observed"], 1)
        self.assertEqual(funnel["clicked"], 1)
        self.assertEqual(funnel["without_impressions"], ["/old-unseen/"])
        self.assertEqual(funnel["fresh"], 1)

        body = render(
            [],
            [],
            datetime(2026, 8, 5, tzinfo=timezone.utc),
            diagnostics={
                "search_period": {"start": "2026-07-29", "end": "2026-08-04"},
                "search_pages": rows,
            },
            site_audit={"counts": {"post": 3}},
            public_post_metadata=public_posts,
        )
        self.assertIn("검색 노출 미관측 성숙 글", body)
        self.assertIn("`/old-unseen/`", body)

    def test_write_reports_keeps_latest_and_dated_snapshot(self):
        with TemporaryDirectory() as temporary:
            report_dir = Path(temporary)
            now = datetime(2026, 7, 31, 1, 0, tzinfo=timezone.utc)

            latest, dated = write_reports("daily report\n", now, report_dir)

            self.assertEqual(latest, report_dir / "latest.md")
            self.assertEqual(dated, report_dir / "2026-07-31.md")
            self.assertEqual(latest.read_text(encoding="utf-8"), "daily report\n")
            self.assertEqual(dated.read_text(encoding="utf-8"), "daily report\n")
            self.assertEqual(list(report_dir.glob(".*.tmp")), [])

    def test_fresh_posts_get_24h_72h_then_7d_index_checkpoints(self):
        now = datetime(2026, 8, 19, 1, 0, tzinfo=timezone.utc)
        posts = [
            {
                "link": "https://huntlab.app/new/",
                "status": "publish",
                "date": "2026-08-17T13:00:00+00:00",
            }
        ]

        first = select_index_checkpoint_urls(posts, {}, now)
        self.assertEqual(first[0]["checkpoint"], "24h")
        state = update_index_checkpoint_state(
            {},
            first,
            [{"url": first[0]["url"], "status": "COMPLETE", "verdict": "FAIL"}],
            now,
        )
        self.assertIn("24h", state["urls"][first[0]["url"]]["checkpoints"])

        later = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
        second = select_index_checkpoint_urls(posts, state, later)
        self.assertEqual(second[0]["checkpoint"], "72h")
        state = update_index_checkpoint_state(
            state,
            second,
            [{"url": second[0]["url"], "status": "COMPLETE", "verdict": "FAIL"}],
            later,
        )
        week_later = datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)
        third = select_index_checkpoint_urls(posts, state, week_later)
        self.assertEqual(third[0]["checkpoint"], "7d")

    def test_mature_recovery_rotates_and_persists_full_inspection(self):
        now = datetime(2026, 8, 20, 1, 0, tzinfo=timezone.utc)
        urls = [f"https://huntlab.app/post-{index}/" for index in range(12)]
        first = select_mature_recovery_urls(urls, {}, now, limit=10)
        self.assertEqual(len(first), 10)
        state = update_index_checkpoint_state(
            {},
            [],
            [
                {
                    "url": url,
                    "status": "COMPLETE",
                    "verdict": "NEUTRAL",
                    "coverage_state": "Discovered - currently not indexed",
                    "indexing_state": "INDEXING_ALLOWED",
                    "sitemaps": ["https://huntlab.app/post-sitemap.xml"],
                }
                for url in first
            ],
            now,
            recovery_urls=first,
        )

        second = select_mature_recovery_urls(
            urls, state, now + timedelta(days=1), limit=10
        )
        self.assertEqual(second, urls[10:])
        snapshot = state["urls"][first[0]]["latest"]
        self.assertEqual(snapshot["indexing_state"], "INDEXING_ALLOWED")
        self.assertEqual(snapshot["sitemaps"], ["https://huntlab.app/post-sitemap.xml"])

    def test_index_inspection_reserves_six_fresh_and_four_recovery_slots(self):
        now = datetime(2026, 8, 20, 1, 0, tzinfo=timezone.utc)
        posts = [
            {
                "link": f"https://huntlab.app/fresh-{index}/",
                "status": "publish",
                "date": "2026-08-18T13:00:00+00:00",
            }
            for index in range(10)
        ]
        mature_urls = [
            f"https://huntlab.app/mature-{index}/" for index in range(10)
        ]

        fresh, recovery = allocate_index_inspection_targets(
            posts, mature_urls, {}, now
        )

        self.assertEqual(len(fresh), 6)
        self.assertEqual(len(recovery), 4)
        self.assertEqual(len({item["url"] for item in fresh} | set(recovery)), 10)

    def test_index_inspection_fills_unused_fresh_slots_with_recovery(self):
        now = datetime(2026, 8, 20, 1, 0, tzinfo=timezone.utc)
        posts = [
            {
                "link": f"https://huntlab.app/fresh-{index}/",
                "status": "publish",
                "date": "2026-08-18T13:00:00+00:00",
            }
            for index in range(2)
        ]
        mature_urls = [
            f"https://huntlab.app/mature-{index}/" for index in range(10)
        ]

        fresh, recovery = allocate_index_inspection_targets(
            posts, mature_urls, {}, now
        )

        self.assertEqual(len(fresh), 2)
        self.assertEqual(len(recovery), 8)

    def test_index_recovery_queue_uses_observed_related_sources_only(self):
        now = datetime(2026, 8, 20, 1, 0, tzinfo=timezone.utc)
        posts = [
            {
                "id": 1,
                "link": "https://huntlab.app/target/",
                "title": {"rendered": "대상"},
                "status": "publish",
                "date": "2026-08-01T02:00:00",
                "categories": [3],
                "tags": [7],
            },
            {
                "id": 2,
                "link": "https://huntlab.app/source/",
                "title": {"rendered": "관련 출처"},
                "status": "publish",
                "date": "2026-08-02T02:00:00",
                "categories": [3],
                "tags": [7],
            },
            {
                "id": 3,
                "link": "https://huntlab.app/unrelated/",
                "title": {"rendered": "무관"},
                "status": "publish",
                "date": "2026-08-03T02:00:00",
                "categories": [9],
                "tags": [10],
            },
        ]

        queue = build_index_recovery_queue(
            posts,
            ["/target/"],
            [{"page": "/source/", "clicks": 1, "impressions": 40}],
            {},
            now,
        )

        self.assertEqual(queue["status"], "REVIEW_REQUIRED")
        self.assertFalse(queue["automatic_content_mutation"])
        self.assertEqual(queue["items"][0]["recommended_sources"][0]["post_id"], 2)

    def test_ctr_queue_requires_enough_impressions_and_actionable_position(self):
        now = datetime(2026, 8, 20, 1, 0, tzinfo=timezone.utc)
        queue = build_ctr_experiment_queue(
            [
                {
                    "keys": ["핵심 검색어", "https://huntlab.app/candidate/"],
                    "impressions": 35,
                }
            ],
            [
                {
                    "page": "/candidate/",
                    "clicks": 0,
                    "impressions": 40,
                    "ctr": 0,
                    "position": 11,
                },
                {
                    "page": "/too-low/",
                    "clicks": 0,
                    "impressions": 5,
                    "ctr": 0,
                    "position": 11,
                },
            ],
            [
                {
                    "id": 4,
                    "link": "https://huntlab.app/candidate/",
                    "title": {"rendered": "후보"},
                    "status": "publish",
                }
            ],
            now,
        )

        self.assertEqual(len(queue["items"]), 1)
        self.assertEqual(queue["items"][0]["top_query"], "핵심 검색어")
        self.assertEqual(queue["items"][0]["change_contract"], "title_or_meta_one_at_a_time")

    def test_render_reports_read_to_internal_click_funnel_and_queues(self):
        body = render(
            [],
            [],
            datetime(2026, 8, 20, 1, 0, tzinfo=timezone.utc),
            diagnostics={
                "ga4_events": [
                    {"eventName": "page_view", "eventCount": "20"},
                    {"eventName": "huntlab_engaged_read", "eventCount": "5"},
                    {"eventName": "huntlab_internal_click", "eventCount": "2"},
                ]
            },
            index_checkpoints=[{"url": "https://huntlab.app/fresh/", "checkpoint": "24h"}],
            index_recovery_urls=["https://huntlab.app/mature/"],
            index_recovery_queue={"items": [{"target_url": "https://huntlab.app/mature/", "recommended_sources": [{}]}]},
            ctr_experiment_queue={"items": [{"url": "https://huntlab.app/candidate/", "top_query": "검색어", "baseline": {"impressions": 40, "ctr": 0.01, "position": 9}}]},
        )

        self.assertIn("yesterday_engaged_read_per_page_view: `25.0%`", body)
        self.assertIn("yesterday_internal_click_per_engaged_read: `40.0%`", body)
        self.assertIn("page_view=20, engaged_read=5, internal_click=2", body)
        self.assertIn("article_complete=N/A, share=N/A, return_visit=N/A", body)
        self.assertIn("GA4의 page_view→engaged_read 사이에는 전환율을 계산하지 않는다", body)
        self.assertIn("inspection_slot_allocation: `fresh=1, mature_recovery=1`", body)
        self.assertIn("색인 회복 내부링크 검토 큐", body)
        self.assertIn("CTR 단일변수 실험 검토 큐", body)

    def test_measurement_warning_distinguishes_tag_collection_from_session_classification(self):
        warnings = measurement_warnings(
            {
                "ga4_summary": {
                    "yesterday": {
                        "screenPageViews": "17",
                        "engagedSessions": "0",
                        "userEngagementDuration": "425",
                    },
                    "last7days": {},
                },
                "ga4_events": [{"eventName": "user_engagement", "eventCount": "16"}],
            },
            [],
        )

        self.assertIn("태그 누락보다", warnings[0])
        self.assertIn("huntlab_engaged_read", warnings[0])

    def test_incomplete_checkpoint_is_retried(self):
        now = datetime(2026, 8, 19, 1, 0, tzinfo=timezone.utc)
        posts = [
            {
                "link": "https://huntlab.app/new/",
                "status": "publish",
                "date": "2026-08-18T00:00:00+00:00",
            }
        ]
        selected = select_index_checkpoint_urls(posts, {}, now)
        state = update_index_checkpoint_state(
            {},
            selected,
            [{"url": selected[0]["url"], "status": "INCOMPLETE"}],
            now,
        )
        self.assertEqual(select_index_checkpoint_urls(posts, state, now), selected)


if __name__ == "__main__":
    unittest.main()
