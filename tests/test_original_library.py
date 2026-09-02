from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.bootstrap_original_library import apply_plan, build_plan


class FakeClient:
    def __init__(self) -> None:
        self.created = False
        self.updates = []

    def get_post(self, post_id):
        return {
            "id": post_id,
            "slug": f"post-{post_id}",
            "status": "publish",
            "link": f"https://huntlab.app/post-{post_id}/",
            "categories": [7],
        }

    def request(self, method, path, *, payload=None, expected=(200,)):
        if path.startswith("categories?"):
            return []
        if path == "categories":
            self.created = True
            return {"id": 274, "slug": "technical-explainer"}
        self.updates.append((path, payload))
        return {"categories": payload["categories"]}


class OriginalLibraryTests(unittest.TestCase):
    def test_apply_appends_category_and_preserves_existing_taxonomy(self):
        client = FakeClient()
        plan = build_plan(client, [619, 622])
        with tempfile.TemporaryDirectory() as tmp:
            backup_dir = Path(tmp)
            applied = apply_plan(client, plan, backup_dir=backup_dir)
            backups = list(backup_dir.glob("original-library-before-*.json"))
        self.assertTrue(client.created)
        self.assertEqual(2, len(applied))
        self.assertEqual([7, 274], client.updates[0][1]["categories"])
        self.assertEqual(1, len(backups))


if __name__ == "__main__":
    unittest.main()
