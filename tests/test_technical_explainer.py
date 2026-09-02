import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scripts.run_daily_pipeline import PipelineError
from scripts.run_technical_explainer import (
    EXPLAINER_CATEGORY,
    INPUT_VERSION,
    PLAN_VERSION,
    collect_explainer_input,
    validate_explainer_input,
    validate_explainer_plan,
)


def daily_payload(day: date) -> dict:
    evidence = [f"https://example.com/{day.isoformat()}/evidence"]
    return {
        "contract_version": "daily-briefing-analysis.v2",
        "generated_at": f"{day.isoformat()}T10:00:00+09:00",
        "source_snapshot_hash": "a" * 64,
        "headline": f"{day.isoformat()} 검색 엔진 변경",
        "summary": "검색 엔진의 색인 방식이 달라졌다.",
        "retrospective": {"status": "baseline", "previous_generated_at": "", "previous_snapshot_hash": "", "items": []},
        "core_signals": [{"metric": "1", "label": "색인", "detail": "변경", "action": "", "tone": "green", "evidence_urls": evidence, "event_key": "search-index", "continuity": "new", "change_basis": "공식 변경"}],
        "keywords": [{"keyword": "검색 엔진 색인", "score": 9, "direction": "up", "basis": "반복 관측"}] * 3,
        "matrix": [],
        "timeline": [{"horizon": "week", "action": "", "reason": "배포 확인", "evidence_urls": evidence}],
        "insight_cards": [{"title": "색인 판단", "analysis": "가" * 420, "action": "", "evidence_urls": evidence}],
        "themes": [],
        "developer_insights": [{"title": "설정", "analysis": "설정 예시를 확인한다.", "action": "", "evidence_urls": evidence}],
        "watchlist": [],
        "source_title_translations": [],
        "must_read": [
            {"title": f"Search indexing changed {index}", "korean_title": f"검색 색인 방식 변경 {index}", "category": category, "source": "DEV.to", "source_url": f"https://example.com/source/{index}", "why_it_matters": "설정 예시를 제공한다", "action": ""}
            for index, category in enumerate(("AI/ML 핵심", "개발 트렌드", "AI 공식 블로그"), 1)
        ],
    }


def plan(payload: dict, run_date: date) -> dict:
    evidence = payload["evidence_urls"][:2]
    return {
        "contract_version": PLAN_VERSION,
        "run_date": run_date.isoformat(),
        "source_snapshot_hash": payload["source_snapshot_hash"],
        "title": "검색 엔진 색인 변경을 설정 예제로 확인하는 방법",
        "category": EXPLAINER_CATEGORY,
        "content_type": "tutorial_troubleshooting",
        "structure_mode": "problem_first",
        "tags": ["검색 엔진", "색인", "개발 도구"],
        "primary_keyword": "검색 엔진 색인 변경",
        "secondary_keywords": "색인 설정, 검색 테스트",
        "target_reader": "검색 기능을 운영하는 개발자",
        "reason": "실제 검색 수요와 공식 변경이 함께 관측됐다.",
        "search_intent": "변경된 색인 설정과 실패 조건 확인",
        "research_focus": "변경 전후 설정과 재현 절차",
        "demand_signal_source": "google_trends",
        "demand_signal_basis": "최근 캐시에서 검색 엔진 색인 검색량 관측",
        "candidate_source_url": payload["candidate_source_urls"][0],
        "reader_outcome": "자신의 환경에서 설정 적용 여부를 결정한다.",
        "hands_on_example": "최소 설정과 정상·실패 출력을 비교한다.",
        "failure_or_limit": "지원 버전 밖에서는 적용하지 않는다.",
        "verification_mode": "controlled_comparison",
        "original_artifact": "변경 전후 설정 diff와 실행 판정표",
        "counterexample": "구버전 런타임에서는 동일 설정이 동작하지 않는다.",
        "original_value_plan": "원문 두 개의 설정 차이를 실행 순서로 대조한다.",
        "evidence_plan": "공식 변경과 독립 예시를 구분한다.",
        "duplicate_check": "같은 검색 의도의 기존 글 없음",
        "internal_link_candidates": "해당 날짜 브리핑",
        "topic_cluster": "검색 인프라",
        "pillar_candidate": "개발자 검색 운영 가이드",
        "problem_origin": "official_change",
        "editorial_thesis": "색인 변경은 설정 한 줄보다 실패 복구 방식에 영향을 준다.",
        "chosen_focus": "설정 전후와 실패 판정",
        "rejected_angle": "전체 검색 엔진 역사",
        "recommended_images": "설정 전후 흐름도",
        "sources": "\n".join(evidence),
        "evidence_urls": evidence,
    }


def trends_payload(checked_at: str) -> dict:
    return {
        "contract_version": "google-trends-cache.v2",
        "provider": "google_trends_kr_rss",
        "geo": "KR",
        "checked_at": checked_at,
        "source_snapshot_hash": "c" * 64,
        "rows": [{
            "topic": "검색 엔진 색인 변경",
            "normalized_topic": "검색 엔진 색인 변경",
            "approx_traffic": 1000,
            "published_at": checked_at,
            "first_seen_at": checked_at,
            "last_seen_at": checked_at,
            "news_items": [],
            "discovery_score": 1.0,
            "observation_count": 1,
        }],
    }


