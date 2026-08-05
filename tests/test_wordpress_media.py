from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from PIL import Image

from publisher.wordpress import WordPressClient


class RecordingWordPressClient(WordPressClient):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append({"method": method, "path": path, **kwargs})
        if path == "media":
            return {"id": 42}
        return {"id": 42, "alt_text": kwargs["payload"]["alt_text"]}


class MediaSearchWordPressClient(WordPressClient):
    def __init__(self) -> None:
        self.paths: list[str] = []

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        self.paths.append(path)
        return [
            {
                "id": 259,
                "slug": "body-1-10-2",
                "source_url": (
                    "https://huntlab.app/wp-content/uploads/2026/08/body-1-10.webp"
                ),
            },
            {
                "id": 999,
                "slug": "body-1-10-copy",
                "source_url": (
                    "https://huntlab.app/wp-content/uploads/2026/08/body-1-10-2.webp"
                ),
            },
        ]


class WordPressMediaTests(unittest.TestCase):
    def test_png_is_uploaded_as_smaller_webp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "thumbnail.png"
            Image.new("RGB", (256, 256), (18, 34, 62)).save(source, "PNG")
            client = RecordingWordPressClient()

            result = client.upload_media(source, alt_text="대표 이미지")

            upload = client.calls[0]
            self.assertEqual(upload["content_type"], "image/webp")
            self.assertIn('filename="thumbnail.webp"', upload["extra_headers"]["Content-Disposition"])
            self.assertLess(len(upload["body"]), source.stat().st_size)
            self.assertEqual(result["alt_text"], "대표 이미지")

    def test_find_media_searches_filename_and_selects_exact_source_url(self) -> None:
        client = MediaSearchWordPressClient()
        source_url = (
            "https://huntlab.app/wp-content/uploads/2026/08/body-1-10.webp"
        )

        result = client.find_media_by_source_url(source_url)

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 259)
        request_url = urlparse(client.paths[0])
        query = parse_qs(request_url.query)
        self.assertEqual(request_url.path, "media")
        self.assertEqual(query["search"], ["body-1-10"])
        self.assertEqual(query["per_page"], ["100"])
        self.assertEqual(query["context"], ["edit"])
        self.assertNotIn("slug", query)


if __name__ == "__main__":
    unittest.main()
