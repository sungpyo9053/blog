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


if __name__ == "__main__":
    unittest.main()
