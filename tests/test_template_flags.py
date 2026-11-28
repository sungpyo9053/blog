import unittest

from scripts.audit_content_repetition import template_flags


class TemplateFlagsTest(unittest.TestCase):
    def test_old_template_flagged(self) -> None:
        html = ('<p>2026년 11월 28일 복지부 고시로 확인했습니다.</p><h2>30초 핵심 요약</h2>'
                '<p>자료 확인일: 2026년 11월 28일</p><h2>자주 묻는 질문</h2>'
                + '"@type":"Question"' * 7 + '<p>복지로에 확인하자.</p>')
        self.assertEqual(
            sorted(template_flags(html)),
            sorted(["opener", "fixed_heading:30초 핵심 요약", "checked_box",
                    "fixed_heading:자주 묻는 질문", "faq_block:7", "closer"]),
        )

    def test_clean_post(self) -> None:
        html = '<p>부부가 둘 다 받으면 20%가 줄어든다.</p><h2>국민연금을 받으면 얼마나 줄어드나</h2><p>설명</p>'
        self.assertEqual(template_flags(html), [])

    def test_related_heading_backfill(self) -> None:
        self.assertIn("fixed_heading:함께 읽으면 좋은 글", template_flags("<h2>함께 읽으면 좋은 글</h2>"))

    def test_closer_variants(self) -> None:
        for last in ("결제 전에 공식 홈페이지에서 다시 확인하자.", "가입 전에 결제 화면의 금액을 확인하자."):
            self.assertIn("closer", template_flags(f"<p>본문이다.</p><p>{last}</p>"))
        # closer right before a final disclaimer paragraph (1956·1994·2046)
        self.assertIn("closer", template_flags("<p>a다.</p><p>요금을 다시 확인하자.</p><p>투자를 권하지 않는다.</p>"))

    def test_closer_no_false_positive(self) -> None:
        html = "<p>요금을 다시 확인하자.</p>" + "<p>본문이다.</p>" * 4  # only last 3 paragraphs count
        self.assertNotIn("closer", template_flags(html))
        self.assertNotIn("closer", template_flags("<p>확인하자는 말은 줄였다.</p>"))

    def test_opener_without_date(self) -> None:
        self.assertIn("opener", template_flags("<p>이용약관(2026년 9월 2일 시행)으로 가격과 조건을 확인했습니다.</p>"))
        self.assertNotIn("opener", template_flags("<p>공단에 직접 확인했습니다. 결과는 이렇다.</p>"))

    def test_faq_block_counts(self) -> None:
        for n in (6, 7, 8, 12):
            self.assertIn(f"faq_block:{n}", template_flags('"@type":"Question"' * n))
        self.assertEqual(template_flags('"@type":"Question"' * 5), [])


if __name__ == "__main__":
    unittest.main()
