#!/usr/bin/env python3
"""Score a KO post's style against the 11/28 Naver top-blogger reference (research/naver-style-by-topic.md §3-1).

usage: .venv/bin/python -m scripts.style_score A|B|C|D|EN post.html [...]
A 요금 비교, B 생활 계산기, C 지원금, D 금융·세금. Tone (20 pts) is the court's optional experiment, reported apart.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from scripts.audit_content_repetition import StructureParser, template_flags

# Reference tone per topic from §3-1 (share of sentences): A 합니다 95%, B 해요 83%, C 합니다 81%, D 합니다 80%.
REF_TONE = {"A": "hapnida", "B": "haeyo", "C": "hapnida", "D": "hapnida"}
QUESTION_END = re.compile(r"(\?|나|까|가|지|요|할까|될까|는지)$")


def sentences(paragraphs: list[str]) -> list[str]:
    return [s.strip() for p in paragraphs for s in re.split(r"(?<=[.?!])\s+", p) if len(s.strip()) > 5]


def tone(sentence: str) -> str:
    s = sentence.rstrip(".?!\"' )")
    if s.endswith("니다"):
        return "hapnida"
    if s.endswith(("요", "죠")):
        return "haeyo"
    return "haera" if s.endswith("다") else "other"


EN_FIXED = {"Short answer", "FAQ", "Reproduce it"}
EN_CAPTION = "At a glance: the main measured table from this article."


def score_en(rendered: str) -> dict:
    """EN guide v1 (research/en-style-analysis.md §3-4)."""
    parser = StructureParser()
    parser.feed(re.sub(r"<script\b.*?</script>", "", rendered, flags=re.S))
    text = " ".join(parser.paragraphs)
    sents = [s for s in re.split(r"(?<=[.?!])\s+", text) if len(s.split()) > 3]
    faq = len(re.findall(r'"@type"\s*:\s*"Question"', rendered))
    flags = [f"fixed_heading:{h}" for h in parser.headings if h in EN_FIXED]
    flags += ["opener"] if parser.paragraphs and parser.paragraphs[0].startswith("Short answer") else []
    flags += ["faq_exactly_5"] if faq == 5 else []
    flags += ["shared_caption"] if EN_CAPTION in rendered else []
    flags += ["broken_alt"] if re.search(r'alt="["\']', rendered) else []
    heads = parser.headings
    words = sum(len(s.split()) for s in sents) / len(sents) if sents else 0
    parts = {
        "rules": max(0, 40 - 8 * len(flags)),
        "symptom_headings": round(20 * sum(h not in EN_FIXED for h in heads) / len(heads)) if heads else 0,
        "faq": 0 if faq == 5 else 10,
        "sentence_len": 10 if 15 <= words <= 22 else max(0, round(10 - abs(words - 18.5))),
        "limits_stated": 20 if re.search(r"didn't (test|measure|find)|Not tested|Limits of", text + " " + " ".join(heads)) else 0,
    }
    return {"total": sum(parts.values()), "without_tone": sum(parts.values()), "parts": parts,
            "flags": flags, "avg_len": round(words, 1), "faq": faq}


def score(topic: str, rendered: str) -> dict:
    if topic == "EN":
        return score_en(rendered)
    parser = StructureParser()
    parser.feed(re.sub(r"<script\b.*?</script>", "", rendered, flags=re.S))
    sents = sentences(parser.paragraphs)
    flags = template_flags(rendered)
    heads = parser.headings
    q_ratio = sum(bool(QUESTION_END.search(h)) for h in heads) / len(heads) if heads else 0
    faq = len(re.findall(r'"@type"\s*:\s*"Question"', rendered))
    avg = sum(map(len, sents)) / len(sents) if sents else 0
    tone_share = sum(tone(s) == REF_TONE[topic] for s in sents) / len(sents) if sents else 0
    parts = {
        "rules": max(0, 40 - 8 * len(flags)),
        "question_headings": round(20 * q_ratio),
        "faq": 0 if faq == 7 else 10,
        "sentence_len": 10 if 40 <= avg <= 55 else max(0, round(10 - abs(avg - 47.5) / 2)),
        "tone_experiment": round(20 * tone_share),
    }
    return {"total": sum(parts.values()), "without_tone": sum(parts.values()) - parts["tone_experiment"],
            "parts": parts, "flags": flags, "avg_len": round(avg, 1), "faq": faq}


def main(argv: list[str]) -> int:
    topic, files = argv[0], argv[1:]
    for f in files:
        r = score(topic, Path(f).read_text(encoding="utf-8"))
        extra = "" if topic == "EN" else f" (말투 제외 {r['without_tone']:2d}/80)"
        print(f"{r['total']:3d}/100{extra} {Path(f).name} {r['parts']} avg={r['avg_len']} faq={r['faq']}")
    return 0


if __name__ == "__main__":
    assert tone("줄어든다.") == "haera" and tone("받습니다.") == "hapnida" and tone("받아요.") == "haeyo"
    raise SystemExit(main(sys.argv[1:]))
