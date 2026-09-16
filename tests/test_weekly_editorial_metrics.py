import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import weekly_editorial_metrics as metrics


NOW = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)
ENV = {"SEARCH_CONSOLE_SITE_URL": "sc-domain:huntlab.app", "GA4_PROPERTY_ID": "123"}


def gsc_row(page=False):
    row = {"clicks": 5, "impressions": 100, "ctr": .05, "position": 4}
    if page:
        row["keys"] = ["https://huntlab.app/example/?private=secret#hidden"]
    return row


def ga_response(page=False):
    row = {"metricValues": [{"value": "100"}, {"value": "30"}, {"value": "20"}]}
    if page:
        row["dimensionValues"] = [{"value": "/example/"}]
    return {"metadata": {"timeZone": "Asia/Seoul"}, "rowCount": 1, "rows": [row]}


def successful_query(session, url, body):
    if "webmasters" in url:
        return {"rows": [gsc_row(bool(body.get("dimensions")))]}
    return ga_response(bool(body.get("dimensions")))


class WeeklyMetricsTests(unittest.TestCase):
    def collect(self, query=successful_query):
        with patch.dict(os.environ, ENV, clear=True), patch.object(metrics, "load_env_file"), \
                patch.object(metrics, "_session", return_value=Mock()), \
                patch.object(metrics, "_query", side_effect=query):
            return metrics.collect_metrics(NOW, Path("/unused"))

    def test_windows_and_sufficiency(self):
        result = self.collect()
        self.assertEqual(result["windows"], {
            "current": {"start": "2026-08-17", "end": "2026-09-13"},
            "previous": {"start": "2026-07-20", "end": "2026-08-16"}})
        for source in result["sources"].values():
            self.assertEqual(source["status"], "COMPLETE")
            self.assertTrue(source["comparison_sufficient"])
        encoded = json.dumps(result, allow_nan=False)
        self.assertNotIn("secret", encoded)
        self.assertNotIn("hidden", encoded)

    def test_requests_host_filter_totals_and_no_query_dimension(self):
        calls = []
        def query(session, url, body):
            calls.append((url, body))
            return successful_query(session, url, body)
        self.collect(query)
        self.assertEqual(len(calls), 8)
        for url, body in calls:
            self.assertNotIn("query", body.get("dimensions", []))
            if "webmasters" in url:
                self.assertEqual(body["dataState"], "final")
                self.assertIn("huntlab", body["dimensionFilterGroups"][0]["filters"][0]["expression"])
            else:
                self.assertEqual(body["dimensionFilter"]["filter"]["stringFilter"]["value"], "huntlab.app")

    def test_failure_independent_redacted_not_zero(self):
        def query(session, url, body):
            if "webmasters" in url:
                raise RuntimeError("TOKEN private credential")
            return successful_query(session, url, body)
        result = self.collect(query)
        self.assertEqual(result["sources"]["search_console"], {
            "status": "INCOMPLETE", "error_type": "RuntimeError", "periods": {}})
        self.assertEqual(result["sources"]["ga4"]["status"], "COMPLETE")
        self.assertNotIn("TOKEN", json.dumps(result))

    def test_missing_data_not_zero(self):
        result = self.collect(lambda *args: {})
        self.assertTrue(all(s["status"] == "INCOMPLETE" for s in result["sources"].values()))
        self.assertTrue(all(s["periods"] == {} for s in result["sources"].values()))

    def test_invalid_numbers(self):
        for bad in ("NaN", "Infinity", -1, None, True):
            with self.subTest(bad=bad), self.assertRaises(metrics.InvalidAnalyticsData):
                metrics._number(bad)
        with self.assertRaises(metrics.InvalidAnalyticsData):
            metrics._gsc_numbers(dict(gsc_row(), clicks=101))

    def test_cross_domain_rejected(self):
        def query(session, url, body):
            data = successful_query(session, url, body)
            if "webmasters" in url and body.get("dimensions"):
                data["rows"][0]["keys"] = ["https://evil.example/x"]
            return data
        self.assertEqual(self.collect(query)["sources"]["search_console"]["status"], "INCOMPLETE")

    def test_insufficient_sample_is_not_error(self):
        def query(session, url, body):
            data = successful_query(session, url, body)
            if "webmasters" in url:
                data["rows"][0]["impressions"] = 99
            else:
                data["rows"][0]["metricValues"][1]["value"] = "29"
            return data
        for source in self.collect(query)["sources"].values():
            self.assertEqual(source["status"], "COMPLETE")
            self.assertFalse(source["comparison_sufficient"])

    def test_thresholding_incomplete(self):
        def query(session, url, body):
            data = successful_query(session, url, body)
            if "analyticsdata" in url:
                data["metadata"]["subjectToThresholding"] = True
            return data
        self.assertEqual(self.collect(query)["sources"]["ga4"]["status"], "INCOMPLETE")

    def test_ga_row_count_truncation_incomplete(self):
        def query(session, url, body):
            data = successful_query(session, url, body)
            if "analyticsdata" in url and body.get("dimensions"):
                data["rowCount"] = 5
            return data
        self.assertEqual(self.collect(query)["sources"]["ga4"]["status"], "INCOMPLETE")

    def test_pagination(self):
        calls = []
        def query(session, url, body):
            calls.append(body)
            data = successful_query(session, url, body)
            if body.get("dimensions") and (body.get("startRow", body.get("offset", 0)) > 0):
                data["rows"] = []
            return data
        with patch.object(metrics, "PAGE_SIZE", 1):
            result = self.collect(query)
        self.assertTrue(all(s["status"] == "COMPLETE" for s in result["sources"].values()))
        self.assertTrue(any(c.get("startRow") == 1 for c in calls))

    def test_pagination_bound_fail_closed(self):
        with patch.object(metrics, "PAGE_SIZE", 1), patch.object(metrics, "MAX_PAGES", 1):
            result = self.collect()
        self.assertEqual(result["sources"]["search_console"]["error_type"], "PaginationLimit")

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            metrics.collect_metrics(datetime(2026, 9, 16), Path("/unused"))

    def test_credentials_failure_has_no_detail(self):
        with patch.object(metrics, "load_env_file"), patch.object(metrics, "_session", side_effect=OSError("secret")):
            result = metrics.collect_metrics(NOW, Path("/unused"))
        self.assertNotIn("secret", json.dumps(result))
        self.assertTrue(all(s["status"] == "INCOMPLETE" for s in result["sources"].values()))


if __name__ == "__main__":
    unittest.main()
