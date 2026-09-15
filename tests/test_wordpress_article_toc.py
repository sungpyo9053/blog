from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "deploy/wordpress/huntlab-article-toc"


class HuntLabArticleTocTests(unittest.TestCase):
    def test_article_layout_initializes_before_theme_fragment_measurement(self):
        php = (PLUGIN / 'huntlab-article-toc.php').read_text()
        self.assertIn("'huntlab_article_layout_before_anchor_scroll', 120", php)
        self.assertIn("! is_singular( 'post' )", php)
        self.assertIn("array( 'huntlab-article-toc', 'huntlab-code-tools' )", php)
        self.assertIn("isset( $scripts->registered[$handle] ) && wp_script_is( $handle, 'enqueued' )", php)
        self.assertIn("$scripts->registered['kadence-navigation']->deps[] = $handle;", php)

    @unittest.skipUnless(shutil.which('php'), 'PHP is needed for dependency runtime regression')
    def test_layout_dependencies_runtime_are_scoped_existing_and_idempotent(self):
        code = '''define('ABSPATH', '/');
function add_filter(...$args) {} function add_action(...$args) {}
function is_singular($type) { return $GLOBALS['post'] && $type === 'post'; }
function wp_script_is($handle, $state) { return !empty($GLOBALS['queued'][$handle]); }
function wp_scripts() { return $GLOBALS['scripts']; }
require $argv[1];
$GLOBALS['post'] = true;
$GLOBALS['queued'] = array_fill_keys(['kadence-navigation', 'huntlab-article-toc', 'huntlab-code-tools'], true);
$theme = (object) ['deps'=>['existing-dependency']];
$GLOBALS['scripts'] = (object) ['registered'=>[
 'kadence-navigation'=>$theme, 'huntlab-article-toc'=>(object)[], 'huntlab-code-tools'=>(object)[]]];
huntlab_article_layout_before_anchor_scroll();
huntlab_article_layout_before_anchor_scroll();
if ($theme->deps !== ['existing-dependency','huntlab-article-toc','huntlab-code-tools']) exit(1);
$theme->deps = ['existing-dependency']; $GLOBALS['post'] = false;
huntlab_article_layout_before_anchor_scroll();
if ($theme->deps !== ['existing-dependency']) exit(2);
$GLOBALS['post'] = true;
unset($GLOBALS['scripts']->registered['huntlab-code-tools']);
$GLOBALS['queued']['huntlab-article-toc'] = false;
huntlab_article_layout_before_anchor_scroll();
if ($theme->deps !== ['existing-dependency']) exit(3);
$GLOBALS['queued']['kadence-navigation'] = false;
$GLOBALS['queued']['huntlab-article-toc'] = true;
huntlab_article_layout_before_anchor_scroll();
if ($theme->deps !== ['existing-dependency']) exit(4);
$GLOBALS['queued']['kadence-navigation'] = true;
unset($GLOBALS['scripts']->registered['kadence-navigation']);
huntlab_article_layout_before_anchor_scroll();
'''
        result = subprocess.run(['php', '-r', code, str(PLUGIN / 'huntlab-article-toc.php')],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reader_initial_hash_uses_official_theme_offset_without_global_override(self):
        php = (ROOT / 'deploy/wordpress/huntlab-warm-editorial/reader-tools.php').read_text()
        self.assertIn("add_filter( 'kadence_scroll_to_id_additional_offset', 'huntlab_reader_anchor_offset' )", php)
        self.assertIn("if ( is_front_page() )", php)
        self.assertIn("if ( is_singular( 'post' ) )", php)
        self.assertIn("if ( is_page( 'wordpress-response-check' ) )", php)
        for margin in (90, 112, 100):
            self.assertIn(f"return (float) $offset + {margin};", php)
        self.assertIn("return $offset;", php)

    @unittest.skipUnless(shutil.which('php'), 'PHP is needed for runtime filter regression')
    def test_reader_offset_runtime_preserves_other_pages_and_existing_offset(self):
        plugin = ROOT / 'deploy/wordpress/huntlab-warm-editorial/reader-tools.php'
        code = '''define('ABSPATH', '/');
function add_filter(...$args) {} function add_action(...$args) {} function add_shortcode(...$args) {}
function is_front_page() { return $GLOBALS['context'] === 'home'; }
function is_singular($type) { return $GLOBALS['context'] === $type; }
function is_page($slug) { return $GLOBALS['context'] === $slug; }
require $argv[1];
foreach (['home'=>90, 'post'=>112, 'wordpress-response-check'=>100] as $context=>$margin) {
    $GLOBALS['context'] = $context;
    if (huntlab_reader_anchor_offset(0) !== (float) $margin) exit(1);
    if (huntlab_reader_anchor_offset('24') !== (float) ($margin + 24)) exit(2);
}
foreach (['about', 'category', 'hunt_briefing', 'attachment'] as $context) {
    $GLOBALS['context'] = $context;
    if (huntlab_reader_anchor_offset('24') !== '24') exit(3);
    if (huntlab_reader_anchor_offset(0) !== 0) exit(4);
}
'''
        result = subprocess.run(['php', '-r', code, str(plugin)],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for TOC handler regression')
    def test_toc_navigation_handlers(self):
        result = subprocess.run(['node', str(ROOT / 'tests/article_toc_test.cjs')],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_plugin_builds_toc_from_h2_and_h3_without_editing_posts(self):
        php = (PLUGIN / "huntlab-article-toc.php").read_text(encoding="utf-8")
        self.assertIn("Plugin Name: HuntLab Article Table of Contents", php)
        self.assertIn("is_singular( 'post' )", php)
        self.assertIn("<h([23])", php)
        self.assertIn("huntlab-section-", php)
        self.assertIn("목차 ' . count( $sections ) . '개 보기", php)

    def test_plugin_never_generates_an_unauthored_quick_summary(self):
        php = (PLUGIN / "huntlab-article-toc.php").read_text(encoding="utf-8")
        css = (PLUGIN / "assets/article-toc.css").read_text(encoding="utf-8")

        self.assertIn("Version: 1.3.0", php)
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
        self.assertIn("disclosure.removeAttribute('open')", js)
        self.assertIn("max-width: 767px", js)


if __name__ == "__main__":
    unittest.main()
