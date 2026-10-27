"""Daily benchmark: how many posts revenue WordPress sites publish vs us.

usage: python3 scripts/bench_velocity.py [--titles N]
Prints TSV: site, total posts, posts last 7d, posts last 30d, then recent titles (topic gap check).
Uses only the public WP REST API (/wp-json/wp/v2/posts), one request per site.
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

SITES = [
    "https://huntlab.app",
    "https://aboda.kr", "https://benefitshub.co.kr", "https://blanclucy.co.kr", "https://foxcg.com",
    "https://patross0303.com", "https://thecheck.co.kr", "https://yellowit.co.kr",
]


def fetch(site):
    url = f"{site}/wp-json/wp/v2/posts?per_page=100&_fields=date_gmt,title"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (HuntLab benchmark; +https://huntlab.app)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return int(r.headers.get("X-WP-Total") or 0), json.load(r)


def main():
    n_titles = int(sys.argv[sys.argv.index("--titles") + 1]) if "--titles" in sys.argv else 0
    now = datetime.now(timezone.utc)
    print("site\ttotal\t7d\t30d")
    for site in SITES:
        try:
            total, posts = fetch(site)
        except Exception as e:  # one blocked site must not stop the daily run
            print(f"{site}\tERR {type(e).__name__}")
            continue
        dates = [datetime.fromisoformat(p["date_gmt"]).replace(tzinfo=timezone.utc) for p in posts]
        d7 = sum(d > now - timedelta(days=7) for d in dates)
        d30 = sum(d > now - timedelta(days=30) for d in dates)
        # ponytail: 30d count caps at 100 (one page); fine while no site posts >100/month
        print(f"{site}\t{total}\t{d7}\t{d30}")
        for p in posts[:n_titles]:
            print(f"  {p['date_gmt'][:10]} {p['title']['rendered'][:70]}")


if __name__ == "__main__":
    main()
