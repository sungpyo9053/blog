from __future__ import annotations

import unittest

from scripts.adsense_p0_scope import NOINDEX_CATEGORY_SLUGS, NOINDEX_POST_IDS
from scripts.apply_adsense_p0 import (
    ROBOTS_PATCH,
    stable_post_identity,
)


class AdSenseP0Tests(unittest.TestCase):
    def test_exact_reviewed_scope(self):
        self.assertEqual(len(NOINDEX_POST_IDS), 37)
        self.assertEqual(len(NOINDEX_CATEGORY_SLUGS), 6)

    def test_follow_is_preserved(self):
        self.assertTrue(ROBOTS_PATCH["noindex"])
        self.assertFalse(ROBOTS_PATCH["nofollow"])

    def test_identity_contract_ignores_only_seo_robots(self):
        post = {
            "id": 46,
            "slug": "sample",
            "link": "https://huntlab.app/sample/",
            "featured_media": 10,
            "content": {"raw": "<p>same</p>"},
            "aioseo_meta_data": {"canonical_url": None, "robots_noindex": False},
        }
        before = stable_post_identity(post)
        post["aioseo_meta_data"]["robots_noindex"] = True
        self.assertEqual(before, stable_post_identity(post))


if __name__ == "__main__":
    unittest.main()
