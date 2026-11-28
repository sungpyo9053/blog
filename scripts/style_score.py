#!/usr/bin/env python3
"""Score a KO post's style against the 11/28 Naver top-blogger reference (research/naver-style-by-topic.md §3-1).

usage: .venv/bin/python -m scripts.style_score [--min N] A|B|C|D|EN post.html [...]
--min N: exit 1 if any file scores below N (default: no threshold, always exit 0).
A 요금 비교, B 생활 계산기, C 지원금, D 금융·세금. Tone (20 pts) is the court's optional experiment, reported apart.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scripts.audit_content_repetition import StructureParser, faq_count, template_flags

# Reference tone per topic from §3-1 (share of sentences): A 합니다 95%, B 해요 83%, C 합니다 81%, D 합니다 80%.
REF_TONE = {"A": "hapnida", "B": "haeyo", "C": "hapnida", "D": "hapnida"}
# 11/29 QA fixes (research/qa-style-baseline.md §4-1·4-2, huntlab-ops/qa1128/proposed_fixes_check.py).
STOP_END = ("단가", "하나", "개요", "필요", "중요")  # end like 가/나/요 but are nouns
Q_TAIL = re.compile(r"\s*\([^()]*\)$")  # '…일까요? (계산기)'
SENT_SPLIT = re.compile(r"(?<!\d\.)(?<=[.?!])\s+")  # don't split '2026.1.1. 기준'


def _question(h: str) -> bool:
    h = Q_TAIL.sub("", h).strip()
    if h.endswith("?"):
        return True
    if h.endswith(STOP_END):
        return False
    if re.search(r"(나|까|는지|인지|[나까가죠]요)$", h):
        return True
    # bare '가' only after 받침 ㄴ (인가·다른가·비싼가), not 수가·단가·정가; bare '지' never (가지·급지·해지)
    return h.endswith("가") and len(h) > 1 and "가" <= h[-2] <= "힣" and (ord(h[-2]) - 0xAC00) % 28 == 4


def is_question(heading: str) -> bool:
    """Question heading; with a colon, either side may carry the question ('…보나: KRX 원/g')."""
    return any(_question(part) for part in heading.split(":", 1))


def sentences(paragraphs: list[str]) -> list[str]:
    return [s.strip() for p in paragraphs for s in SENT_SPLIT.split(p) if len(s.strip()) > 5]


def tone(sentence: str) -> str:
    s = re.sub(r"\s*\([^()]*\)\s*\.?$", "", sentence.strip())  # '…셈입니다(중간값 재료면 457,700원).'
    s = s.rstrip(".?!\"'”’ )")
    if s.endswith("니다"):
        return "hapnida"
    if s.endswith(STOP_END):
        return "other"
    if s.endswith(("요", "죠")):
        return "haeyo"
    return "haera" if s.endswith(("다", "자")) else "other"  # '확인하자' is 해라체


EN_FIXED = {"Short answer", "FAQ", "Reproduce it"}
EN_CAPTION = "At a glance: the main measured table from this article."


def score_en(rendered: str) -> dict:
    """EN guide v1 (research/en-style-analysis.md §3-4)."""
    parser = StructureParser()
    parser.feed(re.sub(r"<script\b.*?</script>", "", rendered, flags=re.S))
    text = " ".join(parser.paragraphs)
    sents = [s for s in re.split(r"(?<=[.?!])\s+", text) if len(s.split()) > 3]
    faq = faq_count(rendered)
    flags = [f"fixed_heading:{h}" for h in parser.headings if h in EN_FIXED]
    # "Short answer:" often follows a <pre> error dump and one intro paragraph (QA §4-4-1)
    flags += ["opener"] if any(p.startswith("Short answer") for p in parser.paragraphs[:3]) else []
    flags += [f"faq_block:{faq}"] if faq >= 5 else []  # en-style-v1: FAQ 0-4
    flags += ["shared_caption"] if EN_CAPTION in rendered else []
    flags += ["broken_alt"] if re.search(r'alt="["\']', rendered) else []
    heads = parser.headings
    words = sum(len(s.split()) for s in sents) / len(sents) if sents else 0
    parts = {
        "rules": _rules(flags, per_flag=6),
        "symptom_headings": round(20 * sum(h not in EN_FIXED for h in heads) / len(heads)) if heads else 0,
        "faq": 0 if faq >= 5 else 10,
        "sentence_len": 10 if 15 <= words <= 22 else max(0, round(10 - abs(words - 18.5))),
        "limits_stated": 20 if re.search(r"didn't (test|measure|find)|Not tested|Limits of", text + " " + " ".join(heads)) else 0,
    }
    return {"total": sum(parts.values()), "without_tone": sum(parts.values()), "parts": parts,
            "flags": flags, "avg_len": round(words, 1), "faq": faq}


def _rules(flags: list[str], per_flag: int) -> int:
    """FAQ is scored in its own part (no double penalty); per_flag sized so only all kinds hit 0 (QA §4-5)."""
    return max(0, 40 - per_flag * sum(not f.startswith("faq_block") for f in flags))


def score(topic: str, rendered: str) -> dict:
    if topic == "EN":
        return score_en(rendered)
    parser = StructureParser()
    parser.feed(re.sub(r"<script\b.*?</script>", "", rendered, flags=re.S))
    sents = sentences(parser.paragraphs)
    flags = template_flags(rendered)
    heads = parser.headings
    q_ratio = sum(map(is_question, heads)) / len(heads) if heads else 0
    faq = faq_count(rendered)
    avg = sum(map(len, sents)) / len(sents) if sents else 0
    tone_share = sum(tone(s) == REF_TONE[topic] for s in sents) / len(sents) if sents else 0
    parts = {
        "rules": _rules(flags, per_flag=5),  # 8 non-FAQ kinds: 5 fixed headings, opener, checked_box, closer
        "question_headings": round(20 * q_ratio),
        "faq": 0 if faq >= 6 else 10,
        "sentence_len": 10 if 40 <= avg <= 55 else max(0, round(10 - abs(avg - 47.5) / 2)),
        "tone_experiment": round(20 * tone_share),
    }
    return {"total": sum(parts.values()), "without_tone": sum(parts.values()) - parts["tone_experiment"],
            "parts": parts, "flags": flags, "avg_len": round(avg, 1), "faq": faq}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=None)
    ap.add_argument("topic", choices=[*REF_TONE, "EN"])
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    low = 0
    for f in args.files:
        r = score(args.topic, Path(f).read_text(encoding="utf-8"))
        low += args.min is not None and r["total"] < args.min
        extra = "" if args.topic == "EN" else f" (말투 제외 {r['without_tone']:2d}/80)"
        print(f"{r['total']:3d}/100{extra} {f} {r['parts']} avg={r['avg_len']} faq={r['faq']}")
    return 1 if low else 0


if __name__ == "__main__":
    assert tone("줄어든다.") == "haera" and tone("받습니다.") == "hapnida" and tone("받아요.") == "haeyo"
    raise SystemExit(main(sys.argv[1:]))
