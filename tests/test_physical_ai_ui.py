from pathlib import Path
import json
import os
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "deploy/wordpress/huntlab-warm-editorial"
PHP = shutil.which("php")
PHP_COMMAND = [PHP] if PHP else []
if not PHP_COMMAND and os.environ.get("HUNTLAB_PHP_DOCKER_IMAGE"):
    PHP_COMMAND = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                   "--security-opt", "no-new-privileges", "-v", f"{ROOT}:{ROOT}:ro", "-w", str(ROOT),
                   os.environ["HUNTLAB_PHP_DOCKER_IMAGE"], "php"]
SLUGS = ("physical-ai-basics", "physical-ai-principles", "physical-ai-frameworks", "physical-ai-experiments")


class PhysicalAIUIContractTests(unittest.TestCase):
    def test_routes_and_category_names_match_pipeline(self):
        from scripts.run_daily_pipeline import PHYSICAL_AI_CATEGORIES
        template = (PLUGIN / "physical-home.php").read_text()
        router = (PLUGIN / "reader-tools.php").read_text()
        for slug in SLUGS:
            self.assertIn(slug, template)
            self.assertIn(slug, router)
        for category in PHYSICAL_AI_CATEGORIES:
            self.assertIn(category, template)
        self.assertLess(router.index("'/physical-home.php'"), router.index("'/library-home.php'"))
        for slug in ("rest-api-publishing", "automation-testing", "wordpress-operations"):
            self.assertIn(slug, router)
            self.assertIn("/category/" + slug + "/", template)

    def test_query_is_published_and_category_bounded_with_honest_empty_state(self):
        template = (PLUGIN / "physical-home.php").read_text()
        self.assertIn("$lessons = $query_ids ? new WP_Query", template)
        self.assertIn("'post_status' => 'publish'", template)
        self.assertIn("'category__in' => $query_ids", template)
        self.assertIn("$selected ? ( isset( $terms[ $selected ] )", template)
        self.assertIn("get_query_var( 'page' )", template)
        self.assertIn("첫 글 준비 중", template)
        self.assertIn("기존 운영 글은 아래 아카이브", template)
        self.assertNotIn("99점", template)
        self.assertNotIn("wp_delete_post", template)

    def test_compact_intro_uses_existing_article_instead_of_decorative_hero(self):
        template = (PLUGIN / "physical-home.php").read_text()
        self.assertNotIn("physical-ai-hero.png", template)
        self.assertIn("get_the_post_thumbnail( $featured", template)
        self.assertIn("has_post_thumbnail( $featured )", template)
        self.assertIn("get_the_excerpt( $featured )", template)
        self.assertLess(template.index('class="huntlab-featured-lesson"'), template.index('id="learning-path"'))

    def test_navigation_landmarks_mobile_layout_and_metadata(self):
        template = (PLUGIN / "physical-home.php").read_text()
        css = (PLUGIN / "assets/physical-ai.css").read_text()
        for anchor in ("learning-path", "physical-articles", "operations-archive"):
            self.assertIn(f'id="{anchor}"', template)
            tabs = (ROOT / "deploy/wordpress/huntlab-category-tabs/huntlab-category-tabs.php").read_text()
            self.assertIn("/#" + anchor, tabs)
        self.assertNotIn("/#hunt-news-latest-verified", tabs)
        # Kadence get_header() opens the surrounding main landmark.
        self.assertIn('<div id="main"', template)
        self.assertNotIn('<main ', template)
        self.assertIn(":focus-visible", css)
        self.assertIn("@media(max-width:540px)", css)
        self.assertIn("grid-template-columns:1fr", css)
        php = (PLUGIN / "huntlab-warm-editorial.php").read_text()
        self.assertIn("피지컬 AI, 기초에서 실습까지 - HuntLab", php)
        organization = php[php.index("$organization     = array("):]
        self.assertIn("'description' => '피지컬 AI의 기초와 원리, 도구와 실습을 설명하고", organization)
        self.assertIn("기존 WordPress 운영 기록도 보존합니다.", organization)

    def test_briefing_does_not_reuse_retired_home_copy(self):
        router = (PLUGIN / "reader-tools.php").read_text()
        self.assertIn("function huntlab_hide_retired_briefing_intro", router)
        self.assertIn("add_action( 'wp', 'huntlab_hide_retired_briefing_intro', 30 )", router)
        self.assertIn("function huntlab_site_page_description", router)


