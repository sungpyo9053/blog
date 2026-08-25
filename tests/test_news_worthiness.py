import json
import tempfile
import unittest
from pathlib import Path

from scripts.news_worthiness import (
    CONTRACT_VERSION,
    CandidateEvaluator,
    NewsWorthinessScorer,
    TopicReranker,
    build_shadow_diff,
    make_candidate_id,
    make_shadow_input_snapshot,
    write_shadow_diff,
)


def candidate(title: str, *, cluster: str = "정책", sources: str | None = None):
    return {
        "title": title,
        "category": "생활",
        "primary_keyword": title,
        "effective_date": "2026-08-22",
        "problem_origin": "official_change",
        "topic_cluster": cluster,
        "score_breakdown": (
            "최신성 9; 검색 수요 10; 공식 출처 9; Evergreen 7; "
            "HuntLab 적합성 8; 기술적 깊이 7; 독창성 8; "
            "최근 작성 여부 9; 카테고리 균형 8"
        ),
        "affected_reader": "정책 적용 대상자",
        "life_impact": "신청 조건이 달라진다",
        "reader_action": "공식 공고에서 자격을 확인한다",
        "research_focus": "시행일과 적용 대상을 공식 문서로 대조",
        "editorial_thesis": "독자의 다음 행동을 설명한다",
        "duplicate_check": "중복 없음",
        "whereispost_total_searches": 1000,
        "demand_signal_source": "Whereispost observed cache",
        "sources": sources
        or "https://example.go.kr/releases/1, https://news.example.com/articles/1",
    }


class CandidateEvaluatorTest(unittest.TestCase):
    def test_shadow_snapshot_shares_no_nested_mutable_references(self):
        original = [{"title": "A", "nested": {"values": [1, 2]}}]
        snapshot, legacy_titles = make_shadow_input_snapshot(original, original)

        self.assertEqual(legacy_titles, ("A",))
        self.assertIsNot(snapshot, original)
        self.assertIsNot(snapshot[0], original[0])
        self.assertIsNot(snapshot[0]["nested"], original[0]["nested"])
        self.assertIsNot(snapshot[0]["nested"]["values"], original[0]["nested"]["values"])

    def test_shadow_snapshot_is_deterministic_across_dict_insertion_order(self):
        first = [{"title": "A", "nested": {"b": 2, "a": 1}}]
        second = [{"nested": {"a": 1, "b": 2}, "title": "A"}]

        first_snapshot = make_shadow_input_snapshot(first, first)
        second_snapshot = make_shadow_input_snapshot(second, second)

        self.assertEqual(first_snapshot, second_snapshot)
        self.assertEqual(
            json.dumps(first_snapshot, ensure_ascii=False, sort_keys=True).encode(),
            json.dumps(second_snapshot, ensure_ascii=False, sort_keys=True).encode(),
        )

    def test_missing_evidence_zeroes_effective_score_without_changing_raw(self):
        item = candidate("근거 없는 생활 영향")
        item["affected_reader"] = ""
        item["life_impact"] = ""
        item["reader_action"] = ""

        result = CandidateEvaluator().evaluate(item)

        self.assertEqual(result["raw_features"]["personal_impact"], 8)
        self.assertEqual(result["evidence"]["personal_impact"]["strength"], "none")
        self.assertEqual(result["evidence_multiplier"]["personal_impact"], 0.0)
        self.assertEqual(result["effective_features"]["personal_impact"], 0.0)

    def test_search_demand_uses_observed_number_not_planner_demand_score(self):
        low = candidate("관측 수요 없음")
        low["whereispost_total_searches"] = 0
        high = candidate("관측 수요 있음")
        high["whereispost_total_searches"] = 9999

        low_result = CandidateEvaluator().evaluate(low)
        high_result = CandidateEvaluator().evaluate(high)

        self.assertEqual(low_result["effective_features"]["search_demand"], 0.0)
        self.assertGreater(high_result["effective_features"]["search_demand"], 0.0)

    def test_search_demand_maps_structured_google_trends_traffic(self):
        item = candidate("Google Trends 관측 수요")
        item["whereispost_total_searches"] = 0
        item["google_trends_approx_traffic"] = 200

        result = CandidateEvaluator().evaluate(item)

        self.assertEqual(result["evidence"]["search_demand"]["observed_value"], 200)
        self.assertEqual(result["evidence"]["search_demand"]["strength"], "strong")
        self.assertGreater(result["effective_features"]["search_demand"], 0.0)

    def test_search_demand_recovers_legacy_approx_traffic_claim(self):
        item = candidate("기존 Trends 문자열 수요")
        item["whereispost_total_searches"] = 0
        item["demand_signal_source"] = (
            "Google Trends KR RSS checked_at=2026-08-23T16:10:17Z, "
            "topic=수능원서접수, approx_traffic=200; Search Console 연결 없음"
        )

        result = CandidateEvaluator().evaluate(item)

        self.assertEqual(result["evidence"]["search_demand"]["observed_value"], 200)
        self.assertEqual(result["evidence"]["search_demand"]["strength"], "strong")
        self.assertGreater(result["effective_features"]["search_demand"], 0.0)

    def test_candidate_id_ignores_title_and_tracking_query(self):
        first = make_candidate_id("https://example.com/release?utm_source=x", "event-1")
        second = make_candidate_id("https://example.com/release", "event-1")
        self.assertEqual(first, second)


