from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import call, patch

from scripts.publish_adsense_pilot import checked_html, main


class PilotPublishContractTests(unittest.TestCase):
    def test_apply_rehashes_and_updates_only_the_selected_post_then_reads_it_back(self):
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
            identity = {
                "id": 132,
                "slug": "wordpress-rest-api-pagination",
                "link": "https://huntlab.app/wordpress-rest-api-pagination/",
                "featured_media": 220,
                "aioseo_meta_data": {"canonical_url": ""},
                "status": "publish",
                "content": {"raw": "<p>pagination</p>\n"},
            }
            argv = [
                "publish_adsense_pilot.py",
                "--post-id",
                "132",
                "--html",
                str(html_path),
                "--approval",
                str(approval_path),
                "--apply",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch("scripts.publish_adsense_pilot.WordPressConfig.from_environment"),
                patch("scripts.publish_adsense_pilot.WordPressClient") as client_type,
                redirect_stdout(io.StringIO()),
            ):
                client = client_type.return_value
                client.get_post.side_effect = [identity, identity]
                self.assertEqual(main(), 0)

        self.assertEqual(client.get_post.call_args_list, [call(132), call(132)])
        client.update_post.assert_called_once_with(
            132,
            {"title": "pagination", "content": "<p>pagination</p>\n"},
            status="publish",
        )

    def test_apply_aborts_before_update_if_second_hash_differs(self):
        argv = [
            "publish_adsense_pilot.py",
            "--post-id",
            "132",
            "--html",
            "unused.html",
            "--approval",
            "unused.json",
            "--apply",
        ]
        approval = {
            "decision": "APPROVED",
            "post_id": 132,
            "sha256": "a" * 64,
            "title": "pagination",
        }
        identity = {
            "id": 132,
            "slug": "wordpress-rest-api-pagination",
            "link": "https://huntlab.app/wordpress-rest-api-pagination/",
            "featured_media": 220,
            "aioseo_meta_data": {"canonical_url": ""},
            "status": "publish",
        }
        with (
            patch.object(sys, "argv", argv),
            patch("pathlib.Path.read_text", return_value=json.dumps(approval)),
            patch(
                "scripts.publish_adsense_pilot.checked_html",
                side_effect=[("approved", "a" * 64), ("changed", "b" * 64)],
            ),
            patch("scripts.publish_adsense_pilot.WordPressConfig.from_environment"),
            patch("scripts.publish_adsense_pilot.WordPressClient") as client_type,
        ):
            client = client_type.return_value
            client.get_post.return_value = identity
            with self.assertRaisesRegex(RuntimeError, "changed between validation"):
                main()

        client_type.assert_not_called()
        client.update_post.assert_not_called()

    def test_apply_rejects_readback_content_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path, approval_path, identity = self._apply_fixture(directory)
            changed = {**identity, "content": {"raw": "<p>changed</p>\n"}}
            argv = self._apply_argv(html_path, approval_path)
            with (
                patch.object(sys, "argv", argv),
                patch("scripts.publish_adsense_pilot.WordPressConfig.from_environment"),
                patch("scripts.publish_adsense_pilot.WordPressClient") as client_type,
            ):
                client = client_type.return_value
                client.get_post.side_effect = [identity, changed]
                with self.assertRaisesRegex(RuntimeError, "content does not match"):
                    main()

        client.update_post.assert_called_once()

    def test_apply_rejects_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path, approval_path, identity = self._apply_fixture(directory)
            changed = {**identity, "featured_media": 999}
            argv = self._apply_argv(html_path, approval_path)
            with (
                patch.object(sys, "argv", argv),
                patch("scripts.publish_adsense_pilot.WordPressConfig.from_environment"),
                patch("scripts.publish_adsense_pilot.WordPressClient") as client_type,
            ):
                client = client_type.return_value
                client.get_post.side_effect = [identity, changed]
                with self.assertRaisesRegex(RuntimeError, "canonical changed"):
                    main()

        client.update_post.assert_called_once()

    def test_apply_api_failure_cannot_report_success(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path, approval_path, identity = self._apply_fixture(directory)
            argv = self._apply_argv(html_path, approval_path)
            with (
                patch.object(sys, "argv", argv),
                patch("scripts.publish_adsense_pilot.WordPressConfig.from_environment"),
                patch("scripts.publish_adsense_pilot.WordPressClient") as client_type,
                redirect_stdout(io.StringIO()) as output,
            ):
                client = client_type.return_value
                client.get_post.return_value = identity
                client.update_post.side_effect = RuntimeError("api failed")
                with self.assertRaisesRegex(RuntimeError, "api failed"):
                    main()

        self.assertNotIn("status=UPDATED", output.getvalue())

    @staticmethod
    def _apply_argv(html_path: Path, approval_path: Path) -> list[str]:
        return [
            "publish_adsense_pilot.py",
            "--post-id",
            "132",
            "--html",
            str(html_path),
            "--approval",
            str(approval_path),
            "--apply",
        ]

    @staticmethod
    def _apply_fixture(directory: str) -> tuple[Path, Path, dict]:
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
        identity = {
            "id": 132,
            "slug": "wordpress-rest-api-pagination",
            "link": "https://huntlab.app/wordpress-rest-api-pagination/",
            "featured_media": 220,
            "aioseo_meta_data": {"canonical_url": ""},
            "status": "publish",
            "content": {"raw": "<p>pagination</p>\n"},
        }
        return html_path, approval_path, identity

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

    def test_missing_final_newline_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.html"
            path.write_bytes(b"<p>fixed</p>")
            with self.assertRaisesRegex(ValueError, "exactly one newline"):
                checked_html(
                    path,
                    {"decision": "APPROVED", "post_id": 132, "sha256": "0" * 64},
                )

    def test_multiple_trailing_newlines_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.html"
            path.write_bytes(b"<p>fixed</p>\n\n")
            with self.assertRaisesRegex(ValueError, "exactly one newline"):
                checked_html(
                    path,
                    {"decision": "APPROVED", "post_id": 132, "sha256": "0" * 64},
                )

    def test_invalid_utf8_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.html"
            path.write_bytes(b"<p>\xff</p>\n")
            with self.assertRaises(UnicodeDecodeError):
                checked_html(
                    path,
                    {"decision": "APPROVED", "post_id": 132, "sha256": "0" * 64},
                )
