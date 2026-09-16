from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import unittest

from PIL import Image

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

    def test_hero_asset_dimensions_and_disclosure_are_correct(self):
        template = (PLUGIN / "physical-home.php").read_text()
        dimensions = re.search(r'width="(\d+)" height="(\d+)"', template)
        with Image.open(PLUGIN / "assets/physical-ai-hero.png") as hero:
            self.assertEqual(hero.size, tuple(map(int, dimensions.groups())))
            hero.verify()
        self.assertIn("AI 생성 개념 일러스트", template)
        self.assertIn("실제 실험 사진이 아닙니다", template)
        self.assertIn('alt="카메라', template)

    def test_navigation_landmarks_mobile_layout_and_metadata(self):
        template = (PLUGIN / "physical-home.php").read_text()
        css = (PLUGIN / "assets/physical-ai.css").read_text()
        for anchor in ("learning-path", "physical-articles", "operations-archive"):
            self.assertIn(f'id="{anchor}"', template)
            tabs = (ROOT / "deploy/wordpress/huntlab-category-tabs/huntlab-category-tabs.php").read_text()
            self.assertIn("/#" + anchor, tabs)
        self.assertNotIn("/#hunt-news-latest-verified", tabs)
        self.assertIn('<main id="main"', template)
        self.assertIn(":focus-visible", css)
        self.assertIn("@media(max-width:540px)", css)
        self.assertIn("grid-template-columns:1fr", css)
        php = (PLUGIN / "huntlab-warm-editorial.php").read_text()
        self.assertIn("피지컬 AI, 기초에서 실습까지 - HuntLab", php)


@unittest.skipUnless(PHP_COMMAND, "PHP CLI unavailable: template runtime and syntax are not verified locally")
class PhysicalAIUIRuntimeTests(unittest.TestCase):
    def render(self, scenario):
        result = subprocess.run([*PHP_COMMAND, str(ROOT / "tests/fixtures/physical-home-harness.php"),
                                 str(PLUGIN / "physical-home.php"), scenario],
                                check=True, capture_output=True, text=True)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_php_syntax(self):
        for path in (PLUGIN / "physical-home.php", PLUGIN / "reader-tools.php", PLUGIN / "huntlab-warm-editorial.php"):
            subprocess.run([*PHP_COMMAND, "-l", str(path)], check=True, capture_output=True, text=True)

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
