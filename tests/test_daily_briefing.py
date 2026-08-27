import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.run_daily_pipeline as pipeline
from scripts.daily_briefing import DailyBriefingError, load_daily_briefing


def analysis_payload(source_hash: str = "a" * 64):
    evidence = ["https://example.com/evidence"]
    return {
        "contract_version": "daily-briefing-analysis.v1",
        "generated_at": "2026-08-27T13:00:00+09:00",
        "source_snapshot_hash": source_hash,
        "headline": "오늘의 기술 변화는 권한과 운영 비용으로 모인다",
        "summary": "여러 기사를 중복 제거해 개발자의 결정으로 번역했다.",
        "retrospective": {
            "status": "baseline",
            "previous_generated_at": "",
            "previous_snapshot_hash": "",
            "items": [],
        },
        "core_signals": [
            {"metric": str(index), "label": f"신호 {index}", "detail": "변화 설명", "action": "설정을 확인한다", "tone": tone, "evidence_urls": evidence}
            for index, tone in enumerate(("green", "amber", "red"), 1)
        ],
        "keywords": [
            {"keyword": f"키워드 {index}", "score": 10 - index, "direction": "stable", "basis": "공식 변화와 반복 관측"}
            for index in range(7)
        ],
        "matrix": [
            {"quadrant": quadrant, "label": quadrant, "meaning": "영향 설명", "action": "확인 행동", "evidence_urls": evidence}
            for quadrant in ("focus", "future", "apply", "watch")
        ],
        "timeline": [
            {"horizon": horizon, "action": "실행 항목", "reason": "실행 이유", "evidence_urls": evidence}
            for horizon in ("today", "week", "month", "year")
        ],
        "insight_cards": [
            {"title": f"인사이트 {index}", "analysis": "종합 분석", "action": "결정 확인", "evidence_urls": evidence}
            for index in range(3)
        ],
        "themes": [
            {"title": f"테마 {index}", "analysis": "기사 묶음 분석", "action": "문서를 확인", "evidence_urls": evidence}
            for index in range(3)
        ],
        "developer_insights": [
            {"title": f"개발자 {index}", "analysis": "운영 영향", "action": "환경 점검", "evidence_urls": evidence}
            for index in range(3)
        ],
        "watchlist": [
            {"title": f"주시 {index}", "reason": "후속 발표 대기", "trigger": "공식 릴리스", "evidence_urls": evidence}
            for index in range(2)
        ],
        "source_title_translations": [
            {"source_url": "https://example.com/english", "korean_title": "에이전트 평가를 운영 게이트로 전환"}
        ],
        "must_read": [
            {"title": category, "korean_title": "", "category": category, "source": "공식 원문", "source_url": f"https://example.com/{index}", "why_it_matters": "선택이 달라진다", "action": "원문 조건을 확인한다"}
            for index, category in enumerate(("AI/ML 핵심", "개발 트렌드", "AI 공식 블로그", "국내 IT", "국내 시사"))
        ],
    }


