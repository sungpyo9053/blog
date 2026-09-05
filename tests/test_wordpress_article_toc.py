from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "deploy/wordpress/huntlab-article-toc"


class HuntLabArticleTocTests(unittest.TestCase):
    def test_plugin_builds_toc_from_h2_and_h3_without_editing_posts(self):
        php = (PLUGIN / "huntlab-article-toc.php").read_text(encoding="utf-8")
        self.assertIn("Plugin Name: HuntLab Article Table of Contents", php)
        self.assertIn("is_singular( 'post' )", php)
        self.assertIn("<h([23])", php)
        self.assertIn("huntlab-section-", php)
        self.assertIn("한눈에 보기", php)

    def test_plugin_never_generates_an_unauthored_quick_summary(self):
        php = (PLUGIN / "huntlab-article-toc.php").read_text(encoding="utf-8")
        css = (PLUGIN / "assets/article-toc.css").read_text(encoding="utf-8")

        self.assertIn("Version: 1.2.0", php)
        self.assertNotIn("huntlab_article_quick_summary", php)
        self.assertNotIn("20초 핵심 요약", php)
        self.assertNotIn("huntlab-article-quick-summary", php)
        self.assertIn("huntlab-article-quick-summary", css)
        self.assertIn(".huntlab-article-toc", css)
        self.assertIn("add_filter( 'the_content'", php)

    def test_authored_headings_are_preserved_and_briefing_post_type_is_out_of_scope(self):
        php = (PLUGIN / "huntlab-article-toc.php").read_text(encoding="utf-8")

        self.assertIn("return '<h' . $level . $attributes . '>' . $inner_html . '</h' . $level . '>';", php)
        self.assertIn("is_singular( 'post' )", php)
        self.assertNotIn("is_singular( 'hunt_briefing' )", php)

    def test_toc_has_responsive_sticky_navigation_and_active_section(self):
        css = (PLUGIN / "assets/article-toc.css").read_text(encoding="utf-8")
        js = (PLUGIN / "assets/article-toc.js").read_text(encoding="utf-8")
        self.assertIn("@media (min-width: 1360px)", css)
        self.assertIn("position: fixed", css)
        self.assertIn("scroll-margin-top", css)
        self.assertIn("IntersectionObserver", js)
        self.assertIn("aria-current", js)
        self.assertIn("document.body.appendChild(toc)", js)
        self.assertIn("placeholder.parentNode.insertBefore", js)


if __name__ == "__main__":
    unittest.main()
