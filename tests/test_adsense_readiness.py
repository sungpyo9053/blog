from __future__ import annotations

import unittest

from scripts.audit_content_repetition import analyze_posts, extract_structure
from scripts.update_adsense_readiness import (
    ABOUT_HTML,
    CONTACT_HTML,
    EDITORIAL_HTML,
    PRIVACY_HTML,
    PUBLIC_PAGE_SPECS,
    build_plan,
)


class AdSenseReadinessTests(unittest.TestCase):
    def test_privacy_policy_has_google_required_disclosures(self):
        self.assertIn("Google AdSense", PRIVACY_HTML)
        self.assertIn("제3자 광고 제공업체", PRIVACY_HTML)
        self.assertIn("쿠키", PRIVACY_HTML)
        self.assertIn("웹 비콘", PRIVACY_HTML)
        self.assertIn("IP 주소", PRIVACY_HTML)
        self.assertIn("policies.google.com/technologies/partner-sites", PRIVACY_HTML)

    def test_about_describes_actual_signal_boundaries(self):
        self.assertIn("Google Trends 한국 RSS", ABOUT_HTML)
        self.assertIn("Search Console", ABOUT_HTML)
        self.assertIn("과거 캐시만 장기 수요 참고값", ABOUT_HTML)
        self.assertIn("Shadow Mode", ABOUT_HTML)
        self.assertIn("발행 주제를 바꾸지 않습니다", ABOUT_HTML)

    def test_contact_exposes_operator_editor_and_correction_path(self):
        self.assertIn("HuntLab이 사이트를 운영", CONTACT_HTML)
        self.assertIn("Hunt News 편집팀", CONTACT_HTML)
        self.assertIn("정정 처리 원칙", CONTACT_HTML)
        self.assertIn("개인정보 요청", CONTACT_HTML)

    def test_editorial_policy_discloses_repetition_and_signal_boundaries(self):
        self.assertIn("반복·중복 방지", EDITORIAL_HTML)
        self.assertIn("후보 발견·검색 의도 신호일 뿐 사실 근거로 사용하지 않습니다", EDITORIAL_HTML)

    def test_page_plan_is_idempotent(self):
        pages = [
            {
                "id": index,
                "slug": slug,
                "title": {"raw": spec["title"]},
                "content": {"raw": spec["content"]},
            }
            for index, (slug, spec) in enumerate(PUBLIC_PAGE_SPECS.items(), start=1)
        ]
        self.assertTrue(all(not row["needs_update"] for row in build_plan(pages)))

    def test_repetition_audit_ignores_standard_headings_and_finds_material_duplicates(self):
        html = """
        <p>같은 문제를 설명하는 첫 문단입니다.</p><p>같은 독자 조건을 설명합니다.</p>
        <h2>20초 핵심 요약</h2><h2>실제 판단 기준</h2>
        <p>중간 설명입니다.</p><p>같은 결론입니다.</p><p>같은 행동입니다.</p>
        """
        posts = [
            {"id": 1, "link": "/a", "title": {"rendered": "A"}, "content": {"rendered": html}},
            {"id": 2, "link": "/b", "title": {"rendered": "B"}, "content": {"rendered": html}},
        ]
        result = analyze_posts(posts)
        self.assertEqual(result["risk_post_ids"], [1, 2])
        self.assertEqual(extract_structure(html)["headings"], ["실제 판단 기준"])

    def test_repetition_audit_finds_near_duplicate_copy(self):
        first = "<p>정부 발표가 나왔지만 지금 신청 대상과 날짜를 구분해야 합니다.</p><p>공식 문서에서 적용 조건을 확인했습니다.</p><h2>대상 확인</h2><p>설명</p><p>오늘은 공식 공고를 확인하세요.</p><p>확정 전에는 기다리세요.</p>"
        second = "<p>정부 발표가 나왔지만 지금 신청 대상과 날짜를 구분해야 합니다.</p><p>공식 문서에서 실제 적용 조건을 확인했습니다.</p><h2>대상 확인하기</h2><p>다른 설명</p><p>오늘 공식 공고를 확인하세요.</p><p>확정 전까지 기다리세요.</p>"
        posts = [
            {"id": 1, "link": "/a", "title": {"rendered": "A"}, "content": {"rendered": first}},
            {"id": 2, "link": "/b", "title": {"rendered": "B"}, "content": {"rendered": second}},
        ]
        result = analyze_posts(posts)
        self.assertTrue(result["near_duplicate_intro_pairs"])


if __name__ == "__main__":
    unittest.main()
