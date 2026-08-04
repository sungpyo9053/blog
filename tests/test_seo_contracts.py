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

    def test_writer_requires_metadata_slug_and_optional_faq(self):
        text = read("agents/writer.md")
        for field in (
            "meta_description",
            "excerpt",
            "publish_mode",
            "110~160자",
            "FAQ는 검색 의도상",
        ):
            self.assertIn(field, text)
        self.assertIn("소문자 영문·숫자·하이픈", text)

    def test_style_guide_and_agents_use_technical_blog_contract(self):
        style = read("guides/style-guide.md")
        writer = read("agents/writer.md")
        reviewer = read("agents/reviewer.md")
        for field in (
            "HuntLab WordPress 기술 블로그 문체 가이드",
            "기술·AI 제품 또는 아키텍처 해설",
            "설치·튜토리얼·장애 해결",
            "Build Log·개발 경험",
            "검증 범위와 판단",
            "AI가 쓴 티를 줄이는 규칙",
            "한눈에 보기는 선택 사항",
            "오픈소스·기술 프로젝트 딥다이브",
        ):
            self.assertIn(field, style)
        self.assertNotIn("네이버 블로그 초안", writer)
        self.assertNotIn("gudies/", writer)
        self.assertNotIn("FAQ를 최소 3개", writer)
        self.assertNotIn("ㅋㅋㅋ, ..., ??", style)
        for field in (
            "첫 두 문단",
            "구조, 작동 원리",
            "직접 검증, 공식 자료",
            "같은 H2·요약·결론",
        ):
            self.assertIn(field, writer)
            self.assertIn(field, reviewer)

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

    def test_image_policy_uses_editorial_landscape_thumbnail(self):
        guide = read("guides/image-guide.md")
        agent = read("agents/image-maker.md")
        for text in (guide, agent):
            self.assertIn("1600×900", text)
            self.assertIn("에디토리얼", text)
            self.assertIn("개념 비유", text)
            self.assertIn("HTML·CSS fallback", text)
        self.assertNotIn("1080×1080px", agent)

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
        planner = read("agents/topic-planner-agent.md")
        style = read("guides/style-guide.md")
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
        self.assertIn("capture_evidence", researcher)
        self.assertIn("DIRECT_EVIDENCE_CAPTURE", writer)
        self.assertIn("DIRECT_EVIDENCE_CAPTURE", read("agents/image-maker.md"))
        self.assertIn("검증 캡처가 1~2장", reviewer)
        self.assertIn("직접 검증 캡처", read("guides/image-guide.md"))
        for text in (planner, researcher, writer, reviewer):
            self.assertIn("controlled_comparison", text)
            self.assertIn("not_directly_tested", text)
        self.assertIn("정의되지 않은 변형값은 REJECT", reviewer)
        for term in (
            "command_and_output",
            "failed_attempt",
            "before_after",
            "operator_judgment",
            "docs_vs_observed",
        ):
            self.assertIn(term, planner)
            self.assertIn(term, style)
            self.assertIn(term, researcher)
            self.assertIn(term, writer)
            self.assertIn(term, reviewer)

    def test_topic_planner_prioritizes_core_categories(self):
        text = read("agents/topic-planner-agent.md")
        self.assertIn("70% 이상", text)
        self.assertIn("TOP2의\n최대 한 자리", text)


if __name__ == "__main__":
    unittest.main()
