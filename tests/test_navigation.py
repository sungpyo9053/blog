from __future__ import annotations

import unittest

from publisher.navigation import MENU_LOCATIONS, build_menu_spec, validate_menu_state


class NavigationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.categories = {
            "Tech": {"count": 10, "link": "https://huntlab.app/category/tech/"},
            "AI": {"count": 4, "link": "https://huntlab.app/category/ai/"},
            "Build Log": {
                "count": 4,
                "link": "https://huntlab.app/category/build-log/",
            },
            "Economy": {
                "count": 3,
                "link": "https://huntlab.app/category/economy/",
            },
            "Society": {
                "count": 2,
                "link": "https://huntlab.app/category/society/",
            },
            "Politics": {
                "count": 0,
                "link": "https://huntlab.app/category/politics/",
            },
            "Hot Issue": {
                "count": 2,
                "link": "https://huntlab.app/category/hot-issue/",
            },
        }

    def test_build_menu_omits_empty_category_and_preserves_pages(self) -> None:
        specs = build_menu_spec("https://huntlab.app/", self.categories)
        titles = [spec.title for spec in specs]

        self.assertEqual(titles[0], "카테고리")
        self.assertNotIn("Politics", titles)
        self.assertIn("Tech", titles)
        self.assertIn("편집 및 AI 활용 원칙", titles)
        self.assertEqual(
            next(spec for spec in specs if spec.title == "Tech").parent_title,
            "카테고리",
        )

    def test_validate_menu_accepts_expected_hierarchy(self) -> None:
        specs = build_menu_spec("https://huntlab.app", self.categories)
        ids = {spec.title: index for index, spec in enumerate(specs, start=100)}
        items = [
            {
                "id": ids[spec.title],
                "title": {"raw": spec.title},
                "url": spec.url,
                "parent": ids.get(spec.parent_title or "", 0),
            }
            for spec in specs
        ]

        self.assertEqual(validate_menu_state(items, MENU_LOCATIONS, specs), [])

    def test_validate_menu_reports_location_and_parent_drift(self) -> None:
        specs = build_menu_spec("https://huntlab.app", self.categories)
        items = [
            {
                "id": index,
                "title": {"raw": spec.title},
                "url": spec.url,
                "parent": 0,
            }
            for index, spec in enumerate(specs, start=100)
        ]

        errors = validate_menu_state(items, ("primary",), specs)

        self.assertIn("missing_locations:mobile", errors)
        self.assertIn("parent_mismatch:Tech", errors)


if __name__ == "__main__":
    unittest.main()
