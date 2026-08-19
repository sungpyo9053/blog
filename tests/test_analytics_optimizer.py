from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.run_analytics_optimizer import (
    aggregate_page_rows,
    analyze,
    aug7_review_decisions,
    known_query_breakdown,
    measurement_warnings,
    mature_content_funnel,
    render,
    select_index_checkpoint_urls,
    update_index_checkpoint_state,
    write_reports,
)


class AnalyticsOptimizerTests(unittest.TestCase):
    def test_render_keeps_public_audit_independent(self):
        body = render([], [], datetime(2026, 8, 3, tzinfo=timezone.utc))
        self.assertIn("Analytics Optimization Report", body)
        self.assertNotIn("Public Site Quality Audit", body)

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

    def test_fresh_posts_get_24h_then_72h_index_checkpoints(self):
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
