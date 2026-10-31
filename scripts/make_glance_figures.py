# EN "at a glance" figure: glance_export.php (WP host, wp eval-file) -> tables.json -> this (runner, --apply uploads) -> media.json -> glance_insert.php (WP host, reads /tmp/enfig_media.json) -> wp cache-enabler clear --ids=...
# Draws the post's own biggest table as a 1600px PNG (no new numbers); same palette as make_info_cards.
import html, json, re, sys
from pathlib import Path
sys.path.insert(0, ".")
from PIL import Image, ImageDraw
from scripts.make_info_cards import font, BG, INK, SUB, ACCENT
W, PAD, MAXROWS = 1600, 70, 10
def cells(row): return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)]
def wrap(d, t, f, w):
    out, cur = [], ""
    for word in t.split(" "):
        while d.textlength(word, font=f) > w and len(word) > 1:  # hard-break long tokens (paths, flags)
            k = len(word)
            while k > 1 and d.textlength(word[:k], font=f) > w: k -= 1
            if cur: out.append(cur); cur = ""
            out.append(word[:k]); word = word[k:]
        test = (cur + " " + word).strip()
        if d.textlength(test, font=f) <= w: cur = test
        else: out.append(cur); cur = word
    return out + [cur] if cur else out
def render(item, out):
    rows = [cells(r) for r in re.findall(r"<tr.*?</tr>", item["table"], re.S)]
    rows = [r for r in rows if r]
    head, body = rows[0], rows[1:]
    more = len(body) - MAXROWS
    body = body[:MAXROWS]
    ncol = len(head)
    body = [(r + [""] * ncol)[:ncol] for r in body]
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    hf, bf, tf = font("Bold", 28), font("Regular", 27), font("Bold", 40)
    inner = W - 2 * PAD
    weight = [max(10, min(40, max(len(r[i]) for r in [head] + body))) for i in range(ncol)]
    colw = [inner * w / sum(weight) for w in weight]
    title = item["heading"] if not re.match(r"(?i)what i ran|setup|environment", item["heading"]) else item["title"]
    tl = wrap(tmp, title, tf, inner)[:2]
    def lay(r, f): return [wrap(tmp, c, f, cw - 24)[:4] for c, cw in zip(r, colw)]
    L = [lay(head, hf)] + [lay(r, bf) for r in body]
    rh = [max(1, *(len(c) for c in r)) * 38 + 22 for r in L]
    H = PAD + len(tl) * 54 + 30 + sum(rh) + 90 + (40 if more > 0 else 0)
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 16, H], fill=ACCENT)
    y = PAD
    for line in tl: d.text((PAD, y), line, font=tf, fill=INK); y += 54
    y += 30
    for k, r in enumerate(L):
        if k == 0: d.rectangle([PAD, y, W - PAD, y + rh[0]], fill="#EADFCC")
        x = PAD
        for c, cw in zip(r, colw):
            yy = y + 11
            for line in c: d.text((x + 12, yy), line, font=hf if k == 0 else bf, fill=INK if k == 0 else SUB if False else INK); yy += 38
            x += cw
        y += rh[k]
        d.line([PAD, y, W - PAD, y], fill="#D8CDB9", width=2)
    if more > 0: d.text((PAD, y + 10), f"+{more} more rows in the article", font=bf, fill=SUB); y += 40
    d.text((PAD, H - 60), "huntlab.app · measured results from this article", font=font("Regular", 26), fill=SUB)
    img.save(out)
    return title
if __name__ == "__main__":
    items = json.load(open(sys.argv[1])); outdir = Path(sys.argv[2]); outdir.mkdir(exist_ok=True)
    only = [int(a) for a in sys.argv[3:] if a.isdigit()]
    client = None
    if "--apply" in sys.argv:
        from publisher.wordpress import WordPressClient, WordPressConfig
        client = WordPressClient(WordPressConfig.from_environment(Path(".env")))
    res = {}
    for it in items:
        if only and it["id"] not in only: continue
        out = outdir / f"glance-{it['id']}.png"; t = render(it, out)
        alt = f"{t} — measured results table"
        if client:
            m = client.upload_media(out, alt_text=alt); res[it["id"]] = {"url": m["source_url"], "alt": alt, "w": Image.open(out).size}
        else: print("rendered", out, Image.open(out).size)
    if client: print(json.dumps(res))
