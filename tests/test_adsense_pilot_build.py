from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_adsense_pilot import render


class PilotBuildTests(unittest.TestCase):
    def test_render_produces_utf8_lf_with_exactly_one_final_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "pilot.md"
            source.write_bytes(
                b"---\r\npost_id: 132\r\ntitle: pagination\r\n---\r\n\r\n"
                b"Paragraph.\r\n\r\n## Result\r\n\r\nDone.\r\n\r\n"
            )
            metadata, rendered = render(source)

        self.assertEqual(metadata["post_id"], 132)
        rendered.decode("utf-8")
        self.assertNotIn(b"\r", rendered)
        self.assertTrue(rendered.endswith(b"\n"))
        self.assertFalse(rendered.endswith(b"\n\n"))


if __name__ == "__main__":
    unittest.main()
