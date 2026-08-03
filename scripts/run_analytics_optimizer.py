"""Read-only Search Console and GA4 report generator."""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

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


def collect() -> tuple[list[dict], list[dict]]:
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
    response = (
        search.searchanalytics()
        .query(
            siteUrl=site_url,
            body={
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "dimensions": ["query", "page"],
                "rowLimit": 50,
            },
        )
        .execute()
    )
    search_rows = response.get("rows", [])

    analytics = BetaAnalyticsDataClient(credentials=credentials)
    request = RunReportRequest(
        property="properties/" + os.environ["GA4_PROPERTY_ID"],
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews")],
        limit=50,
    )
    ga_rows = []
    for row in analytics.run_report(request).rows:
        ga_rows.append(
            {
                "page": row.dimension_values[0].value,
                "screenPageViews": row.metric_values[0].value,
            }
        )
    return search_rows, ga_rows


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


def render(search_rows: list[dict], ga_rows: list[dict], now: datetime) -> str:
    refresh, gaps = analyze(search_rows)
    lines = [
        "# Analytics Optimization Report",
        "",
        "- status: `COMPLETE`",
        f"- generated_at: `{now.isoformat()}`",
        "- period: `Search Console 최근 7일(데이터 지연 고려), GA4 최근 7일`",
        f"- search_console_rows: `{len(search_rows)}`",
        f"- ga4_rows: `{len(ga_rows)}`",
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
    try:
        public_audit = render_public_audit(audit_site(public_site_url), heading_level=2)
    except Exception as exc:  # noqa: BLE001 - public audit must not block analytics
        public_audit = (
            "## Public Site Quality Audit\n\n"
            "- status: `INCOMPLETE`\n"
            f"- error_type: `{type(exc).__name__}`\n"
            "- error: `public read failed; no site setting was changed`\n"
        )
    try:
        search_rows, ga_rows = collect()
        body = render(search_rows, ga_rows, now)
        body += "\n" + public_audit
        body += "\n- automatic_pipeline: `disabled_review_required`\n"
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
