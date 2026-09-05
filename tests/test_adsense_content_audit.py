from __future__ import annotations

import unittest

from scripts.audit_adsense_content import KEEP_EVIDENCE, inspect_post


class AdSenseContentAuditTests(unittest.TestCase):
    def test_keep_set_requires_durable_evidence_paths(self):
        self.assertEqual(set(KEEP_EVIDENCE), {96, 269, 274, 290, 301, 373})

    def setUp(self):
        self.categories = {
            1: {"id": 1, "slug": "development-trends", "name": "개발 트렌드"},
            2: {"id": 2, "slug": "life", "name": "생활"},
        }
        self.authors = {1: {"id": 1, "name": "Hunt News 편집팀"}}

    def post(self, content: str, category: int = 1):
        return {
            "id": 10,
            "link": "https://huntlab.app/test/",
            "slug": "test",
            "title": {"raw": "테스트 제목"},
            "content": {"raw": content},
            "date": "2026-09-05T00:00:00",
            "modified": "2026-09-05T00:00:00",
            "categories": [category],
            "author": 1,
            "aioseo_meta_data": {"robots_noindex": False},
        }

    def test_strong_signals_still_require_human_keep_review(self):
        row = inspect_post(
            self.post(
                "<h2>검증 환경</h2><p>직접 실행했습니다. 실패 로그 exit_code=1.</p>"
                "<pre><code>pytest -q</code></pre><p>전후 비교 p95 20ms</p>"
            ),
            self.categories,
            self.authors,
        )

        self.assertEqual(row["decision"], "REWRITE")
        self.assertEqual(row["direct_verification"], "NO")

    def test_reviewed_production_post_can_be_kept(self):
        post = self.post(
            "<h2>검증 환경</h2><p>직접 실행했습니다. 실패 로그 exit_code=1.</p>"
            "<pre><code>pytest -q</code></pre><p>전후 비교 p95 20ms</p>"
        )
        post["id"] = 290
        row = inspect_post(post, self.categories, self.authors)

        self.assertEqual(row["decision"], "KEEP")
        self.assertIn("tests/test_publisher.py", row["evidence_path"])

    def test_rewrites_document_only_technical_post(self):
        row = inspect_post(
            self.post("<h2>공식 문서</h2><p>공식 자료를 정리한 글입니다.</p>"),
            self.categories,
            self.authors,
        )

        self.assertEqual(row["decision"], "REWRITE")
        self.assertEqual(row["direct_verification"], "NO")

    def test_noindexes_nontechnical_post(self):
        row = inspect_post(
            self.post("<p>생활 정책을 설명합니다.</p>", category=2),
            self.categories,
            self.authors,
        )

        self.assertEqual(row["decision"], "NOINDEX")

    def test_untested_disclosure_prevents_keep(self):
        row = inspect_post(
            self.post(
                "<p>직접 실행하지 않았습니다.</p><pre><code>docker run sample</code></pre>"
                "<p>벤치마크 20ms</p>"
            ),
            self.categories,
            self.authors,
        )

        self.assertNotEqual(row["decision"], "KEEP")


if __name__ == "__main__":
    unittest.main()
