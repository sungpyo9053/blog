"""Read-only Search Console and GA4 report generator."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publisher.config import load_env_file
from scripts.audit_public_site import (
    audit_site,
    fetch,
    render_markdown as render_public_audit,
)
from scripts.search_signal_providers import collect_shadow_signals

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "output" / "analytics"
LOG_DIR = ROOT / "logs"
INDEX_RECOVERY_STATE = REPORT_DIR / "index-recovery-state.json"
INDEX_INSPECTION_LIMIT = 10
INDEX_RECOVERY_COOLDOWN = timedelta(days=7)
FRESH_INSPECTION_QUOTA = 6
RECOVERY_INSPECTION_QUOTA = 4
INDEX_RECOVERY_QUEUE = REPORT_DIR / "index-recovery-queue.json"
CTR_EXPERIMENT_QUEUE = REPORT_DIR / "ctr-experiment-queue.json"


def _credentials():
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        scopes=[
            "https://www.googleapis.com/auth/webmasters.readonly",
            "https://www.googleapis.com/auth/analytics.readonly",
        ],
    )


GA4_SUMMARY_METRICS = (
    "activeUsers",
    "newUsers",
    "sessions",
    "engagedSessions",
    "screenPageViews",
    "userEngagementDuration",
)
BRAND_QUERIES = {"huntlab", "hunt lab", "훈트랩"}
RESIDENT_SURVEY_PATH = "/resident-registration-survey/"
RESIDENT_SURVEY_PROPOSED_TITLE = (
    "2026 주민등록 사실조사 방문조사 대상과 비대면 참여 방법"
)


def _optional_path(value: str | None) -> Path | None:
    return Path(value).expanduser() if value and value.strip() else None


def collect_url_inspections(urls: list[str]) -> list[dict[str, Any]]:
    """Read Google's indexed-version status; never submit URLs for indexing."""
    from googleapiclient.discovery import build

    if not urls:
        return []
    try:
        service = build(
            "searchconsole",
            "v1",
            credentials=_credentials(),
            cache_discovery=False,
        )
        site_url = os.environ["SEARCH_CONSOLE_SITE_URL"]
    except Exception as exc:  # noqa: BLE001 - inspection is supplementary
        return [
            {
                "url": url,
                "status": "INCOMPLETE",
                "error_type": type(exc).__name__,
            }
            for url in urls[:10]
        ]
    results: list[dict[str, Any]] = []
    for url in urls[:10]:
        try:
            response = (
                service.urlInspection()
                .index()
                .inspect(
                    body={
                        "inspectionUrl": url,
                        "siteUrl": site_url,
                        "languageCode": "ko-KR",
                    }
                )
                .execute()
            )
            status = response.get("inspectionResult", {}).get(
                "indexStatusResult", {}
            )
            results.append(
                {
                    "url": url,
                    "status": "COMPLETE",
                    "verdict": status.get("verdict", "VERDICT_UNSPECIFIED"),
                    "coverage_state": status.get("coverageState", ""),
                    "robots_txt_state": status.get("robotsTxtState", ""),
                    "indexing_state": status.get("indexingState", ""),
                    "page_fetch_state": status.get("pageFetchState", ""),
                    "last_crawl_time": status.get("lastCrawlTime", ""),
                    "user_canonical": status.get("userCanonical", ""),
                    "google_canonical": status.get("googleCanonical", ""),
                    "referring_urls": status.get("referringUrls", []),
                    "sitemaps": status.get("sitemap", []),
                }
            )
        except Exception as exc:  # noqa: BLE001 - one URL must not block analytics
            results.append(
                {
                    "url": url,
                    "status": "INCOMPLETE",
                    "error_type": type(exc).__name__,
                }
            )
    return results


def select_index_checkpoint_urls(
    public_posts: list[dict],
    state: dict[str, Any],
    now: datetime,
    *,
    limit: int = 10,
) -> list[dict[str, str]]:
    """Select new posts around 24h, 72h and 7d after publication."""
    candidates: list[tuple[datetime, dict[str, str]]] = []
    records = state.get("urls", {}) if isinstance(state, dict) else {}
    for post in public_posts:
        if post.get("status", "publish") != "publish":
            continue
        url = str(post.get("link", "")).strip()
        published_text = str(post.get("date", "")).strip()
        if not url or not published_text:
            continue
        try:
            published_at = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
        except ValueError:
            continue
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=now.tzinfo)
        age_hours = (now.astimezone(published_at.tzinfo) - published_at).total_seconds() / 3600
        if age_hours < 24 or age_hours > 24 * 14:
            continue
        checkpoints = records.get(url, {}).get("checkpoints", {})
        checkpoint = "7d" if age_hours >= 24 * 7 else (
            "72h" if age_hours >= 72 else "24h"
        )
        if checkpoint in checkpoints:
            continue
        candidates.append(
            (
                published_at,
                {
                    "url": url,
                    "checkpoint": checkpoint,
                    "published_at": published_at.isoformat(),
                },
            )
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in candidates[:limit]]


def select_mature_recovery_urls(
    urls: list[str],
    state: dict[str, Any],
    now: datetime,
    *,
    limit: int = INDEX_INSPECTION_LIMIT,
    cooldown: timedelta = INDEX_RECOVERY_COOLDOWN,
) -> list[str]:
    """Rotate through mature no-impression URLs instead of rechecking the same ten."""
    if limit <= 0:
        return []
    records = state.get("urls", {}) if isinstance(state, dict) else {}
    candidates: list[tuple[datetime, int, str]] = []
    never = datetime.min.replace(tzinfo=timezone.utc)
    for position, url in enumerate(dict.fromkeys(urls)):
        inspected_text = str(records.get(url, {}).get("recovery_last_inspected_at", ""))
        inspected_at = never
        if inspected_text:
            try:
                inspected_at = datetime.fromisoformat(inspected_text.replace("Z", "+00:00"))
                if inspected_at.tzinfo is None:
                    inspected_at = inspected_at.replace(tzinfo=now.tzinfo)
            except ValueError:
                inspected_at = never
        comparable = inspected_at.astimezone(now.tzinfo) if inspected_at != never else never
        if comparable != never and now - comparable < cooldown:
            continue
        candidates.append((comparable, position, url))
    candidates.sort(key=lambda item: (item[0], item[1]))
    return [url for _, _, url in candidates[:limit]]


