from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class SEOAgentContractTests(unittest.TestCase):
    def test_topic_planner_has_editor_and_search_contract(self):
        text = read("agents/topic-planner-agent.md")
        for category in (
            "Tech",
            "AI",
            "Economy",
            "Society",
            "Politics",
            "Hot Issue",
            "Build Log",
        ):
            self.assertIn(category, text)
        self.assertIn("전체 최소 35개", text)
        self.assertIn("TOP10", text)
        self.assertIn("TOP2", text)
        self.assertIn("primary_keyword", text)
        self.assertIn("secondary_keywords", text)
        self.assertIn("target_reader", text)
        self.assertIn("TOP2에는 카테고리별 의무 할당을 두지 않는다", text)
        self.assertNotIn(
            "TOP2 중 최소 1개가 Economy, Society, Politics 또는 Hot Issue",
            text,
        )

    def test_research_requires_seo_analysis(self):
        text = read("agents/researcher.md")
        for field in (
            "Primary Keyword",
            "Secondary Keywords",
            "Related Keywords",
            "People Also Ask",
            "경쟁 문서 특징",
            "FAQ 후보",
        ):
            self.assertIn(field, text)

    def test_writer_requires_metadata_slug_and_faq(self):
        text = read("agents/writer.md")
        for field in (
            "meta_description",
            "excerpt",
            "publish_mode",
            "110~160자",
            "FAQ를 최소 3개",
        ):
            self.assertIn(field, text)
        self.assertIn("소문자 영문·숫자·하이픈", text)

    def test_reviewer_rejects_incomplete_seo(self):
        text = read("agents/reviewer.md")
        self.assertIn("하나라도 부족하면 `REJECTED`", text)
        for check in (
            "Primary Keyword",
            "Meta Description",
            "Slug",
            "내부 링크",
            "공식 외부 링크",
            "검색자가 해결하려던 문제",
        ):
            self.assertIn(check, text)

    def test_agents_follow_monetization_policy(self):
        guide = read("guides/monetization-guide.md")
        for field in (
            "검색 의도",
            "제휴",
            "과장",
            "공식 가격",
            "recommended_cta",
            "affiliate_disclosure",
        ):
            self.assertIn(field, guide)
        for agent in (
            "agents/topic-planner-agent.md",
            "agents/researcher.md",
            "agents/writer.md",
            "agents/reviewer.md",
            "agents/publisher-agent.md",
        ):
            self.assertIn("monetization-guide.md", read(agent))

    def test_analytics_optimizer_is_independent(self):
        guide = read("guides/analytics-optimization-guide.md")
        agent = read("agents/analytics-optimizer-agent.md")
        runner = read("scripts/run_analytics_optimizer.py")
        self.assertIn("Daily Pipeline과", guide)
        self.assertIn("Publisher 호출", agent)
        self.assertIn('REPORT_DIR = ROOT / "output" / "analytics"', runner)
        self.assertIn("INCOMPLETE", runner)
        self.assertIn("def analyze(", runner)
        self.assertIn("disabled_review_required", runner)
        self.assertNotIn("trigger_pipeline_if_needed", runner)
        self.assertIn("전달 책임은 정규 Harness에 있다", guide)
        self.assertIn("정규 Harness가 Planner/Writer 프롬프트", agent)

    def test_planner_has_cluster_and_cannibalization_contract(self):
        text = read("agents/topic-planner-agent.md")
        for field in (
            "internal_link_candidates",
            "topic_cluster",
            "pillar_candidate",
            "Keyword Cannibalization",
        ):
            self.assertIn(field, text)

    def test_reviewer_requires_featured_image_contract(self):
        text = read("agents/reviewer.md")
        self.assertIn("./images/thumbnail.png", text)
        self.assertIn("featured_image_alt", text)

    def test_original_value_and_editorial_policy_contract(self):
        planner = read("agents/topic-planner-agent.md")
        researcher = read("agents/researcher.md")
        writer = read("agents/writer.md")
        reviewer = read("agents/reviewer.md")
        policy = read("guides/editorial-policy.md")
        for field in ("original_value_plan", "evidence_plan"):
            self.assertIn(field, planner)
        for field in ("original_contribution", "evidence", "limitations", "INSUFFICIENT"):
            self.assertIn(field, researcher)
        self.assertIn("INSUFFICIENT", writer)
        self.assertIn("단순 재요약은 REJECT", reviewer)
        self.assertIn("AI를 조사 정리와 초안 작성의 보조 도구", policy)
        self.assertIn("하루 발행량보다 품질 기준", policy)
        self.assertIn("유사 글 증산보다", policy)


class SEOImageAndPublisherPolicyTests(unittest.TestCase):
    def test_image_policy_blocks_sensitive_fabrication(self):
        text = read("guides/image-guide.md")
        self.assertIn("실존 정치인", text)
        self.assertIn("출처 없는 차트", text)
        self.assertIn("가짜 뉴스 화면", text)
        self.assertIn("가짜 성공 화면", text)
        self.assertIn("이미지 0장", text)

    def test_publisher_metadata_and_category_contract(self):
        text = read("guides/publisher-guide.md")
        for field in (
            "Title",
            "Slug",
            "Category",
            "Tags",
            "Meta Description",
            "Excerpt",
            "OG Description",
            "Featured Image",
            "Publish Mode",
        ):
            self.assertIn(field, text)
        self.assertIn("존재하지 않는 Category를 자동 생성하지 않는다", text)
        self.assertIn("`Uncategorized`", text)
        self.assertIn("`draft`와 `publish`", text)

    def test_seo_guide_has_google_search_contract(self):
        text = read("guides/seo-guide.md")
        for section in (
            "Google 검색 유입 핵심 계약",
            "Featured Snippet",
            "People Also Ask",
            "E-E-A-T",
            "Google Helpful Content",
            "Evergreen",
        ):
            self.assertIn(section, text)

    def test_editorial_policy_exposes_author_and_verification_contract(self):
        text = read("guides/editorial-policy.md")
        self.assertIn("HuntLab 편집팀", text)
        self.assertIn("작성자와 운영 환경", text)
        self.assertIn("Reviewer 승인", text)

    def test_research_writer_reviewer_share_execution_evidence_contract(self):
        researcher = read("agents/researcher.md")
        writer = read("agents/writer.md")
        reviewer = read("agents/reviewer.md")
        for term in (
            "verification_date",
            "environment",
            "observed_result",
            "operator_judgment",
        ):
            self.assertIn(term, researcher)
        for term in ("검증 날짜", "환경", "관측 결과", "운영 판단"):
            self.assertIn(term, writer)
            self.assertIn(term, reviewer)

    def test_topic_planner_prioritizes_core_categories(self):
        text = read("agents/topic-planner-agent.md")
        self.assertIn("70% 이상", text)
        self.assertIn("TOP2의\n최대 한 자리", text)


if __name__ == "__main__":
    unittest.main()
