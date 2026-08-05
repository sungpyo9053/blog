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

    def test_plugin_backfills_grounded_quick_summary_without_replacing_toc(self):
        php = (PLUGIN / "huntlab-article-toc.php").read_text(encoding="utf-8")
        css = (PLUGIN / "assets/article-toc.css").read_text(encoding="utf-8")

        self.assertIn("Version: 1.1.2", php)
        self.assertIn("huntlab_article_quick_summary", php)
        self.assertIn("20초 핵심 요약", php)
        self.assertIn("<strong>무엇</strong>", php)
        self.assertIn("<strong>왜</strong>", php)
        self.assertIn("<strong>어떻게</strong>", php)
        self.assertIn("get_the_excerpt()", php)
        self.assertIn("문제 또는 판단 기준을 놓치지 않기 위해서", php)
        self.assertIn("array_slice( $steps, 1, 3 )", php)
        self.assertIn("핵심 요약", php)
        self.assertIn("huntlab-article-quick-summary", css)
        self.assertIn(".huntlab-article-toc", css)
        self.assertIn("add_filter( 'the_content'", php)

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
