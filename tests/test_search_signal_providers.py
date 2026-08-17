from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.search_signal_providers import (
    SearchSignalError,
    load_naver_searchadvisor,
    load_whereispost_shadow,
)


class SearchSignalProviderTests(unittest.TestCase):
    def test_missing_optional_exports_are_na_not_zero(self):
        self.assertEqual(load_naver_searchadvisor(None)["status"], "N/A")
        self.assertEqual(load_whereispost_shadow(None)["status"], "N/A")

    def test_whereispost_requires_complete_manual_rows(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "whereispost.json"
            path.write_text(
                json.dumps(
                    {
                        "provider": "whereispost_keywordmaster",
                        "checked_at": "2026-08-07T01:00:00+09:00",
                        "rows": [{"keyword": "불완전"}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(SearchSignalError):
                load_whereispost_shadow(path)

    def test_naver_owner_export_is_loaded_without_credentials(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "naver.json"
            path.write_text(
                json.dumps(
                    {
                        "provider": "naver_searchadvisor",
                        "checked_at": "2026-08-07T01:00:00+09:00",
                        "rows": [{"page": "https://huntlab.app/example/"}],
                    }
                ),
                encoding="utf-8",
            )
            result = load_naver_searchadvisor(path)
            self.assertEqual(result["status"], "AVAILABLE")
            self.assertEqual(len(result["rows"]), 1)

    def test_whereispost_rejects_a_mismatched_total(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "whereispost.json"
            path.write_text(
                json.dumps(
                    {
                        "provider": "whereispost_keywordmaster",
                        "checked_at": "2026-08-16T16:30:00+09:00",
                        "rows": [
                            {
                                "keyword": "주택청약",
                                "pc_searches": 10,
                                "mobile_searches": 20,
                                "total_searches": 99,
                                "documents": 100,
                                "competition_ratio": 1.0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SearchSignalError, "total_searches mismatch"):
                load_whereispost_shadow(path)


if __name__ == "__main__":
    unittest.main()
