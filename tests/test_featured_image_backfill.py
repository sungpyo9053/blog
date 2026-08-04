import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from scripts.backfill_featured_images import load_manifest, verify_targets


class FakeClient:
    def get_post(self, post_id):
        return {"id": post_id, "slug": "matched", "featured_media": 7, "status": "publish"}


class FeaturedImageBackfillTests(unittest.TestCase):
    def test_manifest_requires_existing_unique_images(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (1600, 900), "white").save(root / "image.webp")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    [
                        {
                            "post_id": 1,
                            "slug": "matched",
                            "title": "Title",
                            "image": "image.webp",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            items = load_manifest(manifest)
            self.assertEqual(items[0]["resolved_image"], (root / "image.webp").resolve())

    def test_target_identity_is_checked_before_update(self):
        with TemporaryDirectory() as directory:
            image = Path(directory) / "image.webp"
            Image.new("RGB", (1600, 900), "white").save(image)
            items = [
                {
                    "post_id": 1,
                    "slug": "matched",
                    "title": "Title",
                    "image": "image.webp",
                    "resolved_image": image,
                }
            ]
            verified = verify_targets(FakeClient(), items)
            self.assertEqual(verified[0]["old_featured_media"], 7)


if __name__ == "__main__":
    unittest.main()