class ScorerAndRerankerTest(unittest.TestCase):
    def test_hard_filter_rejects_missing_official_source_before_scoring(self):
        item = candidate("공식 출처 없음", sources="출처 확인 필요")
        result = NewsWorthinessScorer().score(CandidateEvaluator().evaluate(item))

        self.assertEqual(result["hard_filter_result"], "reject")
        self.assertIn("official_source_missing", result["hard_filter_reasons"])
        self.assertEqual(result["base_score"], 0.0)

    def test_topic_reranker_applies_repeat_decay(self):
        scorer = NewsWorthinessScorer()
        records = [
            scorer.score(CandidateEvaluator().evaluate(candidate("A", cluster="같은 주제"))),
            scorer.score(CandidateEvaluator().evaluate(candidate("B", cluster="같은 주제"))),
        ]
        ranked = TopicReranker().rank(records)

        self.assertFalse(ranked[0]["topic_decay_applied"])
        self.assertTrue(ranked[1]["topic_decay_applied"])
        self.assertEqual(ranked[1]["topic_decay"]["factor"], 0.7)

    def test_shadow_diff_is_reproducible_and_preserves_legacy_top2(self):
        items = [
            candidate("Legacy A", cluster="A"),
            candidate("Legacy B", cluster="B"),
            candidate("Shadow C", cluster="C"),
        ]
        legacy = [items[0]["title"], items[1]["title"]]
        first = build_shadow_diff(items, legacy, selected_at="2026-08-21T00:00:00+00:00")
        second = build_shadow_diff(items, legacy, selected_at="2026-08-21T00:00:00+00:00")

        self.assertEqual(first, second)
        self.assertEqual(first["legacy_top2"], ["Legacy A", "Legacy B"])
        self.assertEqual(first["selection_mode"], "shadow")
        self.assertEqual(first["contract_version"], CONTRACT_VERSION)
        self.assertIn("score_breakdown", first)
        self.assertIn("topic_decay_applied", first)

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "shadow.json"
            write_shadow_diff(path, first)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), first)

    def test_all_hard_filtered_candidates_produce_empty_shadow_top2(self):
        items = [candidate("탈락 A", sources="없음"), candidate("탈락 B", sources="없음")]
        result = build_shadow_diff(
            items,
            [item["title"] for item in items],
            selected_at="2026-08-21T00:00:00+00:00",
        )
        self.assertEqual(result["shadow_top2"], [])
        self.assertEqual(result["legacy_top2"], ["탈락 A", "탈락 B"])
        self.assertEqual(len(result["hard_filter_rejections"]), 2)


if __name__ == "__main__":
    unittest.main()
