from __future__ import annotations

import unittest

from scripts.huntlab_wp_diagnostics import audit_indexability, status_only_accepts, validate_rest_response


class HuntLabWordPressDiagnosticsTests(unittest.TestCase):
    def test_html_login_page_with_200_exposes_status_only_false_positive(self):
        body = b"<html><form id='loginform'></form></html>"
        self.assertTrue(status_only_accepts(200))
        result = validate_rest_response(status=200, content_type="text/html; charset=UTF-8", body=body)
        self.assertFalse(result.passed)
        self.assertEqual(result.reason, "unexpected_content_type")

    def test_json_post_identity_passes_same_response_contract(self):
        result = validate_rest_response(status=201, content_type="application/json; charset=UTF-8", body=b'{"id":742,"status":"publish"}', expected_id=742)
        self.assertTrue(result.passed)
        self.assertEqual(result.observed["post_id"], 742)

    def test_noindex_url_in_sitemap_fails_then_removed_url_passes(self):
        pages = [{"url":"https://example.test/private/","robots":["noindex","follow"],"canonical":"https://example.test/private/"}]
        before = b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.test/private/</loc></url></urlset>'
        after = b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        self.assertFalse(audit_indexability(pages=pages, sitemap_xml=before).passed)
        self.assertTrue(audit_indexability(pages=pages, sitemap_xml=after).passed)

    def test_indexable_page_must_be_self_canonical(self):
        pages = [{"url":"https://example.test/a/","robots":["index","follow"],"canonical":"https://example.test/b/"}]
        sitemap = b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.test/a/</loc></url></urlset>'
        result = audit_indexability(pages=pages, sitemap_xml=sitemap)
        self.assertFalse(result.passed)
        self.assertEqual(result.observed["conflicts"][0]["reason"], "indexable_url_not_self_canonical")
