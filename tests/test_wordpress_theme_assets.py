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

    def test_palette_keeps_warm_surfaces_and_accessible_ink(self):
        css = (PLUGIN / "assets/warm-editorial.css").read_text(encoding="utf-8")
        self.assertIn("--huntlab-canvas: #f5efe6", css)
        self.assertIn("--huntlab-surface: #fffaf2", css)
        self.assertIn("--huntlab-ink: #292621", css)
        self.assertIn("--huntlab-terracotta: #a95f49", css)
        self.assertIn(".huntlab-category-tabs__link.is-active", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)


if __name__ == "__main__":
    unittest.main()
