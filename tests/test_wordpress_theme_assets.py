from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "deploy/wordpress/huntlab-warm-editorial"
CATEGORY_TABS = (
    ROOT / "deploy/wordpress/huntlab-category-tabs/huntlab-category-tabs.php"
)


class HuntLabWarmEditorialTests(unittest.TestCase):
    def test_plugin_loads_a_versioned_local_stylesheet(self):
        php = (PLUGIN / "huntlab-warm-editorial.php").read_text(encoding="utf-8")
        self.assertIn("Plugin Name: Hunt News Warm Editorial Theme", php)
        self.assertIn("wp_enqueue_style", php)
        self.assertIn("assets/warm-editorial.css", php)
        self.assertIn("filemtime", php)
        self.assertIn("huntlab-warm-editorial-late-overrides", php)
        self.assertIn("add_action( 'wp_head'", php)
        self.assertIn("huntlab_warm_editorial_home_intro", php)
        self.assertIn("복잡한 변화가", php)
        self.assertIn("hunt-news-life-impact-hero.webp", php)
        self.assertIn("뉴스를 읽고도 남는 세 가지", php)
        self.assertIn("'label'       => '경제'", php)
        self.assertIn("'label'       => '사회'", php)
        self.assertIn("Hunt News 콘텐츠 원칙", php)
        self.assertIn("hunt_news_translate_archive_labels", php)
        self.assertIn("hunt_news_remove_legacy_category_hero", php)
        self.assertIn("remove_action( 'kadence_hero_header', 'Kadence\\\\hero_title' )", php)
        self.assertIn("'Read More'       => '더 읽기'", php)
        self.assertIn("'Continue'        => '계속 읽기'", php)
        self.assertIn("'Page navigation' => '페이지 탐색'", php)
        self.assertIn("'Similar Posts'   => '비슷한 글'", php)
        self.assertIn("'Comment *'              => '댓글 *'", php)
        self.assertIn("is_home() || is_front_page() || is_category()", php)

    def test_palette_keeps_warm_surfaces_and_accessible_ink(self):
        css = (PLUGIN / "assets/warm-editorial.css").read_text(encoding="utf-8")
        self.assertIn("--huntlab-canvas: #f5efe6", css)
        self.assertIn("--huntlab-surface: #fffaf2", css)
        self.assertIn("--huntlab-ink: #292621", css)
        self.assertIn("--huntlab-terracotta: #a95f49", css)
        self.assertIn(".huntlab-category-tabs__link.is-active", css)
        self.assertIn(".huntlab-home-intro", css)
        self.assertIn(".hunt-news-reading-guide", css)
        self.assertIn(".hunt-news-category-grid", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)

    def test_code_blocks_keep_readable_text_and_horizontal_scroll(self):
        php = (PLUGIN / "huntlab-warm-editorial.php").read_text(encoding="utf-8")
        css = (PLUGIN / "assets/warm-editorial.css").read_text(encoding="utf-8")

        self.assertIn("Version: 2.4.0", php)
        self.assertIn(".single-content pre code", css)
        self.assertIn("color: #f7f3ea !important", css)
        self.assertIn("color: inherit !important", css)
        self.assertIn("overflow-x: auto", css)
        self.assertIn("white-space: pre", css)

    def test_home_prioritizes_latest_posts_and_unifies_schema_identity(self):
        php = (PLUGIN / "huntlab-warm-editorial.php").read_text(encoding="utf-8")
        css = (PLUGIN / "assets/warm-editorial.css").read_text(encoding="utf-8")

        self.assertIn("main.parentNode.insertBefore(section,main.nextSibling)", php)
        self.assertIn("Hunt News · 생활 변화 설명서", php)
        self.assertIn("aioseo_schema_output", php)
        self.assertIn("Organization", php)
        self.assertIn("Hunt News 편집팀", php)
        self.assertIn("hunt_news_editorial_author_link", php)
        self.assertIn("home_url( '/about/' )", php)
        self.assertIn("kadence_author_use_profile_link", php)
        self.assertIn("hunt_news_editorial_author_name", php)
        self.assertIn("https://github.com/sungpyo9053/blog", php)
        self.assertIn("aspect-ratio: 2.4 / 1", css)
        self.assertIn("white-space: nowrap", css)

    def test_real_read_signal_requires_visible_time_and_scroll_depth(self):
        php = (PLUGIN / "huntlab-warm-editorial.php").read_text(encoding="utf-8")

        self.assertIn("huntlab_engaged_read", php)
        self.assertIn("document.visibilityState!=='visible'", php)
        self.assertIn("activeMs>=30000", php)
        self.assertIn("maxDepth>=25", php)
        self.assertIn("window.gtag||window.__gtagTracker", php)
        self.assertIn("huntlab_internal_click", php)
        self.assertIn("destination.origin!==window.location.origin", php)
        self.assertIn("link_area", php)
        self.assertIn("huntlab_article_complete", php)
        self.assertIn("huntlab_article_share", php)
        self.assertIn("huntlab_return_visit", php)
        self.assertIn("data-huntlab-share", php)
        self.assertIn("분야 더 보기", php)
        self.assertIn("get_category_link", php)
        self.assertIn("activeMs>=45000", php)

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

    def test_huntlab_site_icon_is_square_and_search_engine_ready(self):
        png = PLUGIN / "assets/huntlab-site-icon.png"
        svg = PLUGIN / "assets/huntlab-site-icon.svg"

        self.assertTrue(png.is_file())
        self.assertTrue(svg.is_file())
        with Image.open(png) as image:
            self.assertEqual((512, 512), image.size)
            self.assertEqual("PNG", image.format)

        svg_text = svg.read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 96 96"', svg_text)
        self.assertIn("Hunt News의 강아지 로고", svg_text)

    def test_category_tabs_include_hunt_news_sections(self):
        php = CATEGORY_TABS.read_text(encoding="utf-8")
        for slug in (
            "life",
            "economy",
            "real-estate",
            "society",
            "politics",
            "culture-entertainment",
            "it",
        ):
            self.assertIn(slug, php)
        self.assertNotIn("0 === (int) $category->count", php)
        self.assertIn("Version: 2.0.1", php)
        self.assertIn("hunt_news_redirect_legacy_categories", php)
        self.assertIn("wp_safe_redirect( $target, 301 )", php)
        self.assertIn("width:100%;min-height:40px;flex-direction:column", php)
        self.assertIn("white-space:normal;overflow-wrap:anywhere", php)
        self.assertIn("min-height:44px", php)

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
