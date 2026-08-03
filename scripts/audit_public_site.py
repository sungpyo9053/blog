"""Read-only public WordPress quality audit for HuntLab."""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

USER_AGENT = "HuntLabPublicAudit/1.0 (+https://huntlab.app/)"
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
    og_image: str = ""
    noindex: bool = False
    featured_alt: str | None = None
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
        self.og_image = ""
        self.robots = ""
        self.featured_alt: str | None = None
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag in {"script", "style", "noscript"}:
            self.ignored_depth += 1
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key = (values.get("name") or values.get("property") or "").lower()
            content = values.get("content", "").strip()
            if key == "author":
                self.author = content
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


def fetch(url: str, *, timeout: float = 6.0, method: str = "GET") -> FetchResult:
    marker = b"\n__HUNTLAB_AUDIT_META__"
    last_error = ""
    for _attempt in range(2):
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
                continue
            status_text, content_type, effective_url = metadata.decode("utf-8", errors="replace").split("\t", 2)
            status = int(status_text)
            return FetchResult(
                url=effective_url,
                status=status,
                content_type=content_type,
                body=body if method == "GET" else b"",
                error="" if completed.returncode == 0 and status < 400 else "CurlHTTPError",
            )
        except (OSError, ValueError) as exc:
            last_error = type(exc).__name__
    return FetchResult(url=url, status=0, error=last_error)


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
    parser = PageParser(result.url)
    parser.feed(result.body.decode("utf-8", errors="replace"))
    visible_text = " ".join(parser.text_parts)
    facts.title = " ".join(parser.title_parts).strip()
    facts.canonical = parser.canonical
    facts.author = parser.author
    facts.og_image = parser.og_image
    facts.noindex = "noindex" in parser.robots
    facts.featured_alt = parser.featured_alt
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
    with ThreadPoolExecutor(max_workers=4) as executor:
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

    return {
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
        "empty_categories": sorted(category.get("name", "") for category in categories if category.get("count") == 0),
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
    evidence_review = sorted(verified_posts, key=lambda page: (len(page["evidence_signals"]), page["url"]))[:10]
    endpoint_rows = audit["endpoints"]
    heading = "#" * heading_level
    subheading = "#" * (heading_level + 1)
    detail_heading = "#" * (heading_level + 2)
    lines = [
        f"{heading} Public Site Quality Audit",
        "",
        f"- base_url: `{audit['base_url']}`",
        f"- posts: `{audit['counts']['post']}`",
        f"- pages: `{audit['counts']['page']}`",
        f"- categories_in_sitemap: `{audit['counts']['category']}`",
        f"- broken_internal_links: `{len(audit['broken_internal_links'])}`",
        f"- unverified_urls: `{len(audit['unverified_urls'])}`",
        f"- empty_categories: `{len(audit['empty_categories'])}`",
        f"- generic_author_posts: `{len(generic_authors)}`",
        f"- missing_featured_or_alt_posts: `{len(missing_featured)}`",
        f"- missing_canonical_pages: `{len(missing_canonical)}`",
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
    lines.append("- 깨진 내부 링크: " + (str(len(audit["broken_internal_links"])) + "개"))
    lines.append("- 네트워크 오류로 확인 보류: " + (str(len(audit["unverified_urls"])) + "개"))
    lines.append("- 일반 계정명 작성자 글: " + str(len(generic_authors)) + "개")
    lines.append("- 대표 이미지 또는 ALT 누락 글: " + str(len(missing_featured)) + "개")
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
    report = render_markdown(audit_site(args.base_url, timeout=args.timeout))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(args.output)
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
