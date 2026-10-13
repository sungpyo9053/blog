#!/usr/bin/env python3
"""Weekly Kakao: progress toward the $200/month goal (GA4 + GSC, read-only).

AdSense/Coupang revenue has no API access here, so the report shows the last
console figure the user gave, recorded in editorial/operations/revenue-actual.tsv.
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REVENUE_LOG = ROOT / "editorial/operations/revenue-actual.tsv"
# (deadline, weekly sessions target) — see editorial/operations/revenue-200-plan.md
MILESTONES = [
    (date(2026, 10, 24), 70),
    (date(2026, 11, 30), 210),
    (date(2026, 12, 31), 700),
    (date(2027, 3, 31), 2100),
    (date(2027, 6, 30), 7000),
]


def target_for(today: date) -> tuple[date, int]:
    return next((m for m in MILESTONES if today <= m[0]), MILESTONES[-1])


def last_revenue(path: Path = REVENUE_LOG) -> str:
    """'MM/DD 확인 애드센스 $x·쿠팡 y원' from the newest row, never an estimate."""
    day, adsense, coupang = path.read_text().strip().splitlines()[-1].split("\t")
    return f"{day[5:7]}/{day[8:]} 확인 애드센스 ${float(adsense):.2f}·쿠팡 {int(coupang):,}원"


def message(today: date, sessions: int, views: int, organic: int, clicks: int, impressions: int, revenue: str) -> str:
    deadline, goal = target_for(today)
    verdict = "순항" if sessions >= goal else f"미달({sessions * 100 // max(goal, 1)}%)"
    return (f"[HuntLab $200 주간]\n지난7일 방문 {sessions}·조회 {views}·검색유입 {organic}\n"
            f"구글 클릭 {clicks}·노출 {impressions}\n"
            f"목표 {deadline:%m/%d}까지 주 {goal}방문 → {verdict}\n"
            f"실수익({revenue}) / 월 $200")[:200]


def main() -> int:
    from scripts.weekly_editorial_metrics import _query, _session, load_env_file
    load_env_file(ROOT / ".env")
    session = _session()
    ga = _query(session, f"https://analyticsdata.googleapis.com/v1beta/properties/{os.environ['GA4_PROPERTY_ID']}:runReport",
                {"dateRanges": [{"startDate": "7daysAgo", "endDate": "yesterday"}],
                 "dimensions": [{"name": "sessionDefaultChannelGroup"}],
                 "metrics": [{"name": "sessions"}, {"name": "screenPageViews"}]})
    rows = [(r["dimensionValues"][0]["value"], int(r["metricValues"][0]["value"]), int(r["metricValues"][1]["value"]))
            for r in ga.get("rows", [])]
    end = date.today() - timedelta(days=2)
    gsc = _query(session, "https://searchconsole.googleapis.com/webmasters/v3/sites/sc-domain%3Ahuntlab.app/searchAnalytics/query",
                 {"startDate": (end - timedelta(days=6)).isoformat(), "endDate": end.isoformat()}).get("rows") or [{}]
    text = message(date.today(), sum(r[1] for r in rows), sum(r[2] for r in rows),
                   sum(r[1] for r in rows if r[0] == "Organic Search"),
                   int(gsc[0].get("clicks", 0)), int(gsc[0].get("impressions", 0)), last_revenue())
    print(text)
    if "--send" in sys.argv:
        from scripts.send_kakao_report import send
        send(text, os.environ.get("MCPORTER_BIN", "mcporter"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
