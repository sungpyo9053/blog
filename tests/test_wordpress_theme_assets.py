from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "deploy/wordpress/huntlab-warm-editorial"
CATEGORY_TABS = (
    ROOT / "deploy/wordpress/huntlab-category-tabs/huntlab-category-tabs.php"
)


class HuntLabWarmEditorialTests(unittest.TestCase):
    def test_plugin_loads_a_versioned_local_stylesheet(self):
        php = (PLUGIN / "huntlab-warm-editorial.php").read_text(encoding="utf-8")
        self.assertIn("Plugin Name: HuntLab Warm Editorial Theme", php)
        self.assertIn("wp_enqueue_style", php)
        self.assertIn("assets/warm-editorial.css", php)
        self.assertIn("filemtime", php)
        self.assertIn("huntlab-warm-editorial-late-overrides", php)
        self.assertIn("add_action( 'wp_head'", php)
        self.assertIn("huntlab_warm_editorial_home_intro", php)
        self.assertIn("복잡한 기술을", php)
        self.assertIn("is_home() || is_front_page() || is_category()", php)

    def test_palette_keeps_warm_surfaces_and_accessible_ink(self):
        css = (PLUGIN / "assets/warm-editorial.css").read_text(encoding="utf-8")
        self.assertIn("--huntlab-canvas: #f5efe6", css)
        self.assertIn("--huntlab-surface: #fffaf2", css)
        self.assertIn("--huntlab-ink: #292621", css)
        self.assertIn("--huntlab-terracotta: #a95f49", css)
        self.assertIn(".huntlab-category-tabs__link.is-active", css)
        self.assertIn(".huntlab-home-intro", css)
        self.assertIn(".huntlab-home-intro__dog", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)

    def test_code_blocks_keep_readable_text_and_horizontal_scroll(self):
        php = (PLUGIN / "huntlab-warm-editorial.php").read_text(encoding="utf-8")
        css = (PLUGIN / "assets/warm-editorial.css").read_text(encoding="utf-8")

        self.assertIn("Version: 1.2.0", php)
        self.assertIn(".single-content pre code", css)
        self.assertIn("color: #f7f3ea !important", css)
        self.assertIn("color: inherit !important", css)
        self.assertIn("overflow-x: auto", css)
        self.assertIn("white-space: pre", css)

    def test_category_archives_have_specific_copy_and_optimized_hero_images(self):
        php = (PLUGIN / "huntlab-warm-editorial.php").read_text(encoding="utf-8")
        css = (PLUGIN / "assets/warm-editorial.css").read_text(encoding="utf-8")
        image_dir = PLUGIN / "assets/categories"

        expected = {
            "ml-algorithms": "점수보다",
            "harness-engineering": "자동화보다",
            "system-architecture": "구성요소보다",
            "tech": "도구보다",
            "ai": "모델보다",
            "build-log": "결과보다",
            "economy": "숫자보다",
            "society": "이슈보다",
            "hot-issue": "속보보다",
        }
        for slug, copy in expected.items():
            self.assertIn(f"'{slug}'", php)
            self.assertIn(copy, php)
            image = image_dir / f"{slug}.webp"
            self.assertTrue(image.is_file(), image)
            self.assertLess(image.stat().st_size, 150_000, image)

        self.assertIn("huntlab-home-intro--category", php)
        self.assertIn("loading=\"eager\"", php)
        self.assertIn("fetchpriority=\"high\"", php)
        self.assertIn(".huntlab-home-intro__visual", css)
        self.assertIn("body.category .post-archive-hero-section", css)

    def test_category_tabs_include_huntlab_specialties(self):
        php = CATEGORY_TABS.read_text(encoding="utf-8")
        for slug in (
            "ml-algorithms",
            "harness-engineering",
            "system-architecture",
        ):
            self.assertIn(slug, php)
        self.assertIn("0 === (int) $category->count", php)
        self.assertIn("Version: 1.2.0", php)
        self.assertIn("width:100%;min-height:40px;flex-direction:column", php)
        self.assertIn("white-space:normal;overflow-wrap:anywhere", php)

    def test_category_tabs_show_counts_and_recent_badges(self):
        php = CATEGORY_TABS.read_text(encoding="utf-8")
        self.assertIn("function huntlab_category_tabs_recent_slugs()", php)
        self.assertIn("3 * DAY_IN_SECONDS", php)
        self.assertIn("wp_count_posts( 'post' )", php)
        self.assertIn("'count' => (int) $category->count", php)
        self.assertIn("huntlab-category-tabs__count", php)
        self.assertIn("huntlab-category-tabs__new", php)
        self.assertIn("최근 3일 내 새 글 있음", php)


if __name__ == "__main__":
    unittest.main()
