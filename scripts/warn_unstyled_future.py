#!/usr/bin/env python3
"""Warning-only style check for posts publishing within the next hour (11/28 retrial verdict: warn first, no hold).

Runs from huntlab-operations-watchdog (every 15 min). Never changes a post; sends one KakaoTalk per post.
Exempt: control posts in editorial/operations/research/ko81-queue.md (role 비교용). EN warns below 80.
usage: .venv/bin/python scripts/warn_unstyled_future.py [--apply]
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_content_repetition import template_flags  # noqa: E402
from scripts.style_score import score_en  # noqa: E402

KO81 = ROOT / "editorial/operations/research/ko81-queue.md"
STATE = ROOT / "output/style-warn"


def exempt_ids(text: str) -> set[int]:
    return {int(i) for i in re.findall(r"^\| \d+ \| (\d+) \|[^|]*\|[^|]*\| 비교용", text, re.M)}


def flags_for(kind: str, raw: str) -> list[str]:
    if kind == "posts":
        return template_flags(raw)
    r = score_en(raw)
    return [] if r["total"] >= 80 else (r["flags"] or [f"score {r['total']}"])


def due_warnings(posts_by_kind: dict, now: datetime, exempt: set[int], warned: set[int]) -> list[tuple[int, list[str]]]:
    out = []
    for kind, posts in posts_by_kind.items():
        for p in posts:
            due = datetime.fromisoformat(p["date_gmt"]).replace(tzinfo=UTC)
            if p["id"] in exempt or p["id"] in warned or not now <= due <= now + timedelta(hours=1):
                continue
            bad = flags_for(kind, p["content"]["raw"])
            if bad:
                out.append((p["id"], bad))
    return out


def main(apply: bool) -> int:
    from publisher.wordpress import WordPressClient, WordPressConfig
    from scripts.send_kakao_report import send

    client = WordPressClient(WordPressConfig.from_environment(ROOT / ".env"))
    fields = "status=future&context=edit&orderby=date&order=asc&per_page=20&_fields=id,date_gmt,content"
    posts = {k: client.request("GET", f"{k}?{fields}", expected=(200,)) for k in ("posts", "hunt_en")}
    STATE.mkdir(parents=True, exist_ok=True)
    warned = {int(p.stem) for p in STATE.glob("*.json")}
    for pid, bad in due_warnings(posts, datetime.now(UTC), exempt_ids(KO81.read_text(encoding="utf-8")), warned):
        msg = f"[스타일 경고] #{pid} 1시간 안 공개, 옛 틀: {' '.join(bad[:3])} (공개는 그대로 진행)"
        print(msg)
        if apply:
            send(msg, os.environ["MCPORTER_BIN"])
            (STATE / f"{pid}.json").write_text(json.dumps({"id": pid, "flags": bad, "warned_at": datetime.now(UTC).isoformat()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--apply" in sys.argv))
