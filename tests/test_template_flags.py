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
                    "fixed_heading:자주 묻는 질문", "faq_exactly_7", "closer"]),
        )

    def test_clean_post(self) -> None:
        html = '<p>부부가 둘 다 받으면 20%가 줄어든다.</p><h2>국민연금을 받으면 얼마나 줄어드나</h2><p>설명</p>'
        self.assertEqual(template_flags(html), [])


if __name__ == "__main__":
    unittest.main()
