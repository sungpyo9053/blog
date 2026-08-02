from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image

from publisher.wordpress import WordPressClient


class RecordingWordPressClient(WordPressClient):
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"method": method, "path": path, **kwargs})
        if path == "media":
            return {"id": 42}
        return {"id": 42, "alt_text": kwargs["payload"]["alt_text"]}


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


if __name__ == "__main__":
    unittest.main()