def allocate_index_inspection_targets(
    public_posts: list[dict],
    mature_urls: list[str],
    state: dict[str, Any],
    now: datetime,
) -> tuple[list[dict[str, str]], list[str]]:
    """Reserve daily capacity for both fresh checkpoints and mature recovery."""
    all_checkpoints = select_index_checkpoint_urls(
        public_posts, state, now, limit=INDEX_INSPECTION_LIMIT
    )
    checkpoints = all_checkpoints[:FRESH_INSPECTION_QUOTA]
    checkpoint_urls = {item["url"] for item in checkpoints}
    eligible_recovery = [url for url in mature_urls if url not in checkpoint_urls]
    all_recovery = select_mature_recovery_urls(
        eligible_recovery,
        state,
        now,
        limit=INDEX_INSPECTION_LIMIT,
    )
    recovery_urls = all_recovery[:RECOVERY_INSPECTION_QUOTA]

    remaining = INDEX_INSPECTION_LIMIT - len(checkpoints) - len(recovery_urls)
    if remaining > 0:
        extra_checkpoints = [
            item for item in all_checkpoints if item["url"] not in checkpoint_urls
        ][:remaining]
        checkpoints.extend(extra_checkpoints)
        checkpoint_urls.update(item["url"] for item in extra_checkpoints)
        remaining = INDEX_INSPECTION_LIMIT - len(checkpoints) - len(recovery_urls)
    if remaining > 0:
        recovery_urls.extend(
            url for url in all_recovery if url not in recovery_urls
        )
        recovery_urls = recovery_urls[: INDEX_INSPECTION_LIMIT - len(checkpoints)]
    return checkpoints, recovery_urls


def update_index_checkpoint_state(
    state: dict[str, Any],
    selected: list[dict[str, str]],
    inspections: list[dict[str, Any]],
    now: datetime,
    *,
    recovery_urls: list[str] | None = None,
) -> dict[str, Any]:
    """Persist full completed inspections so transient API failures retry later."""
    updated = json.loads(json.dumps(state)) if isinstance(state, dict) else {}
    updated["version"] = 2
    updated["updated_at"] = now.isoformat()
    records = updated.setdefault("urls", {})
    inspected = {str(item.get("url", "")): item for item in inspections}
    for candidate in selected:
        result = inspected.get(candidate["url"], {})
        if result.get("status") != "COMPLETE":
            continue
        record = records.setdefault(
            candidate["url"],
            {"published_at": candidate["published_at"], "checkpoints": {}},
        )
        snapshot = {
            "inspected_at": now.isoformat(),
            "verdict": result.get("verdict", "VERDICT_UNSPECIFIED"),
            "coverage_state": result.get("coverage_state", ""),
            "indexing_state": result.get("indexing_state", ""),
            "robots_txt_state": result.get("robots_txt_state", ""),
            "page_fetch_state": result.get("page_fetch_state", ""),
            "last_crawl_time": result.get("last_crawl_time", ""),
            "user_canonical": result.get("user_canonical", ""),
            "google_canonical": result.get("google_canonical", ""),
            "sitemaps": result.get("sitemaps", []),
        }
        record.setdefault("checkpoints", {})[candidate["checkpoint"]] = snapshot
        record["latest"] = snapshot
    for url in recovery_urls or []:
        result = inspected.get(url, {})
        if result.get("status") != "COMPLETE":
            continue
        record = records.setdefault(url, {"checkpoints": {}})
        snapshot = {
            "inspected_at": now.isoformat(),
            "verdict": result.get("verdict", "VERDICT_UNSPECIFIED"),
            "coverage_state": result.get("coverage_state", ""),
            "indexing_state": result.get("indexing_state", ""),
            "robots_txt_state": result.get("robots_txt_state", ""),
            "page_fetch_state": result.get("page_fetch_state", ""),
            "last_crawl_time": result.get("last_crawl_time", ""),
            "user_canonical": result.get("user_canonical", ""),
            "google_canonical": result.get("google_canonical", ""),
            "sitemaps": result.get("sitemaps", []),
        }
        record["recovery_last_inspected_at"] = now.isoformat()
        history = record.setdefault("recovery_checks", [])
        history.append(snapshot)
        record["recovery_checks"] = history[-4:]
        record["latest"] = snapshot
    return updated


def read_index_checkpoint_state(path: Path = INDEX_RECOVERY_STATE) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def write_index_checkpoint_state(
    state: dict[str, Any], path: Path = INDEX_RECOVERY_STATE
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def aug7_review_decisions(
    page_rows: list[dict],
    inspections: list[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    """Turn the approved Aug-7 backlog into bounded, auditable decisions."""
    resident = next(
        (row for row in page_rows if row.get("page") == RESIDENT_SURVEY_PATH),
        None,
    )
    review_ready = now.date() >= date(2026, 8, 7)
    if not review_ready:
        title_experiment = {
            "status": "SCHEDULED",
            "reason": "wait_for_2026-08-07_measurement",
        }
    elif resident is None:
        title_experiment = {
            "status": "HOLD",
            "reason": "target_has_no_search_console_page_row",
        }
    else:
        clicks = _number(resident.get("clicks"))
        impressions = _number(resident.get("impressions"))
        position = _number(resident.get("position"))
        eligible = (
            clicks == 0
            and impressions >= 30
            and 8 <= position <= 15
        )
        title_experiment = {
            "status": "ELIGIBLE_REVIEW" if eligible else "HOLD",
            "reason": (
                "zero_clicks_with_repeated_impressions_near_page_one"
                if eligible
                else "threshold_not_met"
            ),
            "clicks": clicks,
            "impressions": impressions,
            "position": position,
            "single_change": "title_only",
            "proposed_title": RESIDENT_SURVEY_PROPOSED_TITLE,
            "stop_rule": "14_days_or_1000_impressions",
        }

    unindexed = [
        item
        for item in inspections
        if item.get("status") == "COMPLETE" and item.get("verdict") != "PASS"
    ]
    discovery = (
        {
            "status": "ELIGIBLE_REVIEW",
            "target_url": unindexed[0]["url"],
            "single_change": "one_relevant_internal_link",
            "reason": unindexed[0].get("coverage_state", "not_indexed"),
            "automatic_indexing_api_submission": "forbidden_for_general_blog_posts",
        }
        if review_ready and unindexed
        else {
            "status": "SCHEDULED" if not review_ready else "HOLD",
            "reason": (
                "wait_for_2026-08-07_url_inspection"
                if not review_ready
                else "no_unindexed_inspected_target"
            ),
        }
    )
    return {
        "review_date_ready": review_ready,
        "title_experiment": title_experiment,
        "index_discovery": discovery,
        "planner_keyword_rule": {
            "status": "ACTIVE",
            "rule": "product_or_technology_plus_observed_problem_plus_user_action",
            "invented_problem": "forbidden",
        },
    }


def collect() -> tuple[list[dict], list[dict], dict[str, Any]]:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        RunReportRequest,
    )
    from googleapiclient.discovery import build

    credentials = _credentials()
    site_url = os.environ["SEARCH_CONSOLE_SITE_URL"]
    search = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=6)
    def search_query(dimensions: list[str], row_limit: int = 100) -> list[dict]:
        body: dict[str, Any] = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "rowLimit": row_limit,
        }
        if dimensions:
            body["dimensions"] = dimensions
        response = (
            search.searchanalytics()
            .query(siteUrl=site_url, body=body)
            .execute()
        )
        return response.get("rows", [])

    search_rows = search_query(["query", "page"])
    search_totals = search_query([], 1)
    search_daily = search_query(["date"], 20)
    search_queries = search_query(["query"])
    search_pages = search_query(["page"])

    analytics = BetaAnalyticsDataClient(credentials=credentials)
    property_name = "properties/" + os.environ["GA4_PROPERTY_ID"]

    def analytics_query(
        start_date: str,
        end_date: str,
        dimensions: tuple[str, ...],
        metrics: tuple[str, ...],
        *,
        limit: int = 50,
    ) -> list[dict[str, str]]:
        request = RunReportRequest(
            property=property_name,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name=name) for name in dimensions],
            metrics=[Metric(name=name) for name in metrics],
            limit=limit,
        )
        rows: list[dict[str, str]] = []
        for row in analytics.run_report(request).rows:
            rows.append(
                {
                    **{
                        name: value.value
                        for name, value in zip(dimensions, row.dimension_values)
                    },
                    **{
                        name: value.value
                        for name, value in zip(metrics, row.metric_values)
                    },
                }
            )
        return rows

    page_rows = analytics_query(
        "6daysAgo",
        "today",
        ("pagePath",),
        ("screenPageViews",),
    )
    ga_rows = []
    for row in page_rows:
        ga_rows.append(
            {
                "page": row["pagePath"],
                "screenPageViews": row["screenPageViews"],
            }
        )
    summary: dict[str, dict[str, str]] = {}
    for label, start_date, end_date in (
        ("today", "today", "today"),
        ("yesterday", "yesterday", "yesterday"),
        ("last7days", "6daysAgo", "today"),
    ):
        rows = analytics_query(
            start_date,
            end_date,
            (),
            GA4_SUMMARY_METRICS,
            limit=1,
        )
        summary[label] = rows[0] if rows else {metric: "0" for metric in GA4_SUMMARY_METRICS}

    channel_rows = analytics_query(
        "6daysAgo",
        "today",
        ("sessionDefaultChannelGroup",),
        ("sessions", "engagedSessions"),
        limit=20,
    )
    event_rows = analytics_query(
        "yesterday",
        "yesterday",
        ("eventName",),
        ("eventCount",),
        limit=50,
    )
    host_rows = analytics_query(
        "yesterday",
        "yesterday",
        ("hostName",),
        ("sessions", "engagedSessions", "screenPageViews", "userEngagementDuration"),
        limit=20,
    )
    diagnostics: dict[str, Any] = {
        "search_period": {"start": start.isoformat(), "end": end.isoformat()},
        "search_totals": search_totals[0] if search_totals else {},
        "search_daily": search_daily,
        "search_queries": search_queries,
        "search_pages": search_pages,
        "ga4_summary": summary,
        "ga4_channels": channel_rows,
        "ga4_events": event_rows,
        "ga4_hosts": host_rows,
    }
    return search_rows, ga_rows, diagnostics


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_page_path(value: str) -> str:
    """Collapse protocol, www and query variants to one public content path."""
    parsed = urllib.parse.urlsplit(value)
    path = parsed.path if parsed.scheme or parsed.netloc else value.split("?", 1)[0]
    path = urllib.parse.unquote(path or "/")
    if path != "/":
        path = path.rstrip("/") + "/"
    return path


