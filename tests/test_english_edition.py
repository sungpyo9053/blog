import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from scripts.english_edition import schedule_english, write_english


def topic(root, article, meta=None):
    root = Path(root)
    exp = root / "experiment"
    exp.mkdir()
    (exp / "experiment.py").write_text("HZ = 10.0")
    (exp / "plan.md").write_text("predict 0.4")
    (exp / "results.json").write_text(json.dumps({"runs": [{"stdout": '{"t": 0.075}'}]}))

    def runner(prompt):
        (root / "en" / "article.html").write_text(article)
        (root / "en" / "meta.json").write_text(json.dumps(meta or {"title": "T", "slug": "a-b", "excerpt": "e"}))
    return root, runner


class EnglishEditionTests(unittest.TestCase):
    def test_gated_article_is_scheduled_in_korean_slot(self):
        with tempfile.TemporaryDirectory() as d:
            root, runner = topic(d, "<!-- measured:start -->0.075 s vs 0.4 s<!-- measured:end -->")
            self.assertTrue(write_english(root, "a-b", None, runner=runner))
            calls = []
            client = SimpleNamespace(request=lambda *a, **k: calls.append((a, k)) or {"id": 9})
            slot = datetime(2026, 10, 5, 10, tzinfo=ZoneInfo("Asia/Seoul"))
            self.assertEqual(schedule_english(root, 827, slot, client), 9)
            payload = calls[0][1]["payload"]
            self.assertEqual((payload["status"], payload["date"], payload["meta"]), ("future", "2026-10-05T10:00:00", {"ko_post_id": 827}))

    def test_invented_number_is_rejected_and_never_scheduled(self):
        with tempfile.TemporaryDirectory() as d:
            root, runner = topic(d, "<!-- measured:start -->0.055 s<!-- measured:end -->")
            with self.assertRaises(ValueError):
                write_english(root, "a-b", None, runner=runner)
            self.assertIsNone(schedule_english(root, 1, datetime(2026, 1, 1), None))

    def test_no_experiment_means_no_english(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(write_english(Path(d), "a-b", None, runner=lambda p: None))


if __name__ == "__main__":
    unittest.main()
