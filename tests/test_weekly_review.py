import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scripts.run_daily_pipeline import PipelineError
from scripts.run_weekly_review import (
    PLAN_VERSION,
    WEEKLY_CATEGORY,
    collect_weekly_input,
    validate_weekly_input,
    validate_weekly_plan,
    week_bounds,
)


def daily_payload(day: date) -> dict:
    evidence = [f"https://example.com/{day.isoformat()}/evidence"]
    categories = ("AI/ML 핵심", "개발 트렌드", "AI 공식 블로그", "국내 IT", "국내 시사")
    return {
        "contract_version": "daily-briefing-analysis.v1",
        "generated_at": f"{day.isoformat()}T10:00:00+09:00",
        "source_snapshot_hash": "a" * 64,
        "headline": f"{day.isoformat()} 기술 변화",
        "summary": "개발자의 결정이 달라지는 변화를 근거로 정리했다.",
        "retrospective": {"status": "baseline", "previous_generated_at": "", "previous_snapshot_hash": "", "items": []},
        "core_signals": [
            {"metric": str(index), "label": f"신호 {index}", "detail": "변화 설명", "action": "확인한다", "tone": tone, "evidence_urls": evidence}
            for index, tone in enumerate(("green", "amber", "red"), 1)
        ],
        "keywords": [
            {"keyword": f"키워드 {index}", "score": 10 - index, "direction": "stable", "basis": "반복 관측"}
            for index in range(7)
        ],
        "matrix": [
            {"quadrant": quadrant, "label": quadrant, "meaning": "영향", "action": "확인", "evidence_urls": evidence}
            for quadrant in ("focus", "future", "apply", "watch")
        ],
        "timeline": [
            {"horizon": horizon, "action": "실행", "reason": "이유", "evidence_urls": evidence}
            for horizon in ("today", "week", "month", "year")
        ],
        "insight_cards": [
            {"title": f"인사이트 {index}", "analysis": "분석", "action": "확인", "evidence_urls": evidence}
            for index in range(3)
        ],
        "themes": [
            {"title": f"테마 {index}", "analysis": "분석", "action": "확인", "evidence_urls": evidence}
            for index in range(3)
        ],
        "developer_insights": [
            {"title": f"개발자 {index}", "analysis": "영향", "action": "확인", "evidence_urls": evidence}
            for index in range(3)
        ],
        "watchlist": [
            {"title": f"주시 {index}", "reason": "후속 발표", "trigger": "공식 발표", "evidence_urls": evidence}
            for index in range(2)
        ],
        "source_title_translations": [],
        "must_read": [
            {"title": category, "korean_title": "", "category": category, "source": "공식", "source_url": f"https://example.com/{day.isoformat()}/{index}", "why_it_matters": "선택 변화", "action": "확인"}
            for index, category in enumerate(categories)
        ],
    }


def weekly_plan(payload: dict) -> dict:
    evidence = payload["evidence_urls"][:5]
    return {
        "contract_version": PLAN_VERSION,
        "week_start": payload["week_start"],
        "week_end": payload["week_end"],
        "source_snapshot_hash": payload["source_snapshot_hash"],
        "title": "AI 개발 기술 주간 회고: 권한과 평가가 배포 기준이 된 한 주",
        "category": WEEKLY_CATEGORY,
        "content_type": "concept_architecture",
        "tags": ["주간 회고", "AI 개발", "기술 동향"],
        "primary_keyword": "AI 개발 기술 주간 회고",
        "secondary_keywords": "에이전트 보안, 평가",
        "target_reader": "AI 개발자와 기술 리더",
        "reason": "반복 관측된 변화를 주간 의사결정으로 합친다.",
        "search_intent": "이번 주 AI 개발 변화와 다음 행동 파악",
        "research_focus": "반복 신호와 변화, 다음 주 확인 조건",
        "demand_signal_source": "일일 브리핑 7일 스냅샷과 지연된 Search Console 보조 신호",
        "observed_problem_phrase": "매일 뉴스를 읽어도 한 주의 방향이 남지 않는다",
        "user_action": "다음 주 점검 항목을 정한다",
        "original_value_plan": "일별 사건을 변화 축으로 다시 묶는다",
        "evidence_plan": "각 변화마다 공식 원문과 날짜를 연결한다",
        "duplicate_check": "같은 주차의 주간 회고 없음",
        "internal_link_candidates": "해당 주 일일 브리핑",
        "topic_cluster": "주간 기술 회고",
        "pillar_candidate": "AI 개발 변화 아카이브",
        "problem_origin": "official_change",
        "editorial_thesis": "이번 주에는 모델보다 권한과 평가가 배포 기준을 바꿨다",
        "chosen_focus": "반복 신호와 개발자 결정",
        "rejected_angle": "기사별 단순 나열은 제외",
        "structure_mode": "impact_timeline",
        "recommended_images": "주간 변화 타임라인 1개",
        "sources": "\n".join(evidence),
        "evidence_urls": evidence,
    }


