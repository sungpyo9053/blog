from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.evidence_topic_miner import (
    contains_secret,
    redact_text,
    run_git,
    safe_relative_path,
    sanitize_url,
)
from scripts.snapshot_topic_inventory import build_snapshot


class TopicMinerSecurityTests(unittest.TestCase):
    def test_redacts_credentials_tokens_email_phone_and_home_path(self):
        source = (
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz "
            "AKIAABCDEFGHIJKLMNOP ghp_abcdefghijklmnopqrstuvwxyz "
            "Cookie: session=private\nowner@example.com 010-1234-5678 /Users/private/blog"
        )
        result = redact_text(source)
        self.assertNotIn("AKIA", result)
        self.assertNotIn("ghp_", result)
        self.assertNotIn("example.com", result)
        self.assertNotIn("010-1234-5678", result)
        self.assertNotIn("/Users/private/", result)
        self.assertNotIn("session=private", result)
        self.assertFalse(contains_secret(result))

    def test_redacts_url_userinfo_and_secret_query(self):
        value = sanitize_url("https://user:pass@example.com/path?token=secret&safe=yes#fragment")
        self.assertNotIn("user", value)
        self.assertNotIn("pass", value)
        self.assertNotIn("secret", value)
        self.assertIn("safe=yes", value)
        self.assertNotIn("fragment", value)

    def test_blocks_env_keys_absolute_escape_and_git_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            for value in (".env", "secret.pem", "../escape", "/tmp/absolute", ".git/objects/aa"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    safe_relative_path(repo, value)

    def test_read_only_git_allowlist_rejects_commit_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            with self.assertRaises(ValueError):
                run_git(repo, ["commit", "-m", "forbidden"])
            with self.assertRaises(ValueError):
                run_git(repo, ["status"])

    def test_git_subprocess_uses_shell_false(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            with patch("scripts.evidence_topic_miner.subprocess.run") as runner:
                runner.return_value.stdout = "head\n"
                run_git(repo, ["rev-parse", "HEAD"])
            self.assertFalse(runner.call_args.kwargs["shell"])
            self.assertEqual(runner.call_args.args[0], ["git", "rev-parse", "HEAD"])

    def test_module_has_no_wordpress_publisher_timer_or_network_dependency(self):
        source = Path("scripts/evidence_topic_miner.py").read_text(encoding="utf-8")
        self.assertNotIn("WordPressClient", source)
        self.assertNotIn("update_post", source)
        self.assertNotIn("create_post", source)
        self.assertNotIn("systemctl", source)
        self.assertNotIn("urllib.request", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("news_worthiness", source)
        self.assertNotIn("google_trends", source)

    def test_inventory_snapshot_source_is_get_only(self):
        source = Path("scripts/snapshot_topic_inventory.py").read_text(encoding="utf-8")
        self.assertIn('client.request("GET"', source)
        self.assertNotIn('client.request("POST"', source)
        self.assertNotIn('client.request("PUT"', source)
        self.assertNotIn('client.request("DELETE"', source)
        self.assertNotIn("update_post", source)
        self.assertNotIn("create_post", source)

    def test_inventory_snapshot_paginates_publish_and_reads_draft_with_get_only(self):
        class Client:
            def __init__(self): self.calls = []
            def request(self, method, path, expected):
                self.calls.append((method, path, expected))
                status = "draft" if "status=draft" in path else "publish"
                page = 2 if "page=2" in path else 1
                count = 1 if status == "draft" else (100 if page == 1 else 19)
                return [{"id": page * 1000 + i, "link": f"https://example.test/{status}-{page}-{i}", "slug": f"{status}-{page}-{i}", "status": status, "title": {"rendered": "title"}, "excerpt": {"rendered": "excerpt"}} for i in range(count)]
        client = Client()
        snapshot = build_snapshot(client)
        self.assertEqual(snapshot["metadata"]["statuses"], {"publish": 119, "draft": 1})
        self.assertEqual(len(snapshot["posts"]), 120)
        self.assertTrue(all(method == "GET" for method, _, _ in client.calls))


if __name__ == "__main__":
    unittest.main()
