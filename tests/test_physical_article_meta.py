"""Execute PHP harness where PHP exists; source boundary tests always run."""
import json, shutil, subprocess, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PHP=shutil.which('php')
MODULE=ROOT/'deploy/wordpress/huntlab-warm-editorial/physical-article-meta.php'
HARNESS=ROOT/'tests/fixtures/physical-article-meta-harness.php'

class ArticleMeta(unittest.TestCase):
    def test_display_only_source(self):
        source=MODULE.read_text()
        for forbidden in ['wp_update_post(', 'update_post_meta(', 'wp_insert_post(', '검증완료', '99점', 'get_the_author(']:
            self.assertNotIn(forbidden,source)
        self.assertIn("get_post_datetime( $post, 'date' )",source)
        self.assertIn("get_post_datetime( $post, 'modified' )",source)
        self.assertIn('hunt_news_is_verified_case',source)

    @unittest.skipUnless(PHP,'PHP runtime absent locally; run harness on deployment host')
    def test_render_contract(self):
        def run(scenario):
            return json.loads(subprocess.check_output([PHP,str(HARNESS),str(MODULE),scenario],text=True))
        for scenario in ['rest','feed','admin','briefing','outside-loop','secondary','legacy','verified-case','draft','password','missing']:
            with self.subTest(scenario=scenario):
                self.assertEqual(run(scenario)['html'],'<p>ORIGINAL &amp; RAW</p>')
        normal=run('normal')
        self.assertEqual(normal['html'],normal['twice'])
        self.assertTrue(normal['html'].endswith('<p>ORIGINAL &amp; RAW</p>'))
        self.assertIn('2026-09-17T10:01:02+09:00',normal['html'])
        self.assertIn('2026-09-20T14:01:02+09:00',normal['html'])
        self.assertEqual(normal['html'].count('<time '),2)
        self.assertEqual(run('same-date')['html'].count('<time '),1)
        self.assertEqual(run('missing-date')['html'].count('<time '),0)

if __name__=='__main__': unittest.main()