@unittest.skipUnless(PHP_COMMAND, "PHP CLI unavailable: template runtime and syntax are not verified locally")
class PhysicalAIUIRuntimeTests(unittest.TestCase):
    def render(self, scenario):
        result = subprocess.run([*PHP_COMMAND, str(ROOT / "tests/fixtures/physical-home-harness.php"),
                                 str(PLUGIN / "physical-home.php"), scenario],
                                check=True, capture_output=True, text=True)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_php_syntax(self):
        for path in (PLUGIN / "physical-home.php", PLUGIN / "physical-learning.php", PLUGIN / "reader-tools.php", PLUGIN / "huntlab-warm-editorial.php"):
            subprocess.run([*PHP_COMMAND, "-l", str(path)], check=True, capture_output=True, text=True)

    def learning(self, scenario):
        result = subprocess.run([*PHP_COMMAND, str(ROOT / "tests/fixtures/physical-learning-harness.php"),
                                 str(PLUGIN / "physical-learning.php"), scenario],
                                check=True, capture_output=True, text=True)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_learning_links_only_real_public_unprotected_category_posts(self):
        result = self.learning("normal")
        self.assertEqual(len(result["starts"]), 4)
        self.assertIn("post-773/", result["html"])
        self.assertIn("post-771/", result["html"])
        self.assertIn("&lt;unsafe&gt;", result["html"])
        self.assertNotIn("<unsafe>", result["html"])
        for scenario in ("missing", "draft", "password", "wrong-category"):
            result = self.learning(scenario)
            self.assertNotIn("physical-ai-principles", result["starts"])
            self.assertNotIn("post-773/", result["html"])

    def test_learning_never_changes_briefing_feed_rest_or_secondary_content(self):
        for scenario in ("briefing", "feed", "rest", "outside-loop", "secondary", "legacy"):
            self.assertEqual(self.learning(scenario)["html"], "ORIGINAL")

    def test_new_physical_post_gets_learning_entry_not_fake_sequence(self):
        html = self.learning("new-post")["html"]
        self.assertTrue(html.startswith("ORIGINAL"))
        self.assertIn("/#learning-path", html)
        self.assertNotIn("다음 학습", html)
        self.assertNotIn("이전 학습", html)

    def test_home_starting_links_do_not_replace_dynamic_latest_query(self):
        result = self.render("published-starts")
        self.assertEqual(result["html"].count('class="huntlab-starting-post"'), 4)
        self.assertIn("최근 공개한 글", result["html"])
        self.assertIn("&lt;script&gt;", result["html"])
        self.assertEqual(len(result["queries"]), 1)
        self.assertEqual(result["queries"][0]["posts_per_page"], 12)
        self.assertNotIn("post__in", result["queries"][0])
        self.assertIn('existing-diagram.png', result["html"])
        self.assertLess(result["html"].index('class="huntlab-featured-lesson"'), result["html"].index('id="learning-path"'))
        self.assertNotIn('class="huntlab-featured-lesson"', self.render("absent")["html"])
        self.assertNotIn('class="huntlab-featured-lesson"', self.render("selected")["html"])

    def test_missing_categories_never_query_all_posts(self):
        for scenario in ("absent", "missing-selected"):
            result = self.render(scenario)
            self.assertEqual(result["queries"], [])
            self.assertIn("시리즈를 준비", result["html"])

    def test_empty_existing_category_is_not_faked_as_a_course(self):
        result = self.render("empty")
        self.assertEqual(result["queries"][0]["category__in"], [901])
        self.assertIn("첫 글 준비 중", result["html"])
        self.assertNotIn("편 읽기", result["html"])

    def test_selected_category_escaping_and_static_front_pagination(self):
        result = self.render("selected")
        self.assertEqual(result["queries"][0]["category__in"], [901])
        self.assertNotIn("<script>unsafe()", result["html"])
        self.assertIn("&lt;script&gt;", result["html"])
        self.assertEqual(self.render("page")["queries"][0]["paged"], 2)
