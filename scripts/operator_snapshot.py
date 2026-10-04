#!/usr/bin/env python3
"""Midnight operator report to Kakao: publication, queue, yesterday's traffic and ad revenue,
and the last 7 days of Google Search (impressions, clicks, CTR, top query). Deterministic, no LLM."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

KST = ZoneInfo("Asia/Seoul")


def search_week(session, query, today):
    site = os.environ["SEARCH_CONSOLE_SITE_URL"]
    url = "https://www.googleapis.com/webmasters/v3/sites/" + quote(site, safe="") + "/searchAnalytics/query"
    body = {"startDate": (today - timedelta(days=9)).isoformat(), "endDate": (today - timedelta(days=3)).isoformat(),
            "dataState": "all", "type": "web"}
    totals = (query(session, url, dict(body, rowLimit=1)).get("rows") or [{}])[0]
    top = query(session, url, dict(body, dimensions=["query"], rowLimit=1)).get("rows") or []
    english = (query(session, url, dict(body, rowLimit=1, dimensionFilterGroups=[{"filters": [
        {"dimension": "page", "operator": "contains", "expression": "/en/"}]}])).get("rows") or [{}])[0]
    return {"impressions": int(totals.get("impressions", 0)), "clicks": int(totals.get("clicks", 0)),
            "ctr": round(totals.get("ctr", 0) * 100, 1), "top_query": top[0]["keys"][0] if top else None,
            "en_impressions": int(english.get("impressions", 0)), "en_clicks": int(english.get("clicks", 0))}


def analytics_yesterday(session, query, today):
    from scripts.weekly_editorial_metrics import HOST
    url = "https://analyticsdata.googleapis.com/v1beta/properties/" + os.environ["GA4_PROPERTY_ID"] + ":runReport"
    day = (today - timedelta(days=1)).isoformat()
    data = query(session, url, {"dateRanges": [{"startDate": day, "endDate": day}],
                                "metrics": [{"name": n} for n in ("screenPageViews", "sessions", "totalAdRevenue",
                                                                  "userEngagementDuration", "activeUsers")],
                                "dimensionFilter": {"filter": {"fieldName": "hostName", "stringFilter": {
                                    "matchType": "EXACT", "value": HOST, "caseSensitive": False}}}})
    values = [float(v["value"]) for v in (data.get("rows") or [{"metricValues": [{"value": 0}] * 5}])[0]["metricValues"]]
    # GA4's "average engagement time per active user".
    return {"views": int(values[0]), "sessions": int(values[1]), "revenue": round(values[2], 2),
            "engaged_seconds": round(values[3] / values[4]) if values[4] else 0}


def site_today(today, fetch_json):
    after = today.isoformat() + "T00:00:00"
    ko = fetch_json(f"https://huntlab.app/wp-json/wp/v2/posts?after={after}&_fields=id")
    en = fetch_json(f"https://huntlab.app/wp-json/wp/v2/hunt_en?after={after}&_fields=id")
    return len(ko), len(en)


def due_today(rows, today):
    """The report runs at 00:00, before the 10:00 release, so count today's scheduled pair as well."""
    due = [r for r in rows if r["status"] == "scheduled" and str(r.get("scheduled_at", ""))[:10] == today.isoformat()]
    return len(due), sum(bool(r.get("english")) for r in due)


def compose(today, published, queue_depth, analytics, search):
    lines = [f"[HuntLab 일일 {today.strftime('%m/%d')}]",
             f"오늘 공개 한{published[0]} 영{published[1]} · 대기 {queue_depth}편"]
    lines.append(f"어제 조회 {analytics['views']} 세션 {analytics['sessions']} 광고 ${analytics['revenue']}"
                 if analytics else "어제 GA4 조회 실패")
    if analytics:
        lines.append(f"평균 참여 {analytics.get('engaged_seconds', 0)}초/명")
    if search:
        lines.append(f"검색7일 노출 {search['impressions']} 클릭 {search['clicks']} ({search['ctr']}%)"
                     f" · 영문 {search.get('en_impressions', 0)}/{search.get('en_clicks', 0)}")
        if search["top_query"]:
            lines.append(f"상위 검색어: {search['top_query'][:40]}")
    else:
        lines.append("검색 조회 실패")
    return "\n".join(lines)[:200]


def main() -> int:
    import urllib.request
    from scripts import editorial_queue as queue
    from scripts.weekly_editorial_metrics import _query, _session, load_env_file
    load_env_file(ROOT / ".env")
    today = datetime.now(KST).date()
    fetch_json = lambda url: json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "HuntLab-Operator/1.0"}), timeout=30).read())
    rows = queue.rows(ROOT)
    live, due = site_today(today, fetch_json), due_today(rows, today)
    published = (live[0] + due[0], live[1] + due[1])
    depth = sum(row["status"] in ("queued", "scheduled") for row in rows)
    analytics = search = None
    session = _session()
    try:
        analytics = analytics_yesterday(session, _query, today)
    except Exception:
        pass
    try:
        search = search_week(session, _query, today)
    except Exception:
        pass
    message = compose(today, published, depth, analytics, search)
    receipt = ROOT / "output/operator-snapshot" / f"{today.isoformat()}.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    try:
        from scripts.send_kakao_report import send
        send(message, os.environ.get("MCPORTER_BIN", "mcporter"))
        status = "sent"
    except Exception:
        status = "failed"
    receipt.write_text(json.dumps({"message": message, "status": status}, ensure_ascii=False))
    print(message)
    return 0 if status == "sent" else 1


if __name__ == "__main__":
    raise SystemExit(main())
