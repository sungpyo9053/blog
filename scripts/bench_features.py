"""Daily feature diff: revenue WordPress sites vs huntlab, ~45 HTML-observable features.

usage: python3 scripts/bench_features.py [--posts 3] [--json out.json]
For each site: home page + N latest posts (via public WP REST). A site's value = mean over its posts.
Output: matrix + loss list (features most benchmark sites have and we lack/underuse), sorted by gap.
Stdlib only, regex-based heuristics (not a full HTML parser) — check surprising rows by eye.
"""
import json
import re
import sys
import time
import urllib.request
from statistics import median

US = "https://huntlab.app"
BENCH = ["https://aboda.kr", "https://benefitshub.co.kr", "https://blanclucy.co.kr", "https://foxcg.com",
         "https://patross0303.com", "https://thecheck.co.kr", "https://yellowit.co.kr"]
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36",
      "Accept": "text/html"}


def get(url):
    t = time.time()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return r.read().decode("utf-8", "replace"), time.time() - t, r.status


def c(pat, h):
    return len(re.findall(pat, h, re.I))


def has(pat, h):
    return 1 if re.search(pat, h, re.I | re.S) else 0


def body(h):
    m = re.search(r'<(article|main)\b.*?</\1>', h, re.I | re.S)
    return m.group(0) if m else h


def title(h):
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


