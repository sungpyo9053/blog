#!/usr/bin/env python3
"""Snapshot current publish and draft post search intent using REST GET only."""

from __future__ import annotations

import argparse, hashlib, html, json, re, sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient
from scripts.evidence_topic_miner import atomic_replace, atomic_write_new, redact_text, sanitize_url


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def fetch_status(client: WordPressClient, status: str) -> list[dict]:
    rows, page = [], 1
    while True:
        query = urlencode({"context":"edit", "status":status, "per_page":"100", "page":str(page), "_fields":"id,link,slug,status,title,excerpt"})
        batch = client.request("GET", f"posts?{query}", expected=(200,))
        rows.extend(batch)
        if len(batch) < 100: return rows
        page += 1


def build_snapshot(client: WordPressClient) -> dict:
    by_status = {status: fetch_status(client, status) for status in ("publish", "draft")}
    posts = []
    for status, rows in by_status.items():
        for row in rows:
            posts.append({
                "post_id": int(row["id"]), "url": sanitize_url(str(row.get("link", ""))),
                "slug": redact_text(str(row.get("slug", ""))),
                "title": redact_text(plain(str((row.get("title") or {}).get("rendered", "")))),
                "excerpt": redact_text(plain(str((row.get("excerpt") or {}).get("rendered", "")))[:1000]),
                "status": status,
            })
    posts.sort(key=lambda row: row["post_id"])
    return {"metadata":{"complete":True,"source":"wordpress_rest_context_edit_get_only","collected_at":datetime.now(UTC).isoformat(),"statuses":{k:len(v) for k,v in by_status.items()}},"posts":posts}


def main() -> int:
    root = ROOT; parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file",type=Path,default=root/".env"); parser.add_argument("--output",type=Path,default=root/"output/topic-miner/inventory-latest.json"); args=parser.parse_args()
    data=(json.dumps(build_snapshot(WordPressClient(WordPressConfig.from_environment(args.env_file))),ensure_ascii=False,indent=2)+"\n").encode()
    stamp=datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    archive=args.output.parent/"inventory"/f"{stamp}.json"
    atomic_write_new(archive,data)
    atomic_replace(args.output,data)
    print(f"status=OK output={args.output} archive={archive} sha256={hashlib.sha256(data).hexdigest()}"); return 0


if __name__ == "__main__": raise SystemExit(main())
