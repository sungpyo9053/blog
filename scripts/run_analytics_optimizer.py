"""Read-only Search Console and GA4 report generator."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publisher.config import load_env_file

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


def render(search_rows: list[dict], ga_rows: list[dict], now: datetime) -> str:
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
    lines += [
        "",
        "## 다음 사이클 제안",
        "",
        "- 노출 대비 CTR이 낮은 검색어는 제목과 Meta Description 개선 후보로 검토한다.",
        "- 조회 데이터가 있는 페이지는 검색 의도를 해결한 뒤 관련 글 CTA를 검토한다.",
        "- 표본이 없거나 적으면 성과·전환을 추정하지 않는다.",
        "- 이 리포트는 다음 Planner/Writer 호출에 명시적으로 전달할 때만 참고한다.",
    ]
    return "\n".join(lines) + "\n"


def content_gap(search_rows: list[dict], ga_rows: list[dict]) -> bool:
    """Require meaningful data before starting an extra publishing run."""
    impressions = sum(float(row.get("impressions", 0)) for row in search_rows)
    return len(search_rows) >= 5 and impressions >= 100 and bool(ga_rows)


def trigger_pipeline_if_needed(
    search_rows: list[dict], ga_rows: list[dict], now: datetime
) -> str:
    if not content_gap(search_rows, ga_rows):
        return "not_triggered_insufficient_signal"
    marker = LOG_DIR / f"analytics-trigger-{now:%Y-%m-%d}.lock"
    if marker.exists():
        return "not_triggered_daily_limit"
    marker.write_text(now.isoformat(), encoding="utf-8")
    command = [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/run_daily_pipeline.py")]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=21600,
        check=False,
    )
    return (
        "triggered_pipeline_success"
        if result.returncode == 0
        else f"triggered_pipeline_failed_exit_{result.returncode}"
    )


def main() -> int:
    load_env_file(ROOT / ".env")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).astimezone()
    try:
        search_rows, ga_rows = collect()
        body = render(search_rows, ga_rows, now)
        body += f"\n- automatic_pipeline: `{trigger_pipeline_if_needed(search_rows, ga_rows, now)}`\n"
        status = "COMPLETE"
    except Exception as exc:  # noqa: BLE001 - safe operational report
        body = (
            "# Analytics Optimization Report\n\n"
            "- status: `INCOMPLETE`\n"
            f"- generated_at: `{now.isoformat()}`\n"
            f"- error_type: `{type(exc).__name__}`\n"
            "- error: `API read failed; credentials are not logged`\n"
        )
        status = "INCOMPLETE"
    temporary = REPORT_DIR / ".latest.md.tmp"
    temporary.write_text(body, encoding="utf-8")
    temporary.replace(REPORT_DIR / "latest.md")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    (LOG_DIR / f"analytics-{now:%Y-%m-%d}.log").open("a", encoding="utf-8").write(
        f"{now.isoformat()} status={status} report_sha256={digest} credentials=not_logged\n"
    )
    print(f"analytics status={status} report={REPORT_DIR / 'latest.md'}")
    return 0 if status == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