def aggregate_page_rows(rows: list[dict]) -> list[dict]:
    """Aggregate Search Console URL variants with impression-weighted position."""
    grouped: dict[str, dict[str, float | str]] = {}
    for row in rows:
        keys = row.get("keys", [""])
        page = normalize_page_path(str(keys[0] if keys else ""))
        impressions = _number(row.get("impressions"))
        item = grouped.setdefault(
            page,
            {
                "page": page,
                "clicks": 0.0,
                "impressions": 0.0,
                "position_weight": 0.0,
            },
        )
        item["clicks"] = _number(item["clicks"]) + _number(row.get("clicks"))
        item["impressions"] = _number(item["impressions"]) + impressions
        item["position_weight"] = _number(item["position_weight"]) + (
            _number(row.get("position")) * impressions
        )
    aggregated = []
    for item in grouped.values():
        impressions = _number(item["impressions"])
        clicks = _number(item["clicks"])
        aggregated.append(
            {
                "page": item["page"],
                "clicks": clicks,
                "impressions": impressions,
                "ctr": clicks / impressions if impressions else 0.0,
                "position": _number(item["position_weight"]) / impressions
                if impressions
                else 0.0,
            }
        )
    return sorted(
        aggregated,
        key=lambda item: (item["clicks"], item["impressions"]),
        reverse=True,
    )


def is_article_path(path: str) -> bool:
    return not (
        path == "/"
        or path.startswith(("/category/", "/tag/", "/page/", "/author/"))
        or path in {"/about/", "/privacy-policy/", "/editorial-policy/", "/contact/"}
    )


def collect_public_posts(base_url: str, *, timeout: float = 10.0) -> list[dict]:
    """Collect published post dates with one stable REST request per 100 posts."""
    posts: list[dict] = []
    endpoint = urllib.parse.urljoin(base_url.rstrip("/") + "/", "wp-json/wp/v2/posts")
    for page in range(1, 101):
        query = urllib.parse.urlencode(
            {
                "per_page": 100,
                "page": page,
                "_fields": "id,date,link,slug,status,title,categories,tags",
            }
        )
        result = fetch(f"{endpoint}?{query}", timeout=timeout)
        if result.status == 400 and page > 1:
            break
        if result.status != 200:
            raise RuntimeError("public WordPress post metadata read failed")
        batch = json.loads(result.body.decode("utf-8"))
        if not isinstance(batch, list):
            raise ValueError("public WordPress post metadata is not a list")
        posts.extend(batch)
        if len(batch) < 100:
            break
    return posts


def mature_content_funnel(
    page_rows: list[dict],
    public_posts: list[dict] | None,
    search_period: dict[str, str],
    *,
    minimum_age_days: int = 3,
) -> dict[str, Any] | None:
    """Measure search entry only for posts old enough to appear in GSC data."""
    if public_posts is None or not search_period.get("end"):
        return None
    try:
        cutoff = date.fromisoformat(search_period["end"]) - timedelta(
            days=minimum_age_days
        )
    except ValueError:
        return None

    eligible_paths: set[str] = set()
    for post in public_posts:
        published_at = str(post.get("date", ""))
        try:
            published_moment = datetime.fromisoformat(
                published_at.replace("Z", "+00:00")
            )
            published_on = published_moment.date()
        except ValueError:
            continue
        if post.get("status", "publish") == "publish" and published_on <= cutoff:
            eligible_paths.add(normalize_page_path(str(post.get("link", ""))))

    observed_paths = {
        str(row.get("page", ""))
        for row in page_rows
        if _number(row.get("impressions")) > 0
    }
    clicked_paths = {
        str(row.get("page", ""))
        for row in page_rows
        if _number(row.get("clicks")) > 0
    }
    observed = eligible_paths & observed_paths
    clicked = eligible_paths & clicked_paths
    eligible = len(eligible_paths)
    return {
        "cutoff": cutoff.isoformat(),
        "eligible": eligible,
        "observed": len(observed),
        "clicked": len(clicked),
        "without_impressions": sorted(eligible_paths - observed),
        "search_entry_rate": len(observed) / eligible if eligible else None,
        "click_rate": len(clicked) / eligible if eligible else None,
        "fresh": max(len(public_posts) - eligible, 0),
    }