class TechnicalExplainerTests(unittest.TestCase):
    def test_collects_recent_briefings_and_observed_demand(self):
        run_date = date(2026, 9, 2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "runs"
            for offset in range(3):
                day = run_date - timedelta(days=offset)
                target = runs / day.isoformat()
                target.mkdir(parents=True)
                (target / "daily-briefing-analysis.json").write_text(json.dumps(daily_payload(day), ensure_ascii=False), encoding="utf-8")
            trends = root / "trends.json"
            trends.write_text(json.dumps(trends_payload("2026-09-02T09:00:00+09:00")), encoding="utf-8")
            analytics = root / "latest.md"
            analytics.write_text("- generated_at: `2026-09-02T09:30:00+09:00`\n\n## Search Console 유입\n| 검색어 | 페이지 |\n| 색인 | / |", encoding="utf-8")

            payload = collect_explainer_input(runs, run_date=run_date, generated_at=datetime(2026, 9, 2, tzinfo=timezone.utc), trends_path=trends, analytics_path=analytics)

            validate_explainer_input(payload)
            self.assertEqual(payload["contract_version"], INPUT_VERSION)
            self.assertEqual(payload["daily_briefing_count"], 3)
            self.assertEqual(len(payload["candidate_source_urls"]), 3)
            self.assertTrue(payload["demand_signals"]["google_trends"])

    def test_stale_observations_are_not_treated_as_current_demand(self):
        run_date = date(2026, 9, 2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "runs"
            for offset in range(3):
                day = run_date - timedelta(days=offset)
                target = runs / day.isoformat()
                target.mkdir(parents=True)
                (target / "daily-briefing-analysis.json").write_text(
                    json.dumps(daily_payload(day), ensure_ascii=False), encoding="utf-8"
                )
            trends = root / "trends.json"
            trends.write_text(
                json.dumps(trends_payload("2026-08-31T09:00:00+09:00")), encoding="utf-8"
            )
            analytics = root / "latest.md"
            analytics.write_text(
                "- generated_at: `2026-08-01T09:30:00+09:00`\n\n"
                "## Search Console 유입\n| 검색어 | 페이지 |\n| 색인 | / |",
                encoding="utf-8",
            )

            payload = collect_explainer_input(
                runs,
                run_date=run_date,
                generated_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
                trends_path=trends,
                analytics_path=analytics,
            )

            with self.assertRaisesRegex(PipelineError, "검색 수요"):
                validate_explainer_input(payload)

    def test_input_fails_closed_without_observed_demand(self):
        payload = {"contract_version": INPUT_VERSION, "daily_briefing_count": 3, "evidence_urls": ["https://e/1", "https://e/2"], "demand_signals": {"google_trends": [], "search_console_excerpt": ""}}
        with self.assertRaisesRegex(PipelineError, "검색 수요"):
            validate_explainer_input(payload)

    def test_plan_requires_category_demand_and_snapshot_evidence(self):
        run_date = date(2026, 9, 2)
        payload = {"source_snapshot_hash": "b" * 64, "candidate_source_urls": ["https://example.com/source"], "evidence_urls": ["https://example.com/source", "https://example.com/evidence"], "demand_signals": {"google_trends": [{"query": "검색 엔진 색인 변경"}], "search_console_excerpt": ""}}
        document = plan(payload, run_date)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "technical-explainer-plan.json"
            path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            validated = validate_explainer_plan(path, input_payload=payload, run_date=run_date)
            self.assertEqual(validated["category"], EXPLAINER_CATEGORY)
            document["evidence_urls"][0] = "https://outside.example/evidence"
            path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(PipelineError, "스냅샷 밖"):
                validate_explainer_plan(path, input_payload=payload, run_date=run_date)

    def test_plan_rejects_keyword_unrelated_to_observed_demand(self):
        run_date = date(2026, 9, 2)
        payload = {"source_snapshot_hash": "b" * 64, "candidate_source_urls": ["https://example.com/source"], "evidence_urls": ["https://example.com/source", "https://example.com/evidence"], "demand_signals": {"google_trends": [{"query": "파이썬 비동기"}], "search_console_excerpt": ""}}
        document = plan(payload, run_date)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "technical-explainer-plan.json"
            path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(PipelineError, "연결되지"):
                validate_explainer_plan(path, input_payload=payload, run_date=run_date)

    def test_systemd_runs_twice_weekly_without_catchup(self):
        root = Path(__file__).resolve().parents[1]
        timer = (root / "deploy/huntlab-technical-explainer.timer").read_text(encoding="utf-8")
        service = (root / "deploy/huntlab-technical-explainer.service").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=Wed,Sat *-*-* 20:30:00 Asia/Seoul", timer)
        self.assertIn("Persistent=false", timer)
        self.assertIn("scripts/run_technical_explainer.py", service)

    def test_script_can_be_executed_by_file_path(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / "scripts/run_technical_explainer.py"), "--help"], cwd=root, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("explainer", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
