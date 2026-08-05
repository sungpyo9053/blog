from __future__ import annotations

import unittest

from scripts.audit_public_site import FetchResult, inspect_page, normalize_internal_link, render_markdown, sitemap_urls


class PublicSiteAuditTests(unittest.TestCase):
    def test_sitemap_urls_handles_namespaces(self):
        xml = b'''<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"><url><loc>https://huntlab.app/post/</loc><image:image><image:loc>https://huntlab.app/image.webp</image:loc></image:image></url></urlset>'''
        self.assertEqual(sitemap_urls(xml), ["https://huntlab.app/post/"])

    def test_inspect_page_collects_author_media_and_evidence(self):
        html = '''<html><head><title>Test</title><meta name="author" content="admin"><meta property="og:image" content="https://huntlab.app/a.webp"><link rel="canonical" href="https://huntlab.app/post/"></head><body><img class="wp-post-image" alt="diagram"><section class="huntlab-article-quick-summary">요약</section><aside class="huntlab-article-toc">목차</aside><p>검증 환경과 실행 결과를 확인했다.</p><a href="/next/">next</a></body></html>'''.encode("utf-8")
        facts = inspect_page(FetchResult("https://huntlab.app/post/", 200, "text/html", html), "https://huntlab.app/")
        self.assertEqual(facts.author, "admin")
        self.assertEqual(facts.featured_alt, "diagram")
        self.assertIn("검증 환경", facts.evidence_signals)
        self.assertTrue(facts.has_quick_summary)
        self.assertTrue(facts.has_article_toc)
        self.assertIn("https://huntlab.app/next/", facts.internal_links)

    def test_normalize_internal_link_drops_assets_and_external_urls(self):
        self.assertIsNone(normalize_internal_link("https://example.com/x", "https://huntlab.app/"))
        self.assertIsNone(normalize_internal_link("https://huntlab.app/a.webp", "https://huntlab.app/"))
        self.assertEqual(
            normalize_internal_link("https://huntlab.app/post/#part", "https://huntlab.app/"),
            "https://huntlab.app/post/",
        )

    def test_report_surfaces_empty_categories_and_generic_authors(self):
        report = render_markdown(
            {
                "base_url": "https://huntlab.app/",
                "endpoints": {name: {"status": 200, "content_type": "text/plain", "error": ""} for name in ("robots", "sitemap", "ads_txt")},
                "counts": {"post": 1, "page": 0, "category": 1},
                "child_sitemaps": [],
                "empty_categories": ["Hot Issue"],
                "broken_internal_links": [],
                "unverified_urls": [],
                "pages": [
                    {
                        "url": "https://huntlab.app/post/",
                        "status": 200,
                        "title": "Post",
                        "canonical": "https://huntlab.app/post/",
                        "author": "admin",
                        "og_image": "https://huntlab.app/a.webp",
                        "noindex": False,
                        "featured_alt": "alt",
                        "evidence_signals": [],
                        "internal_links": [],
                    }
                ],
            }
        )
        self.assertIn("Hot Issue", report)
        self.assertIn("generic_author_posts: `1`", report)
        self.assertIn("missing_quick_summary_posts: `1`", report)
        self.assertIn("missing_article_toc_posts: `1`", report)
        self.assertIn("20초 핵심 요약 누락 글", report)
        self.assertIn("https://huntlab.app/post/", report)


if __name__ == "__main__":
    unittest.main()
