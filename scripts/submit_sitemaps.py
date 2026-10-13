#!/usr/bin/env python3
"""Resubmit sitemaps to Search Console after the daily 10:00 publish.

Replaces one-by-one URL Inspection clicks in the GSC web UI. The Indexing API is
not used: it is only allowed for JobPosting/BroadcastEvent pages.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SITE = "sc-domain:huntlab.app"
SITEMAPS = ["https://huntlab.app/sitemap.xml", "https://huntlab.app/hunt_en-sitemap.xml"]


def main() -> int:
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account
    from scripts.weekly_editorial_metrics import load_env_file

    load_env_file(ROOT / ".env")
    session = AuthorizedSession(service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=["https://www.googleapis.com/auth/webmasters"]))
    failed = 0
    for sitemap in SITEMAPS:
        r = session.put(f"https://searchconsole.googleapis.com/webmasters/v3/sites/{quote(SITE, safe='')}"
                        f"/sitemaps/{quote(sitemap, safe='')}", timeout=30)
        print(sitemap, r.status_code)
        failed += r.status_code != 204
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