def hunt_news_performance_funnel(diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Normalize observed metrics into responsibility stages without cross-source joins."""
    search_available = "search_period" in diagnostics and "search_totals" in diagnostics
    ga4_events_available = "ga4_events" in diagnostics
    search_totals = diagnostics.get("search_totals", {})
    event_counts = {
        str(row.get("eventName", "")): _number(row.get("eventCount"))
        for row in diagnostics.get("ga4_events", [])
    }

    def tracked_event(name: str) -> float | None:
        if not ga4_events_available:
            return None
        return event_counts.get(name, 0.0)

    impressions = _number(search_totals.get("impressions")) if search_available else None
    clicks = _number(search_totals.get("clicks")) if search_available else None
    ctr = (
        clicks / impressions
        if clicks is not None and impressions
        else 0.0 if search_available else None
    )
    position = (
        _number(search_totals.get("position"))
        if search_available and impressions and "position" in search_totals
        else None
    )

    return {
        "contract_version": "hunt-news-performance-funnel.v1",
        "cross_source_conversion": None,
        "indexing": {
            "source": None,
            "owner": "Technical SEO",
            "status": "N/A",
        },
        "impression": {
            "source": "Search Console" if search_available else None,
            "owner": "Collector / Scorer / Search intent",
            "impressions": impressions,
            "visible_queries": len(diagnostics.get("search_queries", []))
            if search_available
            else None,
            "average_position": position,
        },
        "click": {
            "source": "Search Console" if search_available else None,
            "owner": "Title / Snippet",
            "clicks": clicks,
            "ctr": ctr,
        },
        "engagement": {
            "source": "GA4 yesterday" if ga4_events_available else None,
            "owner": "Writer / Reviewer",
            "page_view": tracked_event("page_view"),
            "huntlab_engaged_read": tracked_event("huntlab_engaged_read"),
            "huntlab_internal_click": tracked_event("huntlab_internal_click"),
            # These events are not currently instrumented or joined. Their absence
            # must remain unknown rather than becoming an observed zero.
            "article_complete": None,
            "share": None,
            "return_visit": None,
        },
    }


def _funnel_value(value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    if percent:
        return f"{_number(value):.1%}"
    return f"{_number(value):.0f}"


def _rendered_title(post: dict[str, Any]) -> str:
    value = post.get("title", "")
    if isinstance(value, dict):
        value = value.get("rendered", "")
    return str(value).strip()


def build_index_recovery_queue(
    public_posts: list[dict],
    mature_paths: list[str],
    page_rows: list[dict],
    state: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Build a review-only queue with evidence-backed internal-link sources."""
    metrics = {str(row.get("page", "")): row for row in page_rows}
    posts_by_path = {
        normalize_page_path(str(post.get("link", ""))): post
        for post in public_posts
        if post.get("status", "publish") == "publish"
    }
    items: list[dict[str, Any]] = []
    for path in mature_paths:
        target = posts_by_path.get(path)
        if not target:
            continue
        target_categories = {int(value) for value in target.get("categories", [])}
        target_tags = {int(value) for value in target.get("tags", [])}
        ranked_sources: list[tuple[float, dict[str, Any]]] = []
        for source_path, source in posts_by_path.items():
            if source_path == path:
                continue
            shared_categories = target_categories & {
                int(value) for value in source.get("categories", [])
            }
            shared_tags = target_tags & {int(value) for value in source.get("tags", [])}
            if not shared_categories and not shared_tags:
                continue
            source_metrics = metrics.get(source_path, {})
            impressions = _number(source_metrics.get("impressions"))
            clicks = _number(source_metrics.get("clicks"))
            if impressions <= 0:
                continue
            score = clicks * 1000 + impressions + len(shared_tags) * 100 + len(shared_categories) * 25
            ranked_sources.append(
                (
                    score,
                    {
                        "post_id": int(source.get("id", 0)),
                        "title": _rendered_title(source),
                        "url": str(source.get("link", "")),
                        "shared_tag_ids": sorted(shared_tags),
                        "shared_category_ids": sorted(shared_categories),
                        "search_clicks": clicks,
                        "search_impressions": impressions,
                    },
                )
            )
        ranked_sources.sort(key=lambda item: item[0], reverse=True)
        record = state.get("urls", {}).get(str(target.get("link", "")), {})
        latest = record.get("latest", {})
        items.append(
            {
                "target_post_id": int(target.get("id", 0)),
                "target_title": _rendered_title(target),
                "target_url": str(target.get("link", "")),
                "published_at": str(target.get("date", "")),
                "inspection_verdict": latest.get("verdict", "NOT_INSPECTED"),
                "coverage_state": latest.get("coverage_state", ""),
                "last_inspected_at": latest.get("inspected_at", ""),
                "recommended_sources": [item for _, item in ranked_sources[:3]],
                "action": "review_one_contextual_internal_link",
                "automatic_content_mutation": False,
            }
        )
    items.sort(
        key=lambda item: (
            not bool(item["recommended_sources"]),
            item["last_inspected_at"] or "",
            item["published_at"],
        )
    )
    return {
        "version": 1,
        "generated_at": now.isoformat(),
        "status": "REVIEW_REQUIRED",
        "automatic_content_mutation": False,
        "items": items,
    }


def build_ctr_experiment_queue(
    search_rows: list[dict],
    page_rows: list[dict],
    public_posts: list[dict],
    now: datetime,
) -> dict[str, Any]:
    """Queue one-variable CTR experiments without changing public titles."""
    public_by_path = {
        normalize_page_path(str(post.get("link", ""))): post
        for post in public_posts
        if post.get("status", "publish") == "publish"
    }
    top_queries: dict[str, dict[str, Any]] = {}
    for row in search_rows:
        keys = row.get("keys", [])
        if len(keys) < 2:
            continue
        path = normalize_page_path(str(keys[1]))
        current = top_queries.get(path)
        if current is None or _number(row.get("impressions")) > _number(
            current.get("impressions")
        ):
            top_queries[path] = {
                "query": str(keys[0]),
                "impressions": _number(row.get("impressions")),
            }
    items: list[dict[str, Any]] = []
    for row in page_rows:
        path = str(row.get("page", ""))
        post = public_by_path.get(path)
        impressions = _number(row.get("impressions"))
        clicks = _number(row.get("clicks"))
        ctr = _number(row.get("ctr"))
        position = _number(row.get("position"))
        if not post or impressions < 30 or ctr >= 0.02 or not (5 <= position <= 20):
            continue
        items.append(
            {
                "post_id": int(post.get("id", 0)),
                "title": _rendered_title(post),
                "url": str(post.get("link", "")),
                "top_query": top_queries.get(path, {}).get("query", ""),
                "baseline": {
                    "clicks": clicks,
                    "impressions": impressions,
                    "ctr": ctr,
                    "position": position,
                },
                "change_contract": "title_or_meta_one_at_a_time",
                "stop_rule": "14_days_or_1000_impressions",
                "status": "REVIEW_REQUIRED",
            }
        )
    items.sort(key=lambda item: item["baseline"]["impressions"], reverse=True)
    return {
        "version": 1,
        "generated_at": now.isoformat(),
        "status": "REVIEW_REQUIRED",
        "automatic_content_mutation": False,
        "items": items,
    }


def write_json_atomic(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def known_query_breakdown(diagnostics: dict[str, Any]) -> dict[str, float]:
    totals = diagnostics.get("search_totals", {})
    total_clicks = _number(totals.get("clicks"))
    total_impressions = _number(totals.get("impressions"))
    brand_clicks = brand_impressions = nonbrand_clicks = nonbrand_impressions = 0.0
    visible_clicks = visible_impressions = 0.0
    for row in diagnostics.get("search_queries", []):
        query = str((row.get("keys") or [""])[0]).strip().lower()
        clicks = _number(row.get("clicks"))
        impressions = _number(row.get("impressions"))
        visible_clicks += clicks
        visible_impressions += impressions
        if query in BRAND_QUERIES:
            brand_clicks += clicks
            brand_impressions += impressions
        else:
            nonbrand_clicks += clicks
            nonbrand_impressions += impressions
    return {
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
        "known_brand_clicks": brand_clicks,
        "known_brand_impressions": brand_impressions,
        "known_nonbrand_clicks": nonbrand_clicks,
        "known_nonbrand_impressions": nonbrand_impressions,
        "privacy_hidden_clicks": max(total_clicks - visible_clicks, 0.0),
        "privacy_hidden_impressions": max(total_impressions - visible_impressions, 0.0),
    }


def measurement_warnings(
    diagnostics: dict[str, Any], ga_rows: list[dict]
) -> list[str]:
    warnings: list[str] = []
    summary = diagnostics.get("ga4_summary", {})
    yesterday = summary.get("yesterday", {})
    last7 = summary.get("last7days", {})
    if _number(yesterday.get("screenPageViews")) >= 2 and _number(
        yesterday.get("engagedSessions")
    ) == 0:
        events = {
            str(row.get("eventName", "")): _number(row.get("eventCount"))
            for row in diagnostics.get("ga4_events", [])
        }
        if events.get("user_engagement", 0) > 0 or _number(
            yesterday.get("userEngagementDuration")
        ) > 0:
            warnings.append(
                "GA4가 user_engagement와 참여 시간을 수집하지만 참여 세션은 0입니다. "
                "태그 누락보다 속성의 참여 세션 판정·필터 또는 자동 트래픽 가능성을 우선 확인하고, "
                "huntlab_engaged_read를 보조 실독 신호로 사용하세요."
            )
        else:
            warnings.append(
                "어제 페이지뷰가 2회 이상인데 user_engagement와 참여 세션이 모두 0입니다. "
                "GA4 태그 실행·동의 설정 또는 내부 테스트 트래픽을 확인하세요."
            )
    overall_sessions = _number(last7.get("sessions"))
    channel_sessions = sum(
        _number(row.get("sessions")) for row in diagnostics.get("ga4_channels", [])
    )
    if overall_sessions and abs(channel_sessions - overall_sessions) > 0.5:
        warnings.append(
            "채널별 세션 합계가 전체 세션과 일치하지 않습니다. "
            "유입 채널 비율은 방향성으로만 사용하세요."
        )
    total_views = _number(last7.get("screenPageViews"))
    home_views = sum(
        _number(row.get("screenPageViews"))
        for row in ga_rows
        if normalize_page_path(str(row.get("page", ""))) == "/"
    )
    if total_views and home_views / total_views >= 0.5:
        warnings.append(
            f"최근 7일 페이지뷰의 {home_views / total_views:.1%}가 홈페이지에 집중됐습니다. "
            "운영자 확인·새로고침을 외부 방문과 분리하세요."
        )
    return warnings


def analyze(search_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Derive conservative refresh and content-gap candidates."""
    refresh: list[dict] = []
    gaps: list[dict] = []
    for row in search_rows:
        keys = row.get("keys", ["", ""])
        item = {
            "query": keys[0] if keys else "",
            "page": keys[1] if len(keys) > 1 else "",
            "clicks": float(row.get("clicks", 0)),
            "impressions": float(row.get("impressions", 0)),
            "ctr": float(row.get("ctr", 0)),
            "position": float(row.get("position", 0)),
        }
        if item["impressions"] >= 50 and item["ctr"] < 0.02:
            refresh.append({**item, "reason": "high_impressions_low_ctr"})
        if item["impressions"] >= 30 and item["clicks"] == 0 and item["position"] >= 8:
            gaps.append({**item, "reason": "visible_query_without_clicks"})
    return refresh, gaps


def render(
    search_rows: list[dict],
    ga_rows: list[dict],
    now: datetime,
    *,
    diagnostics: dict[str, Any] | None = None,
    site_audit: dict[str, Any] | None = None,
    public_post_metadata: list[dict] | None = None,
    url_inspections: list[dict[str, Any]] | None = None,
    index_checkpoints: list[dict[str, str]] | None = None,
    index_recovery_urls: list[str] | None = None,
    index_recovery_queue: dict[str, Any] | None = None,
    ctr_experiment_queue: dict[str, Any] | None = None,
    shadow_signals: dict[str, dict[str, Any]] | None = None,
) -> str:
    refresh, gaps = analyze(search_rows)
    diagnostics = diagnostics or {}
    query_breakdown = known_query_breakdown(diagnostics)
    page_rows = aggregate_page_rows(diagnostics.get("search_pages", []))
    article_rows = [row for row in page_rows if is_article_path(str(row["page"]))]
    clicked_articles = [row for row in article_rows if _number(row["clicks"]) > 0]
    observed_articles = [row for row in article_rows if _number(row["impressions"]) > 0]
    observation_candidates = [
        row
        for row in article_rows
        if _number(row["clicks"]) == 0
        and _number(row["impressions"]) >= 3
        and 0 < _number(row["position"]) <= 15
    ]
    public_posts = (
        len(public_post_metadata)
        if public_post_metadata is not None
        else int((site_audit or {}).get("counts", {}).get("post", 0))
    )
    period = diagnostics.get("search_period", {})
    mature_funnel = mature_content_funnel(page_rows, public_post_metadata, period)
    period_label = (
        f"{period.get('start', '?')}~{period.get('end', '?')}"
        if period
        else "최근 7일"
    )
    performance_funnel = hunt_news_performance_funnel(diagnostics)
    impression_stage = performance_funnel["impression"]
    click_stage = performance_funnel["click"]
    engagement_stage = performance_funnel["engagement"]
    lines = [
        "# Analytics Optimization Report",
        "",
        "- status: `COMPLETE`",
        f"- generated_at: `{now.isoformat()}`",
        f"- period: `Search Console {period_label}(데이터 지연 고려), GA4 최근 7일`",
        f"- search_console_rows: `{len(search_rows)}`",
        f"- ga4_rows: `{len(ga_rows)}`",
        "- automatic_pipeline: `disabled_review_required`",
        "",
        "## Hunt News 성과 Funnel V1",
        "",
        f"- contract_version: `{performance_funnel['contract_version']}`",
        "- cross_source_conversion: `N/A` — Search Console과 GA4를 동일 모집단으로 간주하지 않음",
        "- zero_semantics: `측정되었으나 발생하지 않음`",
        "- na_semantics: `측정 자체가 없거나 연결할 수 없음`",
        "",
        "| 책임 단계 | 측정 시스템 | 관측값 | 책임 영역 |",
        "|---|---|---|---|",
        "| INDEXING | N/A | N/A | Technical SEO |",
        "| IMPRESSION | {source} | impressions={impressions}, visible_queries={queries}, average_position={position} | Collector / Scorer / Search intent |".format(
            source=impression_stage["source"] or "N/A",
            impressions=_funnel_value(impression_stage["impressions"]),
            queries=_funnel_value(impression_stage["visible_queries"]),
            position=(
                f"{impression_stage['average_position']:.1f}"
                if impression_stage["average_position"] is not None
                else "N/A"
            ),
        ),
        "| CLICK | {source} | clicks={clicks}, CTR={ctr} | Title / Snippet |".format(
            source=click_stage["source"] or "N/A",
            clicks=_funnel_value(click_stage["clicks"]),
            ctr=_funnel_value(click_stage["ctr"], percent=True),
        ),
        "| ENGAGEMENT | {source} | page_view={views}, engaged_read={reads}, internal_click={internal}; article_complete=N/A, share=N/A, return_visit=N/A | Writer / Reviewer |".format(
            source=engagement_stage["source"] or "N/A",
            views=_funnel_value(engagement_stage["page_view"]),
            reads=_funnel_value(engagement_stage["huntlab_engaged_read"]),
            internal=_funnel_value(engagement_stage["huntlab_internal_click"]),
        ),
        "",
        "단계는 같은 진단 언어로만 묶는다. Search Console의 impression→click과 "
        "GA4의 page_view→engaged_read 사이에는 전환율을 계산하지 않는다.",
        "",
        "## 콘텐츠 검색 퍼널 기준점",
        "",
        f"- public_posts: `{public_posts or 'N/A'}`",
        f"- all_observed_article_urls: `{len(observed_articles)}`",
        f"- total_search_clicks: `{query_breakdown['total_clicks']:.0f}`",
        f"- total_search_impressions: `{query_breakdown['total_impressions']:.0f}`",
        f"- known_brand_clicks: `{query_breakdown['known_brand_clicks']:.0f}`",
        f"- known_nonbrand_clicks: `{query_breakdown['known_nonbrand_clicks']:.0f}`",
        f"- privacy_hidden_or_other_clicks: `{query_breakdown['privacy_hidden_clicks']:.0f}`",
    ]
    if mature_funnel:
        entry_rate = mature_funnel["search_entry_rate"]
        click_rate = mature_funnel["click_rate"]
        lines.extend(
            [
                f"- mature_cutoff: `{mature_funnel['cutoff']}`",
                f"- mature_posts_eligible: `{mature_funnel['eligible']}`",
                f"- mature_posts_with_search_impressions: `{mature_funnel['observed']}`",
                f"- mature_posts_with_search_clicks: `{mature_funnel['clicked']}`",
                f"- mature_posts_without_observed_impressions: `{len(mature_funnel['without_impressions'])}`",
                f"- mature_search_entry_rate: `{entry_rate:.1%}`" if entry_rate is not None else "- mature_search_entry_rate: `N/A`",
                f"- mature_click_rate: `{click_rate:.1%}`" if click_rate is not None else "- mature_click_rate: `N/A`",
                f"- fresh_posts_excluded: `{mature_funnel['fresh']}`",
            ]
        )
    else:
        lines.append("- mature_cohort: `N/A`")
    lines.extend(
        [
            "",
            "Search Console의 저빈도 검색어 비공개 처리 때문에 비브랜드 전체 클릭을 "
            "알려진 검색어 합계만으로 단정하지 않는다. 검색 퍼널 비율은 Search Console "
            "종료일 기준 발행 후 3일 이상이며 공개 응답과 발행일이 확인된 글만 계산한다.",
        ]
    )
    if mature_funnel and mature_funnel["without_impressions"]:
        lines.extend(["", "### 검색 노출 미관측 성숙 글", ""])
        lines.extend(
            f"- `{path}`" for path in mature_funnel["without_impressions"]
        )
    lines.extend(
        [
            "",
            "## GA4 측정 기준점",
            "",
            "| 기간 | 사용자 | 세션 | 참여 세션 | 페이지뷰 | 총 참여 시간(초) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for label, display in (
        ("today", "오늘 현재"),
        ("yesterday", "어제"),
        ("last7days", "최근 7일"),
    ):
        item = diagnostics.get("ga4_summary", {}).get(label, {})
        lines.append(
            "| {display} | {users:.0f} | {sessions:.0f} | {engaged:.0f} | "
            "{views:.0f} | {duration:.0f} |".format(
                display=display,
                users=_number(item.get("activeUsers")),
                sessions=_number(item.get("sessions")),
                engaged=_number(item.get("engagedSessions")),
                views=_number(item.get("screenPageViews")),
                duration=_number(item.get("userEngagementDuration")),
            )
        )
    lines += ["", "### 측정 진단", ""]
    warnings = measurement_warnings(diagnostics, ga_rows)
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- 자동 진단에서 명확한 측정 이상 없음")
    ga4_events_available = "ga4_events" in diagnostics
    event_counts = {
        str(row.get("eventName", "")): _number(row.get("eventCount"))
        for row in diagnostics.get("ga4_events", [])
    }
    page_view_events = event_counts.get("page_view", 0) if ga4_events_available else None
    engaged_read_events = (
        event_counts.get("huntlab_engaged_read", 0) if ga4_events_available else None
    )
    internal_click_events = (
        event_counts.get("huntlab_internal_click", 0) if ga4_events_available else None
    )
    read_rate = (
        engaged_read_events / page_view_events
        if page_view_events and engaged_read_events is not None
        else None
    )
    next_click_rate = (
        internal_click_events / engaged_read_events
        if engaged_read_events and internal_click_events is not None
        else None
    )
    lines.extend(
        [
            f"- yesterday_page_view_events: `{_funnel_value(page_view_events)}`",
            f"- yesterday_user_engagement_events: `{_funnel_value(event_counts.get('user_engagement', 0) if ga4_events_available else None)}`",
            f"- yesterday_huntlab_engaged_read_events: `{_funnel_value(engaged_read_events)}`",
            f"- yesterday_huntlab_internal_click_events: `{_funnel_value(internal_click_events)}`",
            f"- yesterday_engaged_read_per_page_view: `{read_rate:.1%}`" if read_rate is not None else "- yesterday_engaged_read_per_page_view: `N/A`",
            f"- yesterday_internal_click_per_engaged_read: `{next_click_rate:.1%}`" if next_click_rate is not None else "- yesterday_internal_click_per_engaged_read: `N/A`",
            f"- yesterday_observed_hosts: `{', '.join(str(row.get('hostName', '')) for row in diagnostics.get('ga4_hosts', []) if row.get('hostName')) or 'N/A'}`",
        ]
    )
    lines += [
        "",
        "## Search Console 유입",
        "",
        "| 검색어 | 페이지 | 클릭 | 노출 | CTR | 평균 순위 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in search_rows[:20]:
        lines.append(
            "| {query} | {page} | {clicks} | {impressions} | {ctr:.1%} | {position:.1f} |".format(
                query=row.get("keys", ["-"])[0].replace("|", "\\|"),
                page=(row.get("keys", ["-", "-"])[1]).replace("|", "\\|"),
                clicks=row.get("clicks", 0),
                impressions=row.get("impressions", 0),
                ctr=row.get("ctr", 0),
                position=row.get("position", 0),
            )
        )
    if not search_rows:
        lines.append("| 데이터 없음 | - | 0 | 0 | 0% | - |")
    lines += ["", "## GA4 페이지 조회", "", "| 경로 | 조회수 |", "|---|---:|"]
    for row in ga_rows[:20]:
        lines.append(f"| {row['page'].replace('|', '\\|')} | {row['screenPageViews']} |")
    if not ga_rows:
        lines.append("| 데이터 없음 | 0 |")
    lines += ["", "## 초기 성공 글", ""]
    if clicked_articles:
        for item in clicked_articles[:10]:
            lines.append(
                f"- `{item['page']}`: 클릭 {item['clicks']:.0f}, "
                f"노출 {item['impressions']:.0f}, CTR {item['ctr']:.1%}, "
                f"평균 순위 {item['position']:.1f} — 자동 수정 없이 성공군으로 관찰"
            )
    else:
        lines.append("- 공개 글 클릭 표본 없음")
    lines += ["", "## 초기 관찰 후보", ""]
    if observation_candidates:
        for item in observation_candidates[:10]:
            lines.append(
                f"- `{item['page']}`: 클릭 0, 노출 {item['impressions']:.0f}, "
                f"평균 순위 {item['position']:.1f} — `disabled_review_required`; "
                "8월 7일 재측정 전 자동 Refresh 금지"
            )
    else:
        lines.append("- 초기 관찰 기준을 충족한 후보 없음")
    lines += ["", "## Refresh 후보", ""]
    if refresh:
        for item in refresh[:10]:
            lines.append(
                f"- `{item['page']}`: `{item['query']}` "
                f"(노출 {item['impressions']:.0f}, CTR {item['ctr']:.1%}) — "
                "제목·Meta Description·첫 화면의 검색 의도 일치를 검토"
            )
    else:
        lines.append("- 관측 임계치를 충족한 후보 없음")
    lines += ["", "## Content Gap 후보", ""]
    if gaps:
        for item in gaps[:10]:
            lines.append(
                f"- `{item['query']}` → `{item['page']}` "
                f"(노출 {item['impressions']:.0f}, 평균 순위 {item['position']:.1f}) — "
                "기존 글 보강을 우선하고 별도 검색 의도일 때만 신규 글 검토"
            )
    else:
        lines.append("- 관측 임계치를 충족한 후보 없음")
    inspections = url_inspections or []
    decisions = aug7_review_decisions(page_rows, inspections, now)
    title_decision = decisions["title_experiment"]
    discovery_decision = decisions["index_discovery"]
    lines += [
        "",
        "## 8월 7일 운영 결정",
        "",
        f"- review_date_ready: `{str(decisions['review_date_ready']).lower()}`",
        f"- resident_title_experiment: `{title_decision['status']}`",
        f"- resident_title_reason: `{title_decision['reason']}`",
    ]
    if "impressions" in title_decision:
        lines.extend(
            [
                "- resident_title_metrics: "
                f"`clicks={title_decision['clicks']:.0f}, "
                f"impressions={title_decision['impressions']:.0f}, "
                f"position={title_decision['position']:.1f}`",
                f"- proposed_single_change: `title_only` → "
                f"`{title_decision['proposed_title']}`",
                f"- experiment_stop_rule: `{title_decision['stop_rule']}`",
            ]
        )
    lines.extend(
        [
            f"- index_discovery_action: `{discovery_decision['status']}`",
            f"- index_discovery_reason: `{discovery_decision['reason']}`",
        ]
    )
    if discovery_decision.get("target_url"):
        lines.extend(
            [
                f"- index_discovery_target: `{discovery_decision['target_url']}`",
                "- proposed_single_change: `one_relevant_internal_link`",
                "- general_blog_indexing_api_submission: `forbidden`",
            ]
        )
    lines.extend(
        [
            "- planner_keyword_rule: "
            "`제품·기술명 + 관측된 오류·문제 + 독자가 실행할 행동`",
            "- planner_invented_problem: `forbidden`",
        ]
    )

    lines += ["", "### Google URL Inspection", ""]
    lines.append(
        "- inspection_slot_allocation: "
        f"`fresh={len(index_checkpoints or [])}, mature_recovery={len(index_recovery_urls or [])}`"
    )
    if index_checkpoints:
        labels = ", ".join(
            f"{item['checkpoint']}:{normalize_page_path(item['url'])}"
            for item in index_checkpoints
        )
        lines.append(f"- fresh_post_checkpoints: `{labels}`")
        lines.append("")
    if index_recovery_urls:
        labels = ", ".join(normalize_page_path(url) for url in index_recovery_urls)
        lines.append(f"- mature_recovery_checks: `{labels}`")
        lines.append("")
    if inspections:
        lines.extend(
            [
                "| URL | 상태 | Verdict | Coverage | 마지막 크롤링 |",
                "|---|---|---|---|---|",
            ]
        )
        for item in inspections:
            lines.append(
                "| {url} | {status} | {verdict} | {coverage} | {crawl} |".format(
                    url=str(item.get("url", "-")).replace("|", "\\|"),
                    status=item.get("status", "N/A"),
                    verdict=item.get("verdict", "N/A"),
                    coverage=str(item.get("coverage_state", "N/A")).replace(
                        "|", "\\|"
                    ),
                    crawl=item.get("last_crawl_time", "N/A") or "N/A",
                )
            )
    else:
        lines.append("- URL Inspection 데이터 없음")

    recovery_items = (index_recovery_queue or {}).get("items", [])
    lines += ["", "### 색인 회복 내부링크 검토 큐", ""]
    lines.append(f"- review_candidates: `{len(recovery_items)}`")
    lines.append("- automatic_content_mutation: `false`")
    for item in recovery_items[:10]:
        lines.append(
            f"- `{normalize_page_path(item.get('target_url', ''))}`: "
            f"추천 출처 `{len(item.get('recommended_sources', []))}`개; "
            f"inspection=`{item.get('inspection_verdict', 'NOT_INSPECTED')}`"
        )
    if not recovery_items:
        lines.append("- 검토 후보 없음")

    ctr_items = (ctr_experiment_queue or {}).get("items", [])
    lines += ["", "### CTR 단일변수 실험 검토 큐", ""]
    lines.append(f"- review_candidates: `{len(ctr_items)}`")
    lines.append("- automatic_content_mutation: `false`")
    for item in ctr_items[:10]:
        baseline = item.get("baseline", {})
        lines.append(
            f"- `{normalize_page_path(item.get('url', ''))}`: "
            f"노출 `{_number(baseline.get('impressions')):.0f}`, "
            f"CTR `{_number(baseline.get('ctr')):.1%}`, "
            f"순위 `{_number(baseline.get('position')):.1f}`; "
            f"query=`{item.get('top_query') or 'N/A'}`"
        )
    if not ctr_items:
        lines.append("- 검토 후보 없음")

    lines += ["", "### Naver·Whereispost Shadow Mode", ""]
    for label, signal in (shadow_signals or {}).items():
        lines.append(
            f"- {label}: `{signal.get('status', 'N/A')}`; "
            f"rows=`{len(signal.get('rows', []))}`; "
            f"reason=`{signal.get('reason', 'provided_export')}`"
        )
    if not shadow_signals:
        lines.append("- optional shadow inputs: `N/A`")
    lines += [
        "",
        "## 다음 사이클 제안",
        "",
        "- 노출 대비 CTR이 낮은 검색어는 제목과 Meta Description 개선 후보로 검토한다.",
        "- 조회 데이터가 있는 페이지는 검색 의도를 해결한 뒤 관련 글 CTA를 검토한다.",
        "- 표본이 없거나 적으면 성과·전환을 추정하지 않는다.",
        "- 정규 Harness가 다음 Planner/Writer 프롬프트에 이 리포트 경로를 명시적으로 제공할 때만 참고한다.",
    ]
    return "\n".join(lines) + "\n"


def write_reports(body: str, now: datetime, report_dir: Path = REPORT_DIR) -> tuple[Path, Path]:
    """Atomically update the pipeline input and the daily snapshot."""
    report_dir.mkdir(parents=True, exist_ok=True)
    latest_path = report_dir / "latest.md"
    dated_path = report_dir / f"{now:%Y-%m-%d}.md"
    for destination in (latest_path, dated_path):
        temporary = report_dir / f".{destination.name}.tmp"
        temporary.write_text(body, encoding="utf-8")
        temporary.replace(destination)
    return latest_path, dated_path


def main() -> int:
    load_env_file(ROOT / ".env")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).astimezone()
    public_site_url = os.environ.get("PUBLIC_SITE_URL", "https://huntlab.app/")
    shadow_signals = collect_shadow_signals(
        _optional_path(os.environ.get("NAVER_SEARCHADVISOR_EXPORT")),
        _optional_path(os.environ.get("WHEREISPOST_SHADOW_EXPORT")),
    )
    public_audit_data: dict[str, Any] | None = None
    public_post_metadata: list[dict] | None = None
    try:
        public_audit_data = audit_site(public_site_url)
        public_audit = render_public_audit(public_audit_data, heading_level=2)
    except Exception as exc:  # noqa: BLE001 - public audit must not block analytics
        public_audit = (
            "## Public Site Quality Audit\n\n"
            "- status: `INCOMPLETE`\n"
            f"- error_type: `{type(exc).__name__}`\n"
            "- error: `public read failed; no site setting was changed`\n"
        )
    try:
        public_post_metadata = collect_public_posts(public_site_url)
    except Exception:  # noqa: BLE001 - cohort can be N/A without blocking analytics
        public_post_metadata = None
    try:
        search_rows, ga_rows, diagnostics = collect()
        page_rows = aggregate_page_rows(diagnostics.get("search_pages", []))
        mature_funnel = mature_content_funnel(
            page_rows,
            public_post_metadata,
            diagnostics.get("search_period", {}),
        )
        checkpoint_state = read_index_checkpoint_state()
        mature_urls = [
            urllib.parse.urljoin(
                public_site_url,
                urllib.parse.quote(path.lstrip("/"), safe="/"),
            )
            for path in (mature_funnel or {}).get("without_impressions", [])
        ]
        index_checkpoints, recovery_urls = allocate_index_inspection_targets(
            public_post_metadata or [],
            mature_urls,
            checkpoint_state,
            now,
        )
        checkpoint_urls = [item["url"] for item in index_checkpoints]
        inspection_urls = checkpoint_urls + recovery_urls
        url_inspections = collect_url_inspections(inspection_urls)
        checkpoint_state = update_index_checkpoint_state(
            checkpoint_state,
            index_checkpoints,
            url_inspections,
            now,
            recovery_urls=recovery_urls,
        )
        write_index_checkpoint_state(checkpoint_state)
        index_recovery_queue = build_index_recovery_queue(
            public_post_metadata or [],
            (mature_funnel or {}).get("without_impressions", []),
            page_rows,
            checkpoint_state,
            now,
        )
        ctr_experiment_queue = build_ctr_experiment_queue(
            search_rows,
            page_rows,
            public_post_metadata or [],
            now,
        )
        write_json_atomic(index_recovery_queue, INDEX_RECOVERY_QUEUE)
        write_json_atomic(ctr_experiment_queue, CTR_EXPERIMENT_QUEUE)
        body = render(
            search_rows,
            ga_rows,
            now,
            diagnostics=diagnostics,
            site_audit=public_audit_data,
            public_post_metadata=public_post_metadata,
            url_inspections=url_inspections,
            index_checkpoints=index_checkpoints,
            index_recovery_urls=recovery_urls,
            index_recovery_queue=index_recovery_queue,
            ctr_experiment_queue=ctr_experiment_queue,
            shadow_signals=shadow_signals,
        )
        body += "\n" + public_audit
        status = "COMPLETE"
    except Exception as exc:  # noqa: BLE001 - safe operational report
        body = (
            "# Analytics Optimization Report\n\n"
            "- status: `INCOMPLETE`\n"
            f"- generated_at: `{now.isoformat()}`\n"
            f"- error_type: `{type(exc).__name__}`\n"
            "- error: `API read failed; credentials are not logged`\n"
            "\n" + public_audit
        )
        status = "INCOMPLETE"
    latest_path, dated_path = write_reports(body, now)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    (LOG_DIR / f"analytics-{now:%Y-%m-%d}.log").open("a", encoding="utf-8").write(
        f"{now.isoformat()} status={status} report_sha256={digest} credentials=not_logged\n"
    )
    print(
        f"analytics status={status} report={latest_path} "
        f"daily_snapshot={dated_path}"
    )
    return 0 if status == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