class WeeklyReviewTests(unittest.TestCase):
    def test_week_bounds_are_monday_to_sunday(self):
        self.assertEqual(week_bounds(date(2026, 8, 30)), (date(2026, 8, 24), date(2026, 8, 30)))

    def test_collects_latest_valid_briefing_per_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp)
            start = date(2026, 8, 24)
            for index in range(7):
                directory = runs / f"run-{index}"
                directory.mkdir()
                (directory / "daily-briefing-analysis.json").write_text(
                    json.dumps(daily_payload(start + timedelta(days=index)), ensure_ascii=False),
                    encoding="utf-8",
                )
            payload = collect_weekly_input(
                runs,
                week_start=start,
                week_end=start + timedelta(days=6),
                generated_at=datetime(2026, 8, 30, 20, 30, tzinfo=timezone(timedelta(hours=9))),
            )
            validate_weekly_input(payload)
            self.assertEqual(payload["daily_briefing_count"], 7)
            self.assertEqual(len(payload["source_snapshot_hash"]), 64)
            self.assertGreaterEqual(len(payload["evidence_urls"]), 5)

            replay = collect_weekly_input(
                runs,
                week_start=start,
                week_end=start + timedelta(days=6),
                generated_at=datetime(2026, 8, 30, 21, 30, tzinfo=timezone(timedelta(hours=9))),
            )
            self.assertNotEqual(payload["generated_at"], replay["generated_at"])
            self.assertEqual(payload["source_snapshot_hash"], replay["source_snapshot_hash"])

    def test_input_fails_closed_below_five_days(self):
        payload = {"contract_version": "weekly-review-input.v1", "daily_briefing_count": 4, "evidence_urls": [f"https://e/{i}" for i in range(5)]}
        with self.assertRaises(PipelineError):
            validate_weekly_input(payload)

    def test_plan_keeps_separate_category_and_snapshot_evidence(self):
        payload = {
            "week_start": "2026-08-24",
            "week_end": "2026-08-30",
            "source_snapshot_hash": "b" * 64,
            "evidence_urls": [f"https://example.com/{i}" for i in range(6)],
        }
        plan = weekly_plan(payload)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "weekly-plan.json"
            path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            validated = validate_weekly_plan(
                path,
                input_payload=payload,
                week_start=date(2026, 8, 24),
                week_end=date(2026, 8, 30),
            )
            self.assertEqual(validated["category"], "주간 기술 회고")

            plan["evidence_urls"][0] = "https://outside.example/evidence"
            path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(PipelineError):
                validate_weekly_plan(
                    path,
                    input_payload=payload,
                    week_start=date(2026, 8, 24),
                    week_end=date(2026, 8, 30),
                )

    def test_systemd_runs_sunday_evening_without_catchup(self):
        root = Path(__file__).resolve().parents[1]
        timer = (root / "deploy/huntlab-weekly-review.timer").read_text(encoding="utf-8")
        service = (root / "deploy/huntlab-weekly-review.service").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=Sun *-*-* 20:30:00 Asia/Seoul", timer)
        self.assertIn("Persistent=false", timer)
        self.assertIn("scripts/run_weekly_review.py", service)

    def test_script_can_be_executed_by_file_path(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "scripts/run_weekly_review.py"), "--help"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("weekly", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
