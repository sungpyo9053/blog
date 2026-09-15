import json
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_refused")


def collect(fetch):
    per_page, page, expected, ids = 3, 1, None, set()
    while True:
        total, pages, rows = fetch(page, per_page)
        if total < 0 or pages != (total + per_page - 1) // per_page or pages > 100:
            raise ValueError("invalid_totals_or_page_limit")
        if expected is None:
            expected = (total, pages)
        if expected != (total, pages):
            raise ValueError("inventory_changed")
        if not isinstance(rows, list) or len(rows) != min(per_page, max(0, total - (page - 1) * per_page)):
            raise ValueError("page_count_mismatch")
        for row in rows:
            post_id = row.get("id") if isinstance(row, dict) else None
            if type(post_id) is not int or post_id <= 0 or post_id in ids:
                raise ValueError("invalid_or_duplicate_id")
            ids.add(post_id)
        print(f"page={page} rows={len(rows)} total={total} pages={pages}")
        if page >= pages:
            break
        page += 1
    if len(ids) != expected[0]:
        raise ValueError("total_mismatch")
    return {"passed": True, "unique_ids": len(ids), "pages_requested": page}


def public_page(page, per_page):
    query = urlencode({"rest_route": "/wp/v2/posts", "status": "publish",
                       "per_page": per_page, "page": page,
                       "orderby": "id", "order": "asc", "_fields": "id"})
    request = Request("https://huntlab.app/?" + query,
                      headers={"User-Agent": "HuntLab-Reader-Check/1.0", "Cache-Control": "no-cache"})
    with build_opener(NoRedirect()).open(request, timeout=20) as response:
        if response.status != 200 or response.headers.get_content_type() != "application/json":
            raise ValueError("unexpected_response")
        raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("response_too_large")
        return (int(response.headers["X-WP-Total"]),
                int(response.headers["X-WP-TotalPages"]), json.loads(raw))


if __name__ == "__main__":
    print(json.dumps(collect(public_page)))
