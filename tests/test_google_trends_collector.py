from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from scripts.collect_google_trends_cache import (
    TrendsCollectorError,
    canonical_hash,
    discovery_score,
    merge_rows,
    parse_approx_traffic,
    parse_feed,
)


RSS = '''<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0">
  <channel>
    <item>
      <title>민방위</title>
      <ht:approx_traffic>10K+</ht:approx_traffic>
      <pubDate>Wed, 19 Aug 2026 00:50:00 -0700</pubDate>
      <ht:news_item>
        <ht:news_item_title>민방위 일정 발표</ht:news_item_title>
        <ht:news_item_url>https://example.com/a</ht:news_item_url>
        <ht:news_item_source>Example News</ht:news_item_source>
      </ht:news_item>
    </item>
  </channel>
</rss>'''.encode("utf-8")


class GoogleTrendsCollectorTests(unittest.TestCase):
    def test_parse_traffic_labels(self):
        self.assertEqual(parse_approx_traffic("2,000+"), 2000)
        self.assertEqual(parse_approx_traffic("10K+"), 10000)
        with self.assertRaises(TrendsCollectorError):
            parse_approx_traffic("많음")

    def test_parse_feed_keeps_topic_traffic_time_and_news(self):
        now = datetime(2026, 8, 19, 8, 10, tzinfo=UTC)
        rows = parse_feed(RSS, collected_at=now)
        self.assertEqual(rows[0]["topic"], "민방위")
        self.assertEqual(rows[0]["approx_traffic"], 10000)
        self.assertEqual(rows[0]["news_source_count"], 1)
        self.assertEqual(rows[0]["news_items"][0]["source"], "Example News")
        self.assertEqual(rows[0]["observation_count"], 1)
        self.assertEqual(rows[0]["peak_traffic"], 10000)
        self.assertGreater(rows[0]["discovery_score"], 0)

    def test_merge_preserves_first_seen_and_drops_stale_rows(self):
        now = datetime(2026, 8, 19, 8, 10, tzinfo=UTC)
        fresh = parse_feed(RSS, collected_at=now)
        existing = [
            {
                **fresh[0],
                "first_seen_at": (now - timedelta(hours=3)).isoformat(),
                "last_seen_at": (now - timedelta(hours=1)).isoformat(),
                "approx_traffic": 20000,
            },
            {
                **fresh[0],
                "topic": "오래된 주제",
                "normalized_topic": "오래된 주제",
                "first_seen_at": (now - timedelta(hours=60)).isoformat(),
                "last_seen_at": (now - timedelta(hours=60)).isoformat(),
            },
        ]
        merged = merge_rows(
            existing,
            fresh,
            collected_at=now,
            retention_hours=48,
            max_rows=300,
        )
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["approx_traffic"], 20000)
        self.assertEqual(
            merged[0]["first_seen_at"], (now - timedelta(hours=3)).isoformat()
        )
        self.assertEqual(merged[0]["observation_count"], 2)
        self.assertEqual(merged[0]["peak_traffic"], 20000)
        self.assertEqual(merged[0]["traffic_delta"], -10000)

    def test_discovery_score_is_observed_and_deterministic(self):
        now = datetime(2026, 8, 19, 8, 10, tzinfo=UTC)
        row = parse_feed(RSS, collected_at=now)[0]
        self.assertEqual(
            discovery_score(row, collected_at=now),
            discovery_score(dict(reversed(list(row.items()))), collected_at=now),
        )
        self.assertEqual(canonical_hash(row), canonical_hash(dict(reversed(list(row.items())))))


if __name__ == "__main__":
    unittest.main()
