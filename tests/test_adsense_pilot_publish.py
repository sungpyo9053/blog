from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.publish_adsense_pilot import checked_html, main


class PilotPublishContractTests(unittest.TestCase):
    def test_dry_run_never_initializes_wordpress_or_sends_a_request(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "final.html"
            approval_path = Path(directory) / "approval.json"
            html_path.write_bytes(b"<p>pagination</p>\n")
            digest = hashlib.sha256(html_path.read_bytes()).hexdigest()
            approval_path.write_text(
                json.dumps(
                    {
                        "decision": "APPROVED",
                        "post_id": 132,
                        "sha256": digest,
                        "title": "pagination",
                    }
                ),
                encoding="utf-8",
            )
            argv = [
                "publish_adsense_pilot.py",
                "--post-id",
                "132",
                "--html",
                str(html_path),
                "--approval",
                str(approval_path),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("scripts.publish_adsense_pilot.WordPressConfig.from_environment") as config,
                patch("scripts.publish_adsense_pilot.WordPressClient") as client,
                redirect_stdout(io.StringIO()) as output,
            ):
                self.assertEqual(main(), 0)

        config.assert_not_called()
        client.assert_not_called()
        self.assertIn("status=DRY_RUN post_id=132", output.getvalue())

    def test_publisher_reads_back_the_cli_selected_post(self):
        source = Path("scripts/publish_adsense_pilot.py").read_text(encoding="utf-8")

        self.assertIn("after = client.get_post(args.post_id)", source)
        self.assertNotIn("ALLOWED_POST_ID", source)

    def test_approved_bytes_match(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.html"
            path.write_bytes(b"<p>fixed</p>\n")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            text, actual = checked_html(
                path,
                {"decision": "APPROVED", "post_id": 50, "sha256": digest},
            )
        self.assertEqual(text, "<p>fixed</p>\n")
        self.assertEqual(actual, digest)

    def test_changed_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.html"
            path.write_bytes(b"<p>changed</p>\n")
            with self.assertRaisesRegex(ValueError, "Reviewer SHA"):
                checked_html(
                    path,
                    {"decision": "APPROVED", "post_id": 50, "sha256": "0" * 64},
                )

    def test_post_132_approved_bytes_match(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.html"
            path.write_bytes(b"<p>pagination</p>\n")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            text, actual = checked_html(
                path,
                {"decision": "APPROVED", "post_id": 132, "sha256": digest},
            )
        self.assertEqual(text, "<p>pagination</p>\n")
        self.assertEqual(actual, digest)

    def test_unapproved_post_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.html"
            path.write_bytes(b"<p>other</p>\n")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "allowed pilot"):
                checked_html(
                    path,
                    {"decision": "APPROVED", "post_id": 999, "sha256": digest},
                )

    def test_crlf_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.html"
            path.write_bytes(b"<p>fixed</p>\r\n")
            with self.assertRaisesRegex(ValueError, "LF"):
                checked_html(
                    path,
                    {"decision": "APPROVED", "post_id": 50, "sha256": "0" * 64},
                )
