#!/usr/bin/env python3
"""Featured-image info cards (1600x900) for life posts that have no image.

Guide (guides/image-guide.md): Economy/Society featured image = neutral public-info graphic.
The card only restates the post's own title (no new numbers), split at ':' into headline/subline.

usage (runner): .venv/bin/python scripts/make_info_cards.py cards.json OUTDIR [--apply]
cards.json: [{"post_id": 1066, "title": "...", "label": "보험·고용"}]
--apply uploads each PNG and sets it as featured_media (only if the post still has none).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

W, H = 1600, 900
BG, INK, SUB, ACCENT = "#F6F1E7", "#2B2622", "#6B625A", "#B5583A"
FONT_DIR = Path("/usr/share/fonts/opentype/noto")


def font(weight, size):
    path = FONT_DIR / f"NotoSansCJK-{weight}.ttc"
    for i in range(10):  # pick the KR face inside the collection
        f = ImageFont.truetype(str(path), size, index=i)
        if "KR" in f.getname()[0]:
            return f
    return ImageFont.truetype(str(path), size)


def wrap(draw, text, f, width):
    lines, cur = [], ""
    for word in text.split(" "):
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=f) <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def render(title, label, out):
    head, _, sub = title.partition(":")
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 24, H], fill=ACCENT)
    x, maxw = 150, W - 300  # keep text inside the central ~80% safe area
    d.text((x, 150), label, font=font("Bold", 40), fill=ACCENT)
    y = 230
    hf = font("Bold", 96)
    for line in wrap(d, head.strip(), hf, maxw)[:3]:
        d.text((x, y), line, font=hf, fill=INK)
        y += 124
    y += 30
    sf = font("Regular", 46)
    for line in wrap(d, sub.strip(), sf, maxw)[:3]:
        d.text((x, y), line, font=sf, fill=SUB)
        y += 66
    d.text((x, H - 120), "huntlab.app · 공식 출처 기준", font=font("Regular", 34), fill=SUB)
    img.save(out)


def main():
    cards = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    client = None
    if "--apply" in sys.argv:
        from publisher.wordpress import WordPressClient, WordPressConfig
        client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    for c in cards:
        out = outdir / f"card-{c['post_id']}.png"
        render(c["title"], c["label"], out)
        if not client:
            print("rendered", out)
            continue
        post = client.request("GET", f"posts/{c['post_id']}?context=edit", expected=(200,))
        if post.get("featured_media"):
            print("skip has-image", c["post_id"])
            continue
        media = client.upload_media(out, alt_text=c["title"].partition(":")[0].strip())
        client.request("POST", f"posts/{c['post_id']}", payload={"featured_media": media["id"]}, expected=(200,))
        print("set", c["post_id"], media["id"], media.get("source_url"))


if __name__ == "__main__":
    main()
