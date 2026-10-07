import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from scripts.backfill_measured import insert_section, pick, run

NOW = datetime(2026, 10, 7, 16, 10, tzinfo=ZoneInfo("Asia/Seoul"))
POST = {"post_id": 7, "slug": "s", "title": "T", "link": "https://huntlab.app/s/",
        "content": "<p>body</p>\n<h2>참고 링크</h2><ul></ul>"}


def executor(command, **_):
    if command[:2] == ["docker", "image"]:
        return SimpleNamespace(returncode=0, stdout="d", stderr="")
    if "/work/experiment.py" not in command[-1]:
        return SimpleNamespace(returncode=0, stdout="jazzy Python 3.12.3 7.1", stderr="")
    return SimpleNamespace(returncode=0, stdout='{"count": 4, "t": 0.075}', stderr="")


def stage_writing(section):
    def stage(name, prompt):
        work = Path(prompt.split("'")[1]).parent
        if name == "Experiment Agent":
            (work / "experiment/experiment.py").write_text("HZ = 10.0")
            (work / "experiment/plan.md").write_text("predict 5")
        else:
            (work / "section.html").write_text(section)
    return stage


class BackfillTests(unittest.TestCase):
    def test_pick_skips_measured_and_attempted(self):
        measured = {**POST, "post_id": 1, "content": '<h2 id="measured-x">'}
        self.assertEqual(pick([measured, POST], {}), POST)
        self.assertIsNone(pick([POST], {"7": {}}))

    def test_insert_before_reference_links(self):
        self.assertEqual(insert_section(POST["content"], "<h2>M</h2>"), "<p>body</p>\n<h2>M</h2>\n\n<h2>참고 링크</h2><ul></ul>")

    def test_default_posts_read_inventory_contents(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            snapshot = Path(d) / "inventory.json"
            snapshot.write_text(json.dumps({"posts": []}))
            seen = []
            with mock.patch("scripts.run_evidence_deep_article.refresh_inventory", return_value=snapshot), \
                    mock.patch("scripts.run_weekly_editorial.eligible_posts", side_effect=lambda c, inv: seen.append(inv) or []):
                result = run(NOW, client=SimpleNamespace(), state_path=Path(d) / "state.json", work_root=Path(d))
        self.assertEqual(seen, [{"posts": []}])
        self.assertEqual(result, {"status": "nothing_to_backfill"})

    def run_with(self, section):
        with tempfile.TemporaryDirectory() as d:
            updates, sent = [], []
            client = SimpleNamespace(update_post=lambda pid, payload, status: updates.append((pid, payload, status)))
            result = run(NOW, client=client, posts=[POST], stage=stage_writing(section), executor=executor,
                         publish=lambda *a: "rev", notify=sent.append, state_path=Path(d) / "state.json",
                         work_root=Path(d))
            state = json.loads((Path(d) / "state.json").read_text())
            return result, updates, sent, state

    def test_measured_section_is_inserted_with_repro_link(self):
        ok = '<h2 id="measured-2026-10-07">실측</h2><!-- measured:start -->0.075초<!-- measured:end -->'
        result, updates, sent, state = self.run_with(ok)
        self.assertEqual(result["status"], "added")
        self.assertIn("experiments/s", updates[0][1]["content"])
        self.assertLess(updates[0][1]["content"].index("measured-2026-10-07"), updates[0][1]["content"].index("참고 링크"))
        self.assertEqual(state["attempted"]["7"]["status"], "added")
        self.assertIn("추가 완료", sent[0])

    def test_invented_number_fails_without_touching_post(self):
        bad = '<h2 id="measured-2026-10-07">실측</h2><!-- measured:start -->0.055초<!-- measured:end -->'
        result, updates, sent, state = self.run_with(bad)
        self.assertEqual((result["status"], updates), ("failed", []))
        self.assertTrue(state["attempted"]["7"]["status"].startswith("failed:"))


if __name__ == "__main__":
    unittest.main()
