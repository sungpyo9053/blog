from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "deploy/wordpress/huntlab-warm-editorial"


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


if __name__ == "__main__":
    unittest.main()