class DailyBriefingTests(unittest.TestCase):
    def test_freezes_latest_valid_prior_briefing_for_retrospective(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            prior = runs / "20260826T170000Z-1111111111"
            current = runs / "20260827T170000Z-2222222222"
            prior.mkdir(parents=True)
            current.mkdir(parents=True)
            (prior / "daily-briefing-analysis.json").write_text(
                json.dumps(analysis_payload(), ensure_ascii=False), encoding="utf-8"
            )

            with mock.patch.object(pipeline, "RUNS_DIR", runs):
                path, snapshot_hash, labels = pipeline.freeze_previous_daily_briefing(
                    run_id=current.name,
                    run_directory=current,
                )

            self.assertEqual(path, current / "previous-daily-briefing.json")
            self.assertEqual(len(snapshot_hash), 64)
            self.assertEqual(labels, ["신호 1", "신호 2", "신호 3"])
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                snapshot["contract_version"],
                "daily-briefing-retrospective-input.v1",
            )
            self.assertEqual(snapshot["previous_run_id"], prior.name)

    def test_pipeline_freezes_source_snapshot_before_agent_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            run.mkdir()
            topics = run / "topics.md"
            topics.write_text("# fixture", encoding="utf-8")
            cache = root / "editorial.json"
            cache.write_text(
                json.dumps(
                    {
                        "provider": "hunt_news_editorial_sources",
                        "contract_version": "editorial-source-cache.v1",
                        "checked_at": "2026-08-27T12:00:00+00:00",
                        "source_snapshot_hash": "a" * 64,
                        "rows": [{"category": "AI/ML 핵심", "source": "source", "title": "title", "url": "https://example.com/item", "published_at": "2026-08-27T12:00:00+00:00"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            def fake_run_stage(*args, **kwargs):
                (run / "daily-briefing-analysis.json").write_text(
                    json.dumps(analysis_payload(), ensure_ascii=False), encoding="utf-8"
                )

            with mock.patch.object(
                pipeline, "DEFAULT_EDITORIAL_SOURCE_CACHE", cache
            ), mock.patch.object(
                pipeline, "RUNS_DIR", root / "isolated-runs"
            ), mock.patch.object(
                pipeline, "run_stage", side_effect=fake_run_stage
            ):
                result = pipeline.run_daily_briefing_analysis(
                    "codex",
                    run_id="20260827T170000Z-1234567890",
                    run_directory=run,
                    topics_path=topics,
                    logger=logging.getLogger("snapshot-test"),
                    timeout_seconds=10,
                )

            self.assertEqual(result, run / "daily-briefing-analysis.json")
            frozen = json.loads((run / "editorial-sources-snapshot.json").read_text())
            self.assertEqual(frozen["source_snapshot_hash"], "a" * 64)

    def test_pipeline_fails_closed_when_required_analysis_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            run.mkdir()
            topics = run / "topics.md"
            topics.write_text("# fixture", encoding="utf-8")
            cache = root / "editorial.json"
            cache.write_text(
                json.dumps(
                    {
                        "provider": "hunt_news_editorial_sources",
                        "contract_version": "editorial-source-cache.v1",
                        "checked_at": "2026-08-27T12:00:00+00:00",
                        "source_snapshot_hash": "a" * 64,
                        "rows": [
                            {
                                "category": "AI/ML 핵심",
                                "source": "source",
                                "title": "title",
                                "url": "https://example.com/item",
                                "published_at": "2026-08-27T12:00:00+00:00",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            def fake_run_stage(*args, **kwargs):
                invalid = analysis_payload()
                invalid["core_signals"][0]["evidence_urls"] = []
                (run / "daily-briefing-analysis.json").write_text(
                    json.dumps(invalid, ensure_ascii=False), encoding="utf-8"
                )

            with mock.patch.object(
                pipeline, "DEFAULT_EDITORIAL_SOURCE_CACHE", cache
            ), mock.patch.object(
                pipeline, "RUNS_DIR", root / "isolated-runs"
            ), mock.patch.object(
                pipeline, "run_stage", side_effect=fake_run_stage
            ), self.assertRaises(pipeline.PipelineError):
                pipeline.run_daily_briefing_analysis(
                    "codex",
                    run_id="20260827T170000Z-1234567890",
                    run_directory=run,
                    topics_path=topics,
                    logger=logging.getLogger("invalid-briefing-test"),
                    timeout_seconds=10,
                )

    def test_validates_complete_evidence_backed_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily-briefing-analysis.json"
            payload = analysis_payload()
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            safe = load_daily_briefing(path, source_snapshot_hash="a" * 64)

            self.assertEqual(len(safe["core_signals"]), 3)
            self.assertEqual(len(safe["must_read"]), 5)
            self.assertEqual(safe["source_title_translations"][0]["korean_title"], "에이전트 평가를 운영 게이트로 전환")
            self.assertEqual({row["category"] for row in safe["must_read"]}, {"AI/ML 핵심", "개발 트렌드", "AI 공식 블로그", "국내 IT", "국내 시사"})

    def test_rejects_non_korean_source_title_translation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily-briefing-analysis.json"
            payload = analysis_payload()
            payload["source_title_translations"][0]["korean_title"] = "English only"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(DailyBriefingError):
                load_daily_briefing(path, source_snapshot_hash="a" * 64)

    def test_rejects_snapshot_drift_and_missing_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily-briefing-analysis.json"
            payload = analysis_payload()
            payload["core_signals"][0]["evidence_urls"] = []
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(DailyBriefingError):
                load_daily_briefing(path, source_snapshot_hash="b" * 64)

    def test_rejects_duplicate_must_read_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily-briefing-analysis.json"
            payload = analysis_payload()
            payload["must_read"][4]["category"] = "AI/ML 핵심"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(DailyBriefingError):
                load_daily_briefing(path, source_snapshot_hash="a" * 64)

    def test_rejects_retrospective_snapshot_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily-briefing-analysis.json"
            payload = analysis_payload()
            payload["retrospective"] = {
                "status": "available",
                "previous_generated_at": "2026-08-26T13:00:00+09:00",
                "previous_snapshot_hash": "b" * 64,
                "items": [
                    {
                        "previous_signal_index": index,
                        "previous_label": f"신호 {index}",
                        "previous_detail": "전일 판단",
                        "verdict": "confirmed",
                        "current_status": "오늘 근거로 유지됨",
                        "action": "변경 여부를 계속 확인한다",
                        "evidence_urls": ["https://example.com/current"],
                    }
                    for index in range(1, 4)
                ],
            }
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(DailyBriefingError):
                load_daily_briefing(
                    path,
                    previous_snapshot_hash="c" * 64,
                    previous_signal_labels=["신호 1", "신호 2", "신호 3"],
                    retrospective_required=True,
                )

    def test_accepts_evidence_backed_three_signal_retrospective(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "daily-briefing-analysis.json"
            payload = analysis_payload()
            payload["retrospective"] = {
                "status": "available",
                "previous_generated_at": "2026-08-26T13:00:00+09:00",
                "previous_snapshot_hash": "b" * 64,
                "items": [
                    {
                        "previous_signal_index": index,
                        "previous_label": f"신호 {index}",
                        "previous_detail": "전일 판단",
                        "verdict": verdict,
                        "current_status": "오늘 근거로 다시 확인한 상태",
                        "action": "공식 변경 여부를 계속 확인한다",
                        "evidence_urls": [f"https://example.com/current/{index}"],
                    }
                    for index, verdict in enumerate(
                        ("confirmed", "changed", "unresolved"), start=1
                    )
                ],
            }
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            safe = load_daily_briefing(
                path,
                previous_snapshot_hash="b" * 64,
                previous_signal_labels=["신호 1", "신호 2", "신호 3"],
                retrospective_required=True,
            )

            self.assertEqual(
                [item["verdict"] for item in safe["retrospective"]["items"]],
                ["confirmed", "changed", "unresolved"],
            )


if __name__ == "__main__":
    unittest.main()
