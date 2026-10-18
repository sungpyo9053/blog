"""Find keywords with high Naver search volume and few blog documents.

Method: expand seeds via Naver Search Ad keywordstool (related keywords + monthly volume),
then count blog documents via Naver Search API, rank by volume / documents.

Keys come from ~/.config/huntlab/naver.env (never printed):
  NAVER_SEARCHAD_API_KEY, NAVER_SEARCHAD_SECRET, NAVER_SEARCHAD_CUSTOMER_ID,
  NAVER_CLIENT_ID, NAVER_CLIENT_SECRET

Usage: python3 scripts/keyword_gap.py "유튜브 프리미엄 가격" "넷플릭스 요금제" [--top 60]
"""
import base64, hashlib, hmac, json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path


def load_keys(path=Path.home() / ".config/huntlab/naver.env"):
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def count(v):
    # Search Ad returns "< 10" for tiny volumes.
    return 5 if isinstance(v, str) else int(v)


def get(url, headers):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as r:
        return json.loads(r.read())


def related(seeds):
    path, ts = "/keywordstool", str(int(time.time() * 1000))
    sig = base64.b64encode(hmac.new(os.environ["NAVER_SEARCHAD_SECRET"].encode(), f"{ts}.GET.{path}".encode(), hashlib.sha256).digest()).decode()
    q = urllib.parse.urlencode({"hintKeywords": ",".join(s.replace(" ", "") for s in seeds[:5]), "showDetail": 1})
    data = get(f"https://api.searchad.naver.com{path}?{q}", {
        "X-Timestamp": ts, "X-API-KEY": os.environ["NAVER_SEARCHAD_API_KEY"],
        "X-Customer": os.environ["NAVER_SEARCHAD_CUSTOMER_ID"], "X-Signature": sig})
    return {k["relKeyword"]: count(k["monthlyPcQcCnt"]) + count(k["monthlyMobileQcCnt"]) for k in data["keywordList"]}


def blog_docs(keyword):
    q = urllib.parse.urlencode({"query": keyword, "display": 1})
    return get(f"https://openapi.naver.com/v1/search/blog.json?{q}", {
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"], "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"]})["total"]


def verdict(volume, docs):
    # ponytail: fixed thresholds, tune after a few weeks of GSC results.
    ratio = docs / max(volume, 1)
    if volume < 300:
        return "수요 적음"
    return "공략" if ratio < 3 else "가능" if ratio < 10 else "경쟁 심함"


def main(argv):
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 60
    seeds = [a for a in argv if not a.startswith("--") and not a.isdigit()]
    load_keys()
    vols = {}
    for i in range(0, len(seeds), 5):
        vols.update(related(seeds[i:i + 5]))
    rows = []
    for kw, vol in sorted(vols.items(), key=lambda x: -x[1])[:top]:
        docs = blog_docs(kw)
        rows.append((kw, vol, docs, verdict(vol, docs)))
        time.sleep(0.1)
    rows.sort(key=lambda r: (r[3] != "공략", r[3] != "가능", -r[1] / max(r[2], 1)))
    print("키워드\t월검색량\t블로그문서\t판정")
    for r in rows:
        print("\t".join(map(str, r)))


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        assert count("< 10") == 5 and count(1200) == 1200
        assert verdict(100, 1) == "수요 적음" and verdict(1000, 2000) == "공략"
        assert verdict(1000, 5000) == "가능" and verdict(1000, 50000) == "경쟁 심함"
        print("ok")
    else:
        main(sys.argv[1:])
