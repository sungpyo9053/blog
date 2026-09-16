"""Read-only Google analytics snapshots; no query text, credentials or writes.

COMPLETE means the bounded API collection completed, not exhaustive GSC coverage
or statistical significance. GSC returns top rows even with pagination.
"""
from __future__ import annotations

import math
import os
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

from publisher.config import load_env_file

PAGE_SIZE = 1000
MAX_PAGES = 50
HOST = "huntlab.app"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly",
          "https://www.googleapis.com/auth/analytics.readonly"]


class InvalidAnalyticsData(ValueError):
    pass


class MissingAnalyticsData(ValueError):
    pass


class PaginationLimit(ValueError):
    pass


def _session():
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    credentials = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES)
    return AuthorizedSession(credentials)


def _query(session, url, body):
    response = session.post(url, json=body, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise InvalidAnalyticsData()
    return data


def _number(value):
    if isinstance(value, bool) or value is None:
        raise InvalidAnalyticsData()
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise InvalidAnalyticsData()
    return result


def _page(value, *, absolute):
    if not isinstance(value, str):
        raise InvalidAnalyticsData()
    parsed = urlsplit(value)
    if absolute:
        if parsed.scheme not in ("http", "https") or parsed.hostname != HOST or parsed.username or parsed.password or parsed.port:
            raise InvalidAnalyticsData()
    elif parsed.scheme or parsed.netloc or not value.startswith("/"):
        raise InvalidAnalyticsData()
    # Never retain query parameters or fragments, which can contain user data.
    return parsed.path or "/"


def _gsc_numbers(row):
    result = {key: _number(row.get(key)) for key in ("clicks", "impressions", "ctr", "position")}
    if result["ctr"] > 1 or result["clicks"] > result["impressions"]:
        raise InvalidAnalyticsData()
    return result


def _gsc(session, windows):
    site = os.environ["SEARCH_CONSOLE_SITE_URL"]
    if site not in ("sc-domain:huntlab.app", "https://huntlab.app/", "https://huntlab.app"):
        raise InvalidAnalyticsData()
    url = "https://www.googleapis.com/webmasters/v3/sites/" + quote(site, safe="") + "/searchAnalytics/query"
    periods = {}
    for name, window in windows.items():
        body = {"startDate": window["start"], "endDate": window["end"],
                "dataState": "final", "type": "web", "aggregationType": "auto",
                "dimensionFilterGroups": [{"groupType": "and", "filters": [{
                    "dimension": "page", "operator": "includingRegex",
                    "expression": r"^https?://huntlab\.app/"}]}]}
        totals_data = _query(session, url, dict(body, rowLimit=1))
        totals_rows = totals_data.get("rows", [])
        if len(totals_rows) != 1:
            raise MissingAnalyticsData()
        totals = _gsc_numbers(totals_rows[0])
        pages, seen = [], set()
        for index in range(MAX_PAGES):
            data = _query(session, url, dict(body, dimensions=["page"], rowLimit=PAGE_SIZE, startRow=index * PAGE_SIZE))
            rows = data.get("rows", [])
            if not isinstance(rows, list) or len(rows) > PAGE_SIZE:
                raise InvalidAnalyticsData()
            for row in rows:
                keys = row.get("keys", [])
                if len(keys) != 1 or keys[0] in seen:
                    raise InvalidAnalyticsData()
                seen.add(keys[0])
                pages.append({"page": _page(keys[0], absolute=True), **_gsc_numbers(row)})
            if len(rows) < PAGE_SIZE:
                break
        else:
            raise PaginationLimit()
        if totals["impressions"] > 0 and not pages:
            raise MissingAnalyticsData()
        periods[name] = {"totals": totals, "pages": pages,
                         "sample_sufficient": totals["impressions"] >= 100}
    return {"periods": periods, "coverage": "google_top_rows_not_exhaustive",
            "calendar_timezone": "America/Los_Angeles",
            "comparison_sufficient": all(p["sample_sufficient"] for p in periods.values()),
            "sufficiency_rule": "heuristic_only: >=100 impressions in each period; not statistical significance"}


GA_METRICS = ("screenPageViews", "sessions", "engagedSessions")


def _ga_numbers(row):
    values = row.get("metricValues", [])
    if len(values) != len(GA_METRICS):
        raise InvalidAnalyticsData()
    result = {key: _number(value.get("value")) for key, value in zip(GA_METRICS, values)}
    if result["engagedSessions"] > result["sessions"]:
        raise InvalidAnalyticsData()
    return result


def _ga4(session, windows):
    property_id = os.environ["GA4_PROPERTY_ID"]
    if not property_id.isascii() or not property_id.isdigit():
        raise InvalidAnalyticsData()
    url = "https://analyticsdata.googleapis.com/v1beta/properties/" + property_id + ":runReport"
    periods, timezones = {}, set()
    for name, window in windows.items():
        body = {"dateRanges": [{"startDate": window["start"], "endDate": window["end"]}],
                "metrics": [{"name": key} for key in GA_METRICS],
                "dimensionFilter": {"filter": {"fieldName": "hostName", "stringFilter": {
                    "matchType": "EXACT", "value": HOST, "caseSensitive": False}}}}
        totals_data = _query(session, url, dict(body, limit=1))
        totals_rows = totals_data.get("rows", [])
        if len(totals_rows) != 1:
            raise MissingAnalyticsData()
        _ga_metadata(totals_data, timezones)
        totals = _ga_numbers(totals_rows[0])
        pages, seen, expected = [], set(), None
        for index in range(MAX_PAGES):
            data = _query(session, url, dict(body, dimensions=[{"name": "pagePath"}],
                                           orderBys=[{"dimension": {"dimensionName": "pagePath"}}],
                                           limit=PAGE_SIZE, offset=index * PAGE_SIZE))
            _ga_metadata(data, timezones)
            raw_count = _number(data.get("rowCount", 0))
            if not raw_count.is_integer():
                raise InvalidAnalyticsData()
            count = int(raw_count)
            if expected is not None and count != expected:
                raise InvalidAnalyticsData()
            expected = count
            rows = data.get("rows", [])
            if not isinstance(rows, list) or len(rows) > PAGE_SIZE:
                raise InvalidAnalyticsData()
            for row in rows:
                values = row.get("dimensionValues", [])
                if len(values) != 1:
                    raise InvalidAnalyticsData()
                page = _page(values[0].get("value"), absolute=False)
                if page in seen:
                    raise InvalidAnalyticsData()
                seen.add(page)
                pages.append({"page": page, **_ga_numbers(row)})
            if len(pages) == expected:
                break
            if len(pages) > expected or len(rows) < PAGE_SIZE:
                raise MissingAnalyticsData()
        else:
            raise PaginationLimit()
        if totals["screenPageViews"] > 0 and not pages:
            raise MissingAnalyticsData()
        periods[name] = {"totals": totals, "pages": pages,
                         "sample_sufficient": totals["sessions"] >= 30}
    if len(timezones) != 1:
        raise InvalidAnalyticsData()
    return {"periods": periods, "calendar_timezone": next(iter(timezones)),
            "comparison_sufficient": all(p["sample_sufficient"] for p in periods.values()),
            "sufficiency_rule": "heuristic_only: >=30 sessions in each period; not statistical significance"}


def _ga_metadata(data, timezones):
    metadata = data.get("metadata", {})
    if metadata.get("subjectToThresholding") or metadata.get("dataLossFromOtherRow") or metadata.get("samplingMetadatas"):
        raise MissingAnalyticsData()
    zone = metadata.get("timeZone")
    if not isinstance(zone, str) or not zone:
        raise MissingAnalyticsData()
    ZoneInfo(zone)
    timezones.add(zone)


def collect_metrics(now: datetime, root: Path) -> dict:
    """Collect fresh API responses independently. Errors never become zero traffic."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("aware datetime required")
    end = now.date() - timedelta(days=3)
    windows = {"current": {"start": (end - timedelta(days=27)).isoformat(), "end": end.isoformat()},
               "previous": {"start": (end - timedelta(days=55)).isoformat(), "end": (end - timedelta(days=28)).isoformat()}}
    result = {"generated_at": now.isoformat(), "windows": windows, "sources": {},
              "freshness": "live API collection; no cached fallback; final GSC data only",
              "comparison_note": "source calendar timezones may differ; compare within each source only"}
    try:
        load_env_file(root / ".env")
    except Exception as exc:
        for name in ("search_console", "ga4"):
            result["sources"][name] = {"status": "INCOMPLETE", "error_type": type(exc).__name__, "periods": {}}
        return result
    for name, collector in (("search_console", _gsc), ("ga4", _ga4)):
        session = None
        try:
            session = _session()
            result["sources"][name] = {"status": "COMPLETE", **collector(session, windows)}
        except Exception as exc:
            result["sources"][name] = {"status": "INCOMPLETE", "error_type": type(exc).__name__, "periods": {}}
        finally:
            if session is not None:
                with suppress(Exception):
                    session.close()
    return result
