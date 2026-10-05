#!/usr/bin/env python3
"""Kakao: how many live posts (ko + /en/) Google has indexed (URL Inspection, read-only).
Bing and Naver have no API access here, so the message reminds Claude to read their consoles."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def summarize(states: list[str]) -> str:
    indexed = sum("indexed" in s.lower() and "not indexed" not in s.lower() for s in states)
    return f"구글 색인 {indexed}/{len(states)}편"


def main() -> int:
    from scripts.run_analytics_optimizer import collect_url_inspections
    from scripts.weekly_editorial_metrics import load_env_file
    load_env_file(ROOT / ".env")
    get = lambda url: json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "HuntLab-Operator/1.0"}), timeout=30).read())
    urls = [p["link"] for kind in ("posts", "hunt_en")
            for p in get(f"https://huntlab.app/wp-json/wp/v2/{kind}?per_page=100&_fields=link")]
    states = [item.get("coverage_state", "") for item in collect_url_inspections(urls)]
    message = f"[HuntLab 색인 비교 알림]\n{summarize(states)}\nClaude: Bing·Naver 콘솔 색인 수와 비교해 보고할 것"
    from scripts.send_kakao_report import send
    send(message[:200], os.environ.get("MCPORTER_BIN", "mcporter"))
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
