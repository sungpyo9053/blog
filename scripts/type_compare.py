"""GSC impressions/clicks per published post, grouped by post type, for 4 one-week windows.
usage (runner): PYTHONPATH=. .venv/bin/python scripts/type_compare.py [END_DATE] [--frozen]   — 11/08 type comparison;
--frozen compares the pages edited on 10/31 (impressions 10/18~10/30) before vs after."""
import collections, datetime as dt, json, re, sys, urllib.request
from pathlib import Path
from scripts.weekly_editorial_metrics import _query, _session, load_env_file

PRICE = re.compile(r"calculator|price|fee|cost|plans|pass|membership|interest|tax|allowance|pension|salary|wage|refund|premium")
ROS = re.compile(r"ros|rclpy|colcon|robot|gazebo|tf2|physical-ai|sensor|gymnasium|gaussian|wordpress|topic-planner|evidence")


def kind(link):
    path = link.split("huntlab.app", 1)[1]
    if path == "/melon-pass-price-guide/":
        return "멜론 #514"  # one post with ~70% of KO impressions; kept apart so it does not decide the type
    if path.startswith("/en/"):
        return "EN"
    if ROS.search(path):
        return "KO ROS·개발"
    return "KO 계산기·가격" if PRICE.search(path) else "KO 서류·제도"


def frozen(s, U, end):
    """Pages with impressions 10/18~10/30 were edited on 10/31 night and frozen; compare per-day before vs 11/01~end."""
    pre, post = ("2026-10-18", "2026-10-30"), ("2026-11-01", str(end))
    days = lambda w: (dt.date.fromisoformat(w[1]) - dt.date.fromisoformat(w[0])).days + 1
    q = lambda w: {r["keys"][0]: r for r in _query(s, U, {"startDate": w[0], "endDate": w[1], "dimensions": ["page"], "rowLimit": 1000}).get("rows", [])}
    a, b = q(pre), q(post)
    print(f"frozen {len(a)} pages, before {pre[0]}~{pre[1]} ({days(pre)}d) vs after {post[0]}~{post[1]} ({days(post)}d), per day")
    tot = [0, 0, 0, 0]
    for link, r in sorted(a.items(), key=lambda kv: -kv[1]["impressions"]):
        n = b.get(link, {"impressions": 0, "clicks": 0, "position": 0})
        tot = [tot[0] + r["impressions"], tot[1] + r["clicks"], tot[2] + n["impressions"], tot[3] + n["clicks"]]
        print(f"{link.split('huntlab.app', 1)[1]}\t노출/일 {r['impressions'] / days(pre):.1f}→{n['impressions'] / days(post):.1f}\t클릭 {r['clicks']}→{n['clicks']}\t"
              f"CTR {r['ctr'] * 100:.1f}%→{(n['clicks'] / n['impressions'] * 100 if n['impressions'] else 0):.1f}%\t순위 {r['position']:.1f}→{n['position']:.1f}")
    print(f"합계 노출/일 {tot[0] / days(pre):.1f}→{tot[2] / days(post):.1f} 클릭/일 {tot[1] / days(pre):.2f}→{tot[3] / days(post):.2f} "
          f"CTR {tot[1] / max(tot[0], 1) * 100:.2f}%→{tot[3] / max(tot[2], 1) * 100:.2f}%")


def main():
    args = [a for a in sys.argv[1:] if a != "--frozen"]
    end = dt.date.fromisoformat(args[0]) if args else dt.date.today() - dt.timedelta(days=3)
    if "--frozen" in sys.argv:
        load_env_file(Path(".env"))
        return frozen(_session(), "https://searchconsole.googleapis.com/webmasters/v3/sites/sc-domain%3Ahuntlab.app/searchAnalytics/query", end)
    load_env_file(Path(".env")); s = _session()
    get = lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "HuntLab-Operator/1.0"}), timeout=30).read())
    posts = {}
    for k in ("posts", "hunt_en"):
        for page in (1, 2, 3):
            try:
                rows = get(f"https://huntlab.app/wp-json/wp/v2/{k}?per_page=100&page={page}&_fields=link,date")
            except Exception:
                break
            for p in rows:
                posts[p["link"].replace("http://", "https://")] = p["date"][:10]
    U = "https://searchconsole.googleapis.com/webmasters/v3/sites/sc-domain%3Ahuntlab.app/searchAnalytics/query"
    print("end", end, "posts", len(posts))
    for w in range(3, -1, -1):
        a, b = end - dt.timedelta(days=7 * w + 6), end - dt.timedelta(days=7 * w)
        rows = _query(s, U, {"startDate": str(a), "endDate": str(b), "dimensions": ["page"], "rowLimit": 1000}).get("rows", [])
        gsc = {r["keys"][0]: r for r in rows}
        agg = collections.defaultdict(lambda: [0, 0, 0])
        for link, date in posts.items():
            if date > str(b):
                continue
            t = agg[kind(link)]; t[0] += 1
            r = gsc.get(link)
            if r:
                t[1] += r["impressions"]; t[2] += r["clicks"]
        print(f"{a}~{b}", " | ".join(f"{k} {n}편 노출 {i} (편당 {i / n:.1f}) 클릭 {c}" for k, (n, i, c) in sorted(agg.items())))


if __name__ == "__main__":
    main()
