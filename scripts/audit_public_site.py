"""Read-only public WordPress quality audit for HuntLab."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

USER_AGENT = "HuntLabPublicAudit/1.0 (+https://huntlab.app/)"
REQUEST_INTERVAL_SECONDS = 0.25
FETCH_ATTEMPTS = 3
FETCH_BACKOFF_SECONDS = 0.75
_FETCH_GATE = threading.Lock()
_NEXT_FETCH_AT = 0.0
GENERIC_AUTHORS = {"admin", "administrator", "user"}
EVIDENCE_TERMS = (
    "검증 환경",
    "테스트 환경",
    "실행 결과",
    "검증 결과",
    "직접 확인",
    "실패",
    "로그",
    "한계",
)
ACTIVE_CATEGORY_SLUGS = {
    "life",
    "economy",
    "real-estate",
    "society",
    "politics",
    "culture-entertainment",
    "it",
}


@dataclass
class FetchResult:
    url: str
    status: int
    content_type: str = ""
    body: bytes = b""
    error: str = ""


@dataclass
class PageFacts:
    url: str
    status: int
    title: str = ""
    canonical: str = ""
    author: str = ""
    published_at: str = ""
    og_image: str = ""
    noindex: bool = False
    featured_alt: str | None = None
    has_quick_summary: bool = False
    quick_summary_fields: dict[str, str] = field(default_factory=dict)
    has_article_toc: bool = False
    evidence_signals: list[str] = field(default_factory=list)
    internal_links: set[str] = field(default_factory=set)


class PageParser(HTMLParser):
    def __init__(self, url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.url = url
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.in_title = False
        self.ignored_depth = 0
        self.canonical = ""
        self.author = ""
        self.published_at = ""
        self.og_image = ""
        self.robots = ""
        self.featured_alt: str | None = None
        self.has_quick_summary = False
        self.has_article_toc = False
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        if "huntlab-article-quick-summary" in classes:
            self.has_quick_summary = True
        if "huntlab-article-toc" in classes:
            self.has_article_toc = True
        if tag in {"script", "style", "noscript"}:
            self.ignored_depth += 1
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key = (values.get("name") or values.get("property") or "").lower()
            content = values.get("content", "").strip()
            if key == "author":
                self.author = content
            elif key == "article:published_time":
                self.published_at = content
            elif key == "og:image":
                self.og_image = content
            elif key == "robots":
                self.robots = content.lower()
        elif tag == "link" and "canonical" in values.get("rel", "").lower():
            self.canonical = urllib.parse.urljoin(self.url, values.get("href", ""))
        elif tag == "a" and values.get("href"):
            self.links.add(urllib.parse.urljoin(self.url, values["href"]))
        elif tag == "img" and "wp-post-image" in values.get("class", "").split():
            self.featured_alt = values.get("alt", "").strip()
        elif (
            tag == "time"
            and "published" in classes
            and values.get("itemprop") == "datePublished"
            and values.get("datetime")
            and not self.published_at
        ):
            self.published_at = values["datetime"].strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag in {"script", "style", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if not self.ignored_depth and data.strip():
            self.text_parts.append(data.strip())


def _wait_for_request_slot(interval: float = REQUEST_INTERVAL_SECONDS) -> None:
    """Serialize audit starts so a full crawl does not trip the public CDN."""
    global _NEXT_FETCH_AT
    with _FETCH_GATE:
        now = time.monotonic()
        if _NEXT_FETCH_AT > now:
            time.sleep(_NEXT_FETCH_AT - now)
        _NEXT_FETCH_AT = time.monotonic() + max(interval, 0.0)


def fetch(
    url: str,
    *,
    timeout: float = 6.0,
    method: str = "GET",
    attempts: int = FETCH_ATTEMPTS,
    request_interval: float = REQUEST_INTERVAL_SECONDS,
) -> FetchResult:
    marker = b"\n__HUNTLAB_AUDIT_META__"
    last_error = ""
    last_result: FetchResult | None = None
    for attempt in range(max(attempts, 1)):
        _wait_for_request_slot(request_interval)
        try:
            completed = subprocess.run(
                [
                    "curl",
                    "-sS",
                    "-L",
                    "-X",
                    method,
                    "--max-time",
                    str(timeout),
                    "-A",
                    USER_AGENT,
                    "-w",
                    "\n__HUNTLAB_AUDIT_META__%{http_code}\t%{content_type}\t%{url_effective}",
                    url,
                ],
                check=False,
                capture_output=True,
            )
            body, separator, metadata = completed.stdout.rpartition(marker)
            if not separator:
                last_error = "CurlMetadataError"
                if attempt + 1 < max(attempts, 1):
                    time.sleep(FETCH_BACKOFF_SECONDS * (2 ** attempt))
                continue
            status_text, content_type, effective_url = metadata.decode("utf-8", errors="replace").split("\t", 2)
            status = int(status_text)
            result = FetchResult(
                url=effective_url,
                status=status,
                content_type=content_type,
                body=body if method == "GET" else b"",
                error="" if completed.returncode == 0 and status < 400 else "CurlHTTPError",
            )
            last_result = result
            retryable = status in {0, 403, 408, 425, 429} or status >= 500
            if not retryable or attempt + 1 >= max(attempts, 1):
                return result
        except (OSError, ValueError) as exc:
            last_error = type(exc).__name__
        if attempt + 1 < max(attempts, 1):
            time.sleep(FETCH_BACKOFF_SECONDS * (2 ** attempt))
    return last_result or FetchResult(url=url, status=0, error=last_error)


def sitemap_urls(xml_body: bytes) -> list[str]:
    root = ET.fromstring(xml_body)
    urls: list[str] = []
    for entry in list(root):
        if entry.tag.rsplit("}", 1)[-1] not in {"url", "sitemap"}:
            continue
        for node in list(entry):
            if node.tag.rsplit("}", 1)[-1] == "loc" and (node.text or "").strip():
                urls.append((node.text or "").strip())
                break
    return urls


def normalize_internal_link(url: str, base_url: str) -> str | None:
    parsed = urllib.parse.urlsplit(url)
    base = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != base.netloc:
        return None
    if parsed.path.startswith(("/wp-admin/", "/wp-json/", "/cdn-cgi/")):
        return None
    if parsed.path.endswith(("/feed/", ".jpg", ".jpeg", ".png", ".webp", ".svg", ".css", ".js")):
        return None
    clean = urllib.parse.urlunsplit((base.scheme, base.netloc, parsed.path or "/", parsed.query, ""))
    return clean


def inspect_page(result: FetchResult, base_url: str) -> PageFacts:
    facts = PageFacts(url=result.url, status=result.status)
    if result.status != 200 or "html" not in result.content_type.lower():
        return facts
    document = result.body.decode("utf-8", errors="replace")
    parser = PageParser(result.url)
    parser.feed(document)
    visible_text = " ".join(parser.text_parts)
    facts.title = " ".join(parser.title_parts).strip()
    facts.canonical = parser.canonical
    facts.author = parser.author
    facts.published_at = parser.published_at
    facts.og_image = parser.og_image
    facts.noindex = "noindex" in parser.robots
    facts.featured_alt = parser.featured_alt
    facts.has_quick_summary = parser.has_quick_summary
    summary_match = re.search(
        r'<section\b[^>]*class=["\'][^"\']*huntlab-article-quick-summary[^"\']*["\'][^>]*>(.*?)</section>',
        document,
        re.IGNORECASE | re.DOTALL,
    )
    # Published articles may contain the same grounded summary as a normal
    # Markdown ``## 20초 핵심 요약`` heading rather than the optional plugin
    # wrapper. Treat that canonical article structure as a real summary too;
    # otherwise the audit reports a false omission for valid posts.
    if summary_match is None:
        summary_match = re.search(
            r'<h2\b[^>]*>\s*20초\s*핵심\s*요약\s*</h2>\s*'
            r'<ul\b[^>]*>(.*?)</ul>',
            document,
            re.IGNORECASE | re.DOTALL,
        )
    if summary_match:
        facts.has_quick_summary = True
        block = summary_match.group(1)
        for label in ("무엇", "왜", "어떻게"):
            value_match = re.search(
                rf'<li\b[^>]*>\s*<strong\b[^>]*>\s*{label}\s*:?' 
                rf'\s*</strong>(.*?)</li>',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            value = re.sub(r"<[^>]+>", " ", value_match.group(1)) if value_match else ""
            facts.quick_summary_fields[label] = " ".join(html.unescape(value).split())
    facts.has_article_toc = parser.has_article_toc
    facts.evidence_signals = [term for term in EVIDENCE_TERMS if term in visible_text]
    facts.internal_links = {
        normalized
        for link in parser.links
        if (normalized := normalize_internal_link(link, base_url)) is not None
    }
    return facts


def _parallel_fetch(urls: Iterable[str], timeout: float, *, method: str = "GET") -> list[FetchResult]:
    ordered_urls = list(dict.fromkeys(urls))
    results: dict[str, FetchResult] = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(fetch, url, timeout=timeout, method=method): url for url in ordered_urls}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return [results[url] for url in ordered_urls]


def audit_site(base_url: str, *, timeout: float = 6.0) -> dict:
    base_url = base_url.rstrip("/") + "/"
    endpoints = {
        name: fetch(urllib.parse.urljoin(base_url, path), timeout=timeout)
        for name, path in (("robots", "robots.txt"), ("sitemap", "sitemap.xml"), ("ads_txt", "ads.txt"))
    }
    sitemap_result = endpoints["sitemap"]
    child_sitemaps = sitemap_urls(sitemap_result.body) if sitemap_result.status == 200 else []
    child_results = _parallel_fetch(child_sitemaps, timeout)
    urls_by_kind: dict[str, list[str]] = {"post": [], "page": [], "category": []}
    for result in child_results:
        if result.status != 200:
            continue
        name = urllib.parse.urlsplit(result.url).path.rsplit("/", 1)[-1]
        kind = next((key for key in urls_by_kind if name.startswith(f"{key}-")), "")
        if kind:
            urls_by_kind[kind].extend(sitemap_urls(result.body))

    content_urls = urls_by_kind["post"] + urls_by_kind["page"] + urls_by_kind["category"] + [base_url]
    page_results = _parallel_fetch(content_urls, timeout)
    pages = [inspect_page(result, base_url) for result in page_results]
    known_urls = {page.url for page in pages}
    linked_urls = set().union(*(page.internal_links for page in pages)) if pages else set()
    links_to_check = sorted(linked_urls - known_urls)[:20]
    link_results = _parallel_fetch(links_to_check, min(timeout, 3.0), method="HEAD")
    checked_results = page_results + link_results
    broken_links = [
        {"url": result.url, "status": result.status, "error": result.error}
        for result in checked_results
        if result.status >= 400
    ]
    unverified_urls = [
        {"url": result.url, "error": result.error}
        for result in checked_results
        if result.status == 0
    ]

    categories_url = urllib.parse.urljoin(base_url, "wp-json/wp/v2/categories?per_page=100&hide_empty=false")
    categories_result = fetch(categories_url, timeout=timeout)
    categories: list[dict] = []
    if categories_result.status == 200:
        try:
            categories = json.loads(categories_result.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            categories = []

    complete = (
        sitemap_result.status == 200
        and bool(child_sitemaps)
        and all(result.status == 200 for result in child_results)
        and not unverified_urls
    )
    return {
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "base_url": base_url,
        "endpoints": {
            name: {"status": result.status, "content_type": result.content_type, "error": result.error}
            for name, result in endpoints.items()
        },
        "counts": {kind: len(urls) for kind, urls in urls_by_kind.items()},
        "child_sitemaps": [
            {"url": result.url, "status": result.status, "error": result.error}
            for result in child_results
        ],
        "empty_categories": sorted(
            category.get("name", "")
            for category in categories
            if category.get("count") == 0
            and (
                not category.get("slug")
                or category.get("slug") in ACTIVE_CATEGORY_SLUGS
            )
        ),
        "legacy_empty_categories": sorted(
            category.get("name", "")
            for category in categories
            if category.get("count") == 0
            and category.get("slug")
            and category.get("slug") not in ACTIVE_CATEGORY_SLUGS
        ),
        "broken_internal_links": broken_links,
        "unverified_urls": unverified_urls,
        "pages": [facts.__dict__ | {"internal_links": sorted(facts.internal_links)} for facts in pages],
    }


def render_markdown(audit: dict, *, heading_level: int = 1) -> str:
    pages = audit["pages"]
    posts = pages[: audit["counts"]["post"]]
    verified_posts = [page for page in posts if page["status"] == 200]
    verified_pages = [page for page in pages if page["status"] == 200]
    generic_authors = [page for page in verified_posts if page["author"].strip().lower() in GENERIC_AUTHORS]
    missing_featured = [page for page in verified_posts if not page["og_image"] or page["featured_alt"] in {None, ""}]
    missing_canonical = [page for page in verified_pages if not page["canonical"]]
    missing_quick_summary = [page for page in verified_posts if not page.get("has_quick_summary", False)]
    incomplete_quick_summary = [
        page
        for page in verified_posts
        if page.get("has_quick_summary", False)
        and any(not page.get("quick_summary_fields", {}).get(label, "").strip() for label in ("무엇", "왜", "어떻게"))
    ]
    missing_article_toc = [page for page in verified_posts if not page.get("has_article_toc", False)]
    evidence_review = sorted(verified_posts, key=lambda page: (len(page["evidence_signals"]), page["url"]))[:10]
    endpoint_rows = audit["endpoints"]
    heading = "#" * heading_level
    subheading = "#" * (heading_level + 1)
    detail_heading = "#" * (heading_level + 2)
    lines = [
        f"{heading} Public Site Quality Audit",
        "",
        f"- status: `{audit.get('status', 'INCOMPLETE')}`",
        f"- base_url: `{audit['base_url']}`",
        f"- posts: `{audit['counts']['post']}`",
        f"- pages: `{audit['counts']['page']}`",
        f"- categories_in_sitemap: `{audit['counts']['category']}`",
        f"- broken_internal_links: `{len(audit['broken_internal_links'])}`",
        f"- unverified_urls: `{len(audit['unverified_urls'])}`",
        f"- empty_categories: `{len(audit['empty_categories'])}`",
        f"- legacy_empty_categories: `{len(audit.get('legacy_empty_categories', []))}`",
        f"- generic_author_posts: `{len(generic_authors)}`",
        f"- missing_featured_or_alt_posts: `{len(missing_featured)}`",
        f"- missing_canonical_pages: `{len(missing_canonical)}`",
        f"- missing_quick_summary_posts: `{len(missing_quick_summary)}`",
        f"- incomplete_quick_summary_posts: `{len(incomplete_quick_summary)}`",
        f"- missing_article_toc_posts: `{len(missing_article_toc)}`",
        "",
        f"{subheading} 공개 엔드포인트",
        "",
        "| 항목 | HTTP | Content-Type |",
        "|---|---:|---|",
    ]
    for name in ("robots", "sitemap", "ads_txt"):
        item = endpoint_rows[name]
        lines.append(f"| {name} | {item['status']} | {item['content_type'].replace('|', '\\|')} |")
    lines += ["", f"{subheading} 즉시 확인 항목", ""]
    lines.append("- 빈 카테고리: " + (", ".join(audit["empty_categories"]) or "없음"))
    lines.append(
        "- 리디렉션용 빈 레거시 카테고리: "
        + (", ".join(audit.get("legacy_empty_categories", [])) or "없음")
    )
    lines.append("- 깨진 내부 링크: " + (str(len(audit["broken_internal_links"])) + "개"))
    lines.append("- 네트워크 오류로 확인 보류: " + (str(len(audit["unverified_urls"])) + "개"))
    lines.append("- 일반 계정명 작성자 글: " + str(len(generic_authors)) + "개")
    lines.append("- 대표 이미지 또는 ALT 누락 글: " + str(len(missing_featured)) + "개")
    lines.append("- 20초 핵심 요약 누락 글: " + str(len(missing_quick_summary)) + "개")
    lines.append("- 20초 핵심 요약 빈 항목 글: " + str(len(incomplete_quick_summary)) + "개")
    lines.append("- 한눈에 보기 목차 누락 글: " + str(len(missing_article_toc)) + "개")
    failed_sitemaps = [item for item in audit["child_sitemaps"] if item["status"] != 200]
    if failed_sitemaps:
        lines.append("- 하위 Sitemap 조회 실패: " + str(len(failed_sitemaps)) + "개")
        for item in failed_sitemaps:
            lines.append(f"  - `{item['status'] or item['error']}` {item['url']}")
    if audit["broken_internal_links"]:
        lines += ["", f"{detail_heading} 깨진 내부 링크", ""]
        for item in audit["broken_internal_links"][:30]:
            lines.append(f"- `{item['status'] or item['error']}` {item['url']}")
    if audit["unverified_urls"]:
        lines += ["", f"{detail_heading} 확인 보류 URL", ""]
        for item in audit["unverified_urls"][:30]:
            lines.append(f"- `{item['error']}` {item['url']}")
    if missing_quick_summary:
        lines += ["", f"{detail_heading} 20초 핵심 요약 누락 글", ""]
        for page in missing_quick_summary:
            lines.append(f"- {page['url']}")
    if incomplete_quick_summary:
        lines += ["", f"{detail_heading} 20초 핵심 요약 빈 항목 글", ""]
        for page in incomplete_quick_summary:
            fields = page.get("quick_summary_fields", {})
            missing_fields = [label for label in ("무엇", "왜", "어떻게") if not fields.get(label, "").strip()]
            lines.append(f"- {page['url']} — {', '.join(missing_fields)}")
    lines += [
        "",
        f"{subheading} 기술 글 실증 근거 검토 후보",
        "",
        "아래 목록은 본문의 표면적 근거 표현을 찾는 보수적 점검이며 품질 판정이 아니다.",
    ]
    for page in evidence_review:
        signals = ", ".join(page["evidence_signals"]) or "명시적 근거 표현 없음"
        lines.append(f"- `{page['url']}` — {signals}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://huntlab.app/")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()
    audit = audit_site(args.base_url, timeout=args.timeout)
    report = render_markdown(audit)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(args.output)
    else:
        print(report, end="")
    return 0 if audit.get("status") == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