POST_FEATURES = {
    "title_len": lambda h, a: len(title(h)),
    "title_year": lambda h, a: has(r"20\d\d", title(h)),
    "title_총정리/방법/비교": lambda h, a: has(r"총정리|방법|비교|정리|해결|가이드", title(h)),
    "meta_desc": lambda h, a: has(r'<meta[^>]+name="description"', h),
    "og_image": lambda h, a: has(r'property="og:image"', h),
    "og_image_w>=1200": lambda h, a: 1 if any(int(x) >= 1200 for x in re.findall(r'og:image:width"\s+content="(\d+)"', h)) else 0,
    "max_image_preview_large": lambda h, a: has(r"max-image-preview:large", h),
    "featured_img": lambda h, a: has(r'wp-post-image', h),
    "schema_article": lambda h, a: has(r'"@type"\s*:\s*"(BlogPosting|Article|NewsArticle)"', h),
    "schema_faq": lambda h, a: has(r'"@type"\s*:\s*"FAQPage"', h),
    "schema_breadcrumb": lambda h, a: has(r'"@type"\s*:\s*"BreadcrumbList"', h),
    "breadcrumb_ui": lambda h, a: has(r'class="[^"]*breadcrumb', h),
    "toc": lambda h, a: has(r'ez-toc|rank-math-toc|lwptoc|class="[^"]*\btoc\b|id="toc|목차', a),
    "faq_section": lambda h, a: has(r"자주 묻는|FAQ", a),
    "h2": lambda h, a: c(r"<h2\b", a),
    "h3": lambda h, a: c(r"<h3\b", a),
    "tables": lambda h, a: c(r"<table\b", a),
    "images": lambda h, a: c(r"<img\b", a),
    "video_iframe": lambda h, a: c(r"<iframe\b[^>]+(youtube|vimeo)", a),
    "lists": lambda h, a: c(r"<(ul|ol)\b", a),
    "bold": lambda h, a: c(r"<(strong|b)\b", a),
    "buttons_cta": lambda h, a: c(r'wp-block-button__link|바로가기', a),
    "summary_box": lambda h, a: has(r"요약|핵심 정리|한눈에|3줄", a),
    "text_chars": lambda h, a: len(re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", re.sub(r"<(script|style)\b.*?</\1>", "", a, flags=re.S | re.I)))),
    "external_gov_links": lambda h, a: c(r'href="https?://[^"]*\.(go\.kr|or\.kr)', a),
    "adsense_ins": lambda h, a: c(r'<ins[^>]+class="adsbygoogle', h),
    "adsense_ins_in_article": lambda h, a: c(r'<ins[^>]+class="adsbygoogle', a),
    "adsense_auto": lambda h, a: has(r"pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js", h),
    "other_ad_net": lambda h, a: has(r"mediavine|ezoic|adpushup|taboola|dable|mobon|adfit", h),
    "related_posts": lambda h, a: has(r"관련 글|관련글|함께 보면|같이 보면|추천 글|related", h),
    "popular_widget": lambda h, a: has(r"인기 글|인기글|popular|많이 본", h),
    "author_box": lambda h, a: has(r'author-box|about-author|author-bio|작성자', h),
    "modified_meta": lambda h, a: has(r'article:modified_time|dateModified', h),
    "visible_updated": lambda h, a: has(r"수정일|업데이트|Updated|최종 수정", a),
    "comments": lambda h, a: has(r'id="comments"|comment-form|id="respond"', h),
    "share_buttons": lambda h, a: has(r"sharer|공유하기|share-button|kakao\.share", h),
    "scripts": lambda h, a: c(r"<script\b", h),
    "html_kb": lambda h, a: len(h) // 1024,
    "lazy_img": lambda h, a: has(r'loading="lazy"', a),
}
SITE_FEATURES = {
    "site:naver_verify": lambda h: has(r'name="naver-site-verification"', h),
    "site:bing_verify": lambda h: has(r'name="msvalidate\.01"', h),
    "site:google_verify": lambda h: has(r'name="google-site-verification"', h),
    "site:rss_link": lambda h: has(r'type="application/rss\+xml"', h),
    "site:search_form": lambda h: has(r'role="search"|type="search"', h),
    "site:category_menu": lambda h: has(r"/category/", h),
    "site:pwa_manifest": lambda h: has(r'rel="manifest"', h),
    "site:push": lambda h: has(r"onesignal|webpushr|pushalert|firebase-messaging", h),
}
NOT_LOSS = {"scripts", "html_kb", "site:home_sec", "post_sec", "title_len"}


def run(site, n_posts):
    out = {}
    home, t_home, _ = get(site + "/")
    out["site:home_sec"] = round(t_home, 2)
    out["site:theme"] = (re.search(r"/wp-content/themes/([\w-]+)/", home) or [None, "?"])[1]
    out["site:plugins"] = sorted(set(re.findall(r"/wp-content/plugins/([\w-]+)/", home)))
    for k, f in SITE_FEATURES.items():
        out[k] = f(home)
    try:
        out["site:ads_txt"] = 1 if get(site + "/ads.txt")[2] == 200 else 0
    except Exception:
        out["site:ads_txt"] = 0
    req = urllib.request.Request(f"{site}/wp-json/wp/v2/posts?per_page={n_posts}&_fields=link", headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        links = [p["link"] for p in json.load(r)]
    host = re.escape(re.sub(r"^https?://", "", site))
    rows = []
    for link in links:
        h, t, _ = get(link)
        a = body(h)
        row = {k: f(h, a) for k, f in POST_FEATURES.items()}
        row["internal_links"] = len(set(re.findall(r'href="https?://(?:www\.)?' + host + r'/[^"#?]+', a)))
        row["post_sec"] = round(t, 2)
        rows.append(row)
    for k in rows[0]:
        out[k] = round(sum(r[k] for r in rows) / len(rows), 2)
    out["_posts"] = links
    return out


def main():
    n = int(sys.argv[sys.argv.index("--posts") + 1]) if "--posts" in sys.argv else 3
    data = {}
    for s in [US] + BENCH:
        try:
            data[s] = run(s, n)
        except Exception as e:  # one blocked site must not stop the run
            print(f"ERR {s} {type(e).__name__}: {e}", file=sys.stderr)
    if "--json" in sys.argv:
        json.dump(data, open(sys.argv[sys.argv.index("--json") + 1], "w"), ensure_ascii=False, indent=1)
    names = [s for s in BENCH if s in data]
    bench, us = [data[s] for s in names], data[US]
    keys = [k for k in us if not k.startswith("_") and k not in ("site:theme", "site:plugins")]
    print("feature\tus\tmedian\thave\t" + "\t".join(s[8:].split(".")[0] for s in names))
    loss = []
    for k in keys:
        vals = [b.get(k, 0) for b in bench]
        med, have = median(vals), sum(1 for v in vals if v)
        print(f"{k}\t{us[k]}\t{med}\t{have}/{len(vals)}\t" + "\t".join(str(v) for v in vals))
        if k in NOT_LOSS:
            continue
        if not us[k] and have * 2 > len(vals):
            loss.append((have / len(vals), k, f"우리 없음, {have}/{len(vals)} 보유"))
        elif us[k] and med and us[k] < med * 0.5:
            loss.append((1 - us[k] / med, k, f"우리 {us[k]} vs 중앙값 {med}"))
    print("\n# themes / plugins")
    for s in [US] + names:
        print(f"{s[8:]}\t{data[s]['site:theme']}\t{','.join(data[s]['site:plugins'])}")
    print("\n# LOSS (gap-sorted)")
    for g, k, why in sorted(loss, reverse=True):
        print(f"{g:.2f}\t{k}\t{why}")


if __name__ == "__main__":
    main()
