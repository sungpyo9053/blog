import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from scripts.collect_editorial_sources import collect, parse_feed
from scripts.search_signal_providers import load_editorial_source_cache


RSS = b'''<?xml version="1.0"?><rss><channel><item><title>AI agent release</title><link>https://example.com/a</link><pubDate>Thu, 27 Aug 2026 00:00:00 GMT</pubDate></item></channel></rss>'''
ATOM = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Runtime update</title><link href="https://example.com/b"/><updated>2026-08-27T00:30:00Z</updated></entry></feed>'''


class EditorialSourceCollectorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 27, 1, 0, tzinfo=UTC)

    def test_parses_rss_and_atom_into_same_contract(self):
        source = {"category": "AI/ML 핵심", "name": "Example"}
        rss = parse_feed(RSS, source, collected_at=self.now)
        atom = parse_feed(ATOM, source, collected_at=self.now)
        self.assertEqual(rss[0]["title"], "AI agent release")
        self.assertEqual(atom[0]["url"], "https://example.com/b")
        self.assertEqual(atom[0]["category"], "AI/ML 핵심")

    def test_source_failure_is_isolated_and_cache_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "sources.json"
            cache = root / "cache.json"
            config.write_text(json.dumps({"sources": [
                {"category": "AI/ML 핵심", "name": "Good", "feed_url": "https://good.test/feed"},
                {"category": "개발 트렌드", "name": "Bad", "feed_url": "https://bad.test/feed"},
            ]}), encoding="utf-8")

            def fake_fetch(source, **kwargs):
                if source["name"] == "Bad":
                    return ({"category": source["category"], "name": "Bad", "status": "ERROR", "reason": "blocked"}, [])
                return ({"category": source["category"], "name": "Good", "status": "SUCCESS", "item_count": 1}, parse_feed(RSS, source, collected_at=self.now))

            with patch("scripts.collect_editorial_sources.fetch_source", side_effect=fake_fetch):
                first = collect(config, cache, now=self.now)
                second = collect(config, cache, now=self.now)
            self.assertEqual(first["source_snapshot_hash"], second["source_snapshot_hash"])
            self.assertEqual(first["successful_source_count"], 1)
            self.assertEqual(load_editorial_source_cache(cache)["status"], "AVAILABLE")

    def test_failed_source_keeps_its_last_good_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "sources.json"
            cache = root / "cache.json"
            config.write_text(json.dumps({"sources": [
                {"category": "AI/ML 핵심", "name": "Stable", "feed_url": "https://stable.test/feed"},
                {"category": "개발 트렌드", "name": "Flaky", "feed_url": "https://flaky.test/feed"},
            ]}), encoding="utf-8")

            def first_fetch(source, **kwargs):
                feed = RSS.replace(b"https://example.com/a", f"https://example.com/{source['name'].lower()}".encode())
                return ({"category": source["category"], "name": source["name"], "status": "SUCCESS", "item_count": 1}, parse_feed(feed, source, collected_at=self.now))

            with patch("scripts.collect_editorial_sources.fetch_source", side_effect=first_fetch):
                collect(config, cache, now=self.now)

            def second_fetch(source, **kwargs):
                if source["name"] == "Flaky":
                    return ({"category": source["category"], "name": "Flaky", "status": "ERROR", "reason": "timeout"}, [])
                return first_fetch(source, **kwargs)

            with patch("scripts.collect_editorial_sources.fetch_source", side_effect=second_fetch):
                payload = collect(config, cache, now=self.now)

            self.assertEqual(payload["fallback_source_count"], 1)
            self.assertIn("Flaky", {row["source"] for row in payload["rows"]})
            self.assertEqual(
                next(row for row in payload["sources"] if row["name"] == "Flaky")["fallback"],
                "LAST_GOOD_CACHE",
            )


if __name__ == "__main__":
    unittest.main()
