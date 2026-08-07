from __future__ import annotations

import unittest
from datetime import date

from scripts.apply_index_discovery_action import (
    add_discovery_link,
    choose_related_source,
    normalize_url_for_compare,
    parse_report,
)


class IndexDiscoveryActionTests(unittest.TestCase):
    def test_report_requires_exact_date_and_eligible_action(self):
        report = (
            "- generated_at: `2026-08-07T01:00:00+09:00`\n"
            "- index_discovery_action: `ELIGIBLE_REVIEW`\n"
            "- index_discovery_target: `https://huntlab.app/target/`\n"
        )
        self.assertEqual(
            parse_report(report, date(2026, 8, 7)),
            "https://huntlab.app/target/",
        )
        with self.assertRaises(ValueError):
            parse_report(report, date(2026, 8, 8))

    def test_related_source_requires_shared_tag_and_skips_existing_link(self):
        target = {
            "id": 9,
            "link": "https://huntlab.app/target/",
            "tags": [3, 4],
            "categories": [2],
        }
        posts = [
            target,
            {
                "id": 10,
                "status": "publish",
                "tags": [8],
                "categories": [2],
                "content": {"raw": "unrelated"},
            },
            {
                "id": 11,
                "status": "publish",
                "tags": [3],
                "categories": [2],
                "content": {"raw": "related"},
            },
        ]
        source, shared = choose_related_source(posts, target)
        self.assertEqual(source["id"], 11)
        self.assertEqual(shared, {3})

    def test_url_comparison_ignores_percent_hex_case(self):
        upper = "https://huntlab.app/7%EC%9B%94-next-js/"
        lower = "https://huntlab.app/7%ec%9b%94-next-js"
        self.assertEqual(
            normalize_url_for_compare(upper),
            normalize_url_for_compare(lower),
        )

    def test_link_is_inserted_once_into_existing_related_section(self):
        target = {
            "id": 9,
            "link": "https://huntlab.app/target/",
            "title": {"rendered": "Target &amp; Guide"},
        }
        original = (
            "본문\n<!-- huntlab-related-links:v1 -->\n"
            "<section><ul><li>기존</li></ul></section>"
        )
        updated = add_discovery_link(original, target)
        self.assertEqual(updated.count("https://huntlab.app/target/"), 1)
        self.assertIn("Target &amp; Guide", updated)
        self.assertEqual(add_discovery_link(updated, target), updated)


if __name__ == "__main__":
    unittest.main()
