"""Read-only Search Console and GA4 report generator."""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publisher.config import load_env_file
from scripts.audit_public_site import audit_site, render_markdown as render_public_audit

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "output" / "analytics"
LOG_DIR = ROOT / "logs"


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
    diagnostics: dict[str, Any] = {
        "search_period": {"start": start.isoformat(), "end": end.isoformat()},
        "search_totals": search_totals[0] if search_totals else {},
        "search_daily": search_daily,
        "search_queries": search_queries,
        "search_pages": search_pages,
        "ga4_summary": summary,
        "ga4_channels": channel_rows,
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


def mature_content_funnel(
    page_rows: list[dict],
    site_audit: dict[str, Any] | None,
    search_period: dict[str, str],
    *,
    minimum_age_days: int = 3,
) -> dict[str, Any] | None:
    """Measure search entry only for posts old enough to appear in GSC data."""
    if not site_audit or not search_period.get("end"):
        return None
    try:
        cutoff = date.fromisoformat(search_period["end"]) - timedelta(
            days=minimum_age_days
        )
    except ValueError:
        return None

    post_count = int(site_audit.get("counts", {}).get("post", 0))
    post_pages = site_audit.get("pages", [])[:post_count]
    eligible_paths: set[str] = set()
    for page in post_pages:
        published_at = str(page.get("published_at", ""))
        try:
            published_moment = datetime.fromisoformat(
                published_at.replace("Z", "+00:00")
            )
            if published_moment.tzinfo is not None:
                published_moment = published_moment.astimezone(
                    timezone(timedelta(hours=9))
                )
            published_on = published_moment.date()
        except ValueError:
            continue
        if page.get("status") == 200 and published_on <= cutoff:
            eligible_paths.add(normalize_page_path(str(page.get("url", ""))))

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
        "fresh_or_unverified": max(post_count - eligible, 0),
    }


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
        warnings.append(
            "어제 페이지뷰가 2회 이상인데 참여 세션이 0입니다. "
            "GA4 event/session 설정 또는 내부 테스트 트래픽을 확인하세요."
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
    public_posts = int((site_audit or {}).get("counts", {}).get("post", 0))
    period = diagnostics.get("search_period", {})
    mature_funnel = mature_content_funnel(page_rows, site_audit, period)
    period_label = (
        f"{period.get('start', '?')}~{period.get('end', '?')}"
        if period
        else "최근 7일"
    )
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
                f"- fresh_or_unverified_posts_excluded: `{mature_funnel['fresh_or_unverified']}`",
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
    public_audit_data: dict[str, Any] | None = None
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
        search_rows, ga_rows, diagnostics = collect()
        body = render(
            search_rows,
            ga_rows,
            now,
            diagnostics=diagnostics,
            site_audit=public_audit_data,
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
