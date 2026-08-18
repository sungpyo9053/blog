from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.manage_whereispost_cache import (
    CacheValidationError,
    promote_cache,
    validate_cache_payload,
)


def cache_payload(*, checked_at: str = "2026-08-17T15:00:00+09:00", rows: int = 6):
    return {
        "provider": "whereispost_keywordmaster",
        "checked_at": checked_at,
        "rows": [
            {
                "keyword": f"후보 {index}",
                "pc_searches": 40,
                "mobile_searches": 80,
                "total_searches": 120,
                "documents": 1000 + index,
                "competition_ratio": 9.0,
                "related_keywords": [f"후보 {index} 신청"],
                "source_origin": "official_change",
                "consumed": False,
            }
            for index in range(rows)
        ],
    }


class WhereispostCacheTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 18, 6, 0, tzinfo=timezone.utc)

    def test_valid_cache_requires_six_eligible_unique_rows(self):
        validated = validate_cache_payload(cache_payload(), now=self.now)

        self.assertEqual(validated["eligible_rows"], 6)
        self.assertEqual(validated["cache_contract_version"], 1)

    def test_stale_cache_is_rejected(self):
        with self.assertRaisesRegex(CacheValidationError, "older than 7"):
            validate_cache_payload(
                cache_payload(checked_at="2026-08-01T15:00:00+09:00"),
                now=self.now,
            )

    def test_duplicate_keyword_is_rejected(self):
        payload = cache_payload()
        payload["rows"][1]["keyword"] = payload["rows"][0]["keyword"]

        with self.assertRaisesRegex(CacheValidationError, "duplicate keyword"):
            validate_cache_payload(payload, now=self.now)

    def test_consumed_or_low_demand_rows_do_not_count_as_eligible(self):
        payload = cache_payload()
        payload["rows"][0]["consumed"] = True

        with self.assertRaisesRegex(CacheValidationError, "eligible rows 5"):
            validate_cache_payload(payload, now=self.now)

    def test_invalid_candidate_does_not_replace_existing_latest(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "candidate.json"
            destination = directory / "latest.json"
            destination.write_text('{"sentinel": true}\n', encoding="utf-8")
            source.write_text(
                json.dumps(cache_payload(rows=5), ensure_ascii=False),
                encoding="utf-8",
            )

            with self.assertRaises(CacheValidationError):
                promote_cache(source, destination, now=self.now)

            self.assertEqual(
                json.loads(destination.read_text(encoding="utf-8")),
                {"sentinel": True},
            )

    def test_valid_candidate_is_atomically_promoted(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "candidate.json"
            destination = directory / "latest.json"
            source.write_text(
                json.dumps(cache_payload(), ensure_ascii=False), encoding="utf-8"
            )

            promote_cache(source, destination, now=self.now)

            promoted = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(promoted["eligible_rows"], 6)
            self.assertEqual(len(promoted["rows"]), 6)


if __name__ == "__main__":
    unittest.main()
