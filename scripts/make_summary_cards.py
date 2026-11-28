#!/usr/bin/env python3
"""Per-section summary cards for KO posts (11/28 style rule 5: own numbers only, alt/caption per card).

cards.json: [{"id": "1916-criteria", "post": 1916, "after": "<h2 id>", "heading": "...",
              "table": "<table>...</table>", "alt": "...", "cap": "..."}]
  check (local):  .venv/bin/python -m scripts.make_summary_cards check post.html cards.json
  render (runner): PYTHONPATH=. .venv/bin/python scripts/make_summary_cards.py render cards.json OUTDIR > media.json
  ops (local):    .venv/bin/python -m scripts.make_summary_cards ops post.html cards.json media.json OPSDIR
  then on the WP host: wp eval-file /tmp/imp.php <post> OPSDIR (inserts each card right under its H2).
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def text(rendered: str) -> str:
    return re.sub(r"<[^>]+>", " ", re.sub(r"<script\b.*?</script>", "", rendered, flags=re.S))


def missing_numbers(post_html: str, card: dict) -> list[str]:
    """Numbers on the card that do not appear in the post body (must be empty)."""
    body = text(post_html)
    shown = text(card["table"]) + " " + card["heading"] + " " + card["alt"] + " " + card["cap"]
    return [n for n in re.findall(r"\d[\d,.]*\d|\d", shown) if n not in body]


def check(post: str, cards_path: str) -> int:
    src = Path(post).read_text(encoding="utf-8")
    bad = 0
    for c in json.loads(Path(cards_path).read_text(encoding="utf-8")):
        miss = missing_numbers(src, c)
        h2 = len(re.findall(r'<h2[^>]*id="%s"' % re.escape(c["after"]), src))
        ok = not miss and h2 == 1
        bad += not ok
        print(("OK  " if ok else "FAIL"), c["id"], "missing:", miss, "h2:", h2)
    return 1 if bad else 0


def render_upload(cards_path: str, outdir: str) -> int:
    from PIL import Image
    from publisher.wordpress import WordPressClient, WordPressConfig
    from scripts.make_glance_figures import render

    out = Path(outdir)
    out.mkdir(exist_ok=True)
    client = WordPressClient(WordPressConfig.from_environment(Path(".env")))
    res = {}
    for c in json.loads(Path(cards_path).read_text(encoding="utf-8")):
        png = out / f"card-{c['id']}.png"
        render({"heading": c["heading"], "title": c["heading"], "table": c["table"], "lang": "ko"}, png)
        media = client.upload_media(png, alt_text=c["alt"])
        res[c["id"]] = {"url": media["source_url"], "w": list(Image.open(png).size)}
    print(json.dumps(res))
    return 0


def ops(post: str, cards_path: str, media_path: str, opsdir: str) -> int:
    src = Path(post).read_text(encoding="utf-8")
    media = json.loads(Path(media_path).read_text(encoding="utf-8"))
    os.makedirs(opsdir, exist_ok=True)
    plan = []
    for k, c in enumerate(json.loads(Path(cards_path).read_text(encoding="utf-8")), 1):
        anchor = re.search(r'<h2[^>]*id="%s"[^>]*>.*?</h2>' % re.escape(c["after"]), src, re.S).group(0)
        assert src.count(anchor) == 1, anchor
        m = media[c["id"]]
        fig = (f'\n<figure class="wp-block-image hl-card"><img src="{m["url"]}" alt="{html.escape(c["alt"], quote=True)}" '
               f'width="{m["w"][0]}" height="{m["w"][1]}" loading="lazy" decoding="async">'
               f'<figcaption>{html.escape(c["cap"])}</figcaption></figure>')
        Path(opsdir, f"a{k}.txt").write_text(anchor, encoding="utf-8")
        Path(opsdir, f"r{k}.txt").write_text(anchor + fig, encoding="utf-8")
        plan.append({"t": "replace", "a": f"a{k}.txt", "r": f"r{k}.txt"})
    Path(opsdir, "ops.json").write_text(json.dumps(plan), encoding="utf-8")
    print(len(plan), "ops")
    return 0


if __name__ == "__main__":
    assert missing_numbers("<p>상한 220만원</p>", {"table": "<td>220만원</td>", "heading": "", "alt": "", "cap": ""}) == []
    assert missing_numbers("<p>상한 220만원</p>", {"table": "<td>230만원</td>", "heading": "", "alt": "", "cap": ""}) == ["230"]
    cmd, *rest = sys.argv[1:]
    raise SystemExit({"check": check, "render": render_upload, "ops": ops}[cmd](*rest))
