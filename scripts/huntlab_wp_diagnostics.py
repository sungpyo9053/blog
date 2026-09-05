#!/usr/bin/env python3
"""Offline diagnostics for WordPress publishing response and indexability contracts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree


@dataclass(frozen=True)
class CheckResult:
    check: str
    passed: bool
    reason: str
    observed: dict[str, Any]


def status_only_accepts(status: int) -> bool:
    """Deliberately weak baseline retained to make the failure reproducible."""
    return 200 <= status < 300


def validate_rest_response(*, status: int, content_type: str, body: bytes, expected_id: int | None = None) -> CheckResult:
    media_type = content_type.split(";", 1)[0].strip().casefold()
    observed: dict[str, Any] = {"status": status, "content_type": media_type, "body_bytes": len(body)}
    if not status_only_accepts(status):
        return CheckResult("rest_response", False, "unexpected_http_status", observed)
    if media_type != "application/json":
        return CheckResult("rest_response", False, "unexpected_content_type", observed)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return CheckResult("rest_response", False, "invalid_json_body", observed)
    if not isinstance(payload, dict) or not isinstance(payload.get("id"), int):
        return CheckResult("rest_response", False, "missing_post_id", observed)
    observed["post_id"] = payload["id"]
    if expected_id is not None and payload["id"] != expected_id:
        return CheckResult("rest_response", False, "post_id_mismatch", observed)
    return CheckResult("rest_response", True, "validated_json_post_identity", observed)


def _sitemap_urls(xml: bytes) -> set[str]:
    root = ElementTree.fromstring(xml)
    return {node.text.strip() for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "loc" and node.text}


def audit_indexability(*, pages: list[dict[str, Any]], sitemap_xml: bytes) -> CheckResult:
    sitemap = _sitemap_urls(sitemap_xml)
    conflicts: list[dict[str, str]] = []
    checked = 0
    for page in pages:
        url = str(page.get("url", "")).strip()
        if urlsplit(url).scheme not in {"http", "https"}:
            continue
        checked += 1
        robots = {str(value).casefold() for value in page.get("robots", [])}
        canonical = str(page.get("canonical", "")).strip()
        if "noindex" in robots and url in sitemap:
            conflicts.append({"url": url, "reason": "noindex_url_in_sitemap"})
        if "noindex" not in robots and canonical and canonical != url:
            conflicts.append({"url": url, "reason": "indexable_url_not_self_canonical"})
    observed = {"checked_pages": checked, "sitemap_urls": len(sitemap), "conflicts": conflicts}
    return CheckResult("indexability", not conflicts, "consistent" if not conflicts else "indexability_conflict", observed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    rest = sub.add_parser("rest-response")
    rest.add_argument("--status", type=int, required=True)
    rest.add_argument("--content-type", required=True)
    rest.add_argument("--body", type=Path, required=True)
    rest.add_argument("--expected-id", type=int)
    index = sub.add_parser("indexability")
    index.add_argument("--pages", type=Path, required=True)
    index.add_argument("--sitemap", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "rest-response":
        result = validate_rest_response(status=args.status, content_type=args.content_type, body=args.body.read_bytes(), expected_id=args.expected_id)
    else:
        pages = json.loads(args.pages.read_text(encoding="utf-8"))
        result = audit_indexability(pages=pages, sitemap_xml=args.sitemap.read_bytes())
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
