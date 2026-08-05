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
        self.assertIn("is_home() || is_front_page()", php)

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
