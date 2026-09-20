#!/usr/bin/env python3
"""Snapshot published, draft and scheduled posts using REST GET only."""

from __future__ import annotations

import argparse, hashlib, html, json, re, sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient, WordPressError
from scripts.evidence_topic_miner import atomic_replace, atomic_write_new, redact_text, sanitize_url


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def fetch_status(client: WordPressClient, status: str) -> list[dict]:
    rows, page = [], 1
    while True:
        query = urlencode({"context":"edit", "status":status, "per_page":"100", "page":str(page), "_fields":"id,link,slug,status,title,excerpt,content,date,date_gmt"})
        try:
            batch = client.request("GET", f"posts?{query}", expected=(200,))
        except WordPressError as exc:
            if page > 1 and exc.status_code == 400 and exc.wp_code == "rest_post_invalid_page_number":
                return rows
            raise
        if not isinstance(batch, list):
            raise ValueError("WordPress inventory is not a list")
        rows.extend(batch)
        if len(batch) < 100: return rows
        page += 1


def build_snapshot(client: WordPressClient) -> dict:
    by_status = {status: fetch_status(client, status) for status in ("publish", "draft", "future")}
    posts, seen = [], set()
    for status, rows in by_status.items():
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("content"), dict) or not any(isinstance(row["content"].get(key), str) for key in ("raw", "rendered")):
                raise ValueError("WordPress inventory lacks full content")
            post_id = row.get("id")
            if type(post_id) is not int or post_id <= 0 or post_id in seen or row.get("status") != status:
                raise ValueError("WordPress inventory has inconsistent identities or statuses; refresh snapshot")
            seen.add(post_id)
            content = row["content"].get("raw")
            if not isinstance(content, str):
                content = row["content"]["rendered"]
            posts.append({
                "post_id": int(row["id"]), "url": sanitize_url(str(row.get("link", ""))),
                "slug": redact_text(str(row.get("slug", ""))),
                "title": redact_text(plain(str((row.get("title") or {}).get("rendered", "")))),
                "excerpt": redact_text(plain(str((row.get("excerpt") or {}).get("rendered", "")))[:1000]),
                "content": redact_text(content),
                "status": status,
                "date": row.get("date"),
                "date_gmt": row.get("date_gmt"),
            })
    posts.sort(key=lambda row: row["post_id"])
    return {"metadata":{"complete":True,"full_content":True,"source":"wordpress_rest_context_edit_get_only","collected_at":datetime.now(UTC).isoformat(),"statuses":{k:len(v) for k,v in by_status.items()}},"posts":posts}


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
