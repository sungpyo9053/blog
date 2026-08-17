from __future__ import annotations

import unittest

from scripts.migrate_hunt_news import ACTIVE_CATEGORIES, build_plan, classify_hot_issue


class HuntNewsMigrationTests(unittest.TestCase):
    def test_active_categories_match_public_navigation(self):
        self.assertEqual(
            list(ACTIVE_CATEGORIES),
            ["life", "economy", "real-estate", "society", "politics", "culture-entertainment", "it"],
        )

    def test_hot_issue_classification_uses_life_impact(self):
        self.assertEqual(
            classify_hot_issue("7월 Next.js 보안 취약점 대응: 공식 패치와 WAF 완화책"),
            "it",
        )
        self.assertEqual(
            classify_hot_issue("AI 모델 평가 중 인프라 침해 사고: 권한 격리 체크리스트"),
            "it",
        )
        self.assertEqual(classify_hot_issue("기준금리 동결과 주담대 금리"), "economy")
        self.assertEqual(classify_hot_issue("전세 계약과 임대차 제도 변경"), "real-estate")
        self.assertEqual(classify_hot_issue("선거법 개정안 찬반"), "politics")
        self.assertEqual(classify_hot_issue("OTT 구독료 변경"), "culture-entertainment")
        self.assertEqual(classify_hot_issue("주민등록 사실조사"), "society")
        self.assertEqual(classify_hot_issue("대중교통 이용 변경"), "life")

    def test_legacy_technical_post_moves_to_it_without_identity_change(self):
        categories = [
            {"id": 27, "slug": "tech", "name": "Tech"},
            {"id": 200, "slug": "it", "name": "IT"},
        ]
        posts = [
            {
                "id": 391,
                "slug": "youtube-scale-video-platform-design",
                "link": "https://huntlab.app/youtube-scale-video-platform-design/",
                "title": {"raw": "유튜브급 동영상 플랫폼 시스템 설계"},
                "categories": [27],
            }
        ]
        updates, _ = build_plan(posts, categories)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["id"], 391)
        self.assertEqual(updates[0]["slug"], posts[0]["slug"])
        self.assertEqual(updates[0]["target_slug"], "it")


if __name__ == "__main__":
    unittest.main()
