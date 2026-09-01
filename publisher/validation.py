"""Policy-oriented validation for WordPress draft creation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .frontmatter import MarkdownDocument
from .models import ValidationIssue, ValidationReport

ACTIVE_EDITOR_CATEGORIES = {
    "AI/ML 핵심",
    "개발 트렌드",
    "AI 공식 블로그",
    "국내 IT",
    "국내 시사",
}
SPECIAL_EDITOR_CATEGORIES = {"기술 해설", "주간 기술 회고"}
LEGACY_EDITOR_CATEGORIES = {
    "생활", "경제", "부동산", "사회", "정치", "문화·엔터", "IT",
    "Tech",
    "AI",
    "Economy",
    "Society",
    "Politics",
    "Hot Issue",
    "Build Log",
    "ML Algorithms",
    "Harness Engineering",
    "System Architecture",
}
# Old approved runs can still be resumed, while every newly planned run uses
# the active Hunt News categories above.
EDITOR_CATEGORIES = ACTIVE_EDITOR_CATEGORIES | SPECIAL_EDITOR_CATEGORIES | LEGACY_EDITOR_CATEGORIES
FORBIDDEN_TERMS = (
    "100%",
    "무조건",
    "완벽",
    "절대",
    "유일",
    "1위",
    "최고",
    "공식",
    "최저가",
)
SECRET_PATTERNS = (
    # A TypeScript declaration such as ``API_KEY: string;`` describes a type,
    # not a credential assignment. Require an assignment value for key-like
    # fields while retaining the explicit Bearer-token check below.
    re.compile(
        r"(?i)(api[_ -]?key|app[_ -]?password|authorization)\s*[:=]"
        r"(?!\s*(?:string|number|boolean)\b)\s*"
    ),
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]{12,}"),
)
SAFE_SECRET_PLACEHOLDER = re.compile(
    r"(?im)^\s*(?:"
    r"authorization\s*:\s*(?:bearer|basic)\s+|"
    r"(?:api[_ -]?key|app[_ -]?password)\s*[:=]\s*"
    r")"
    r"(?:\{[A-Z][A-Z0-9_]*\}|\$\{[A-Z][A-Z0-9_]*\}|"
    r"<[A-Z][A-Z0-9_]*>|YOUR_[A-Z][A-Z0-9_]*|REDACTED)"
    r"\s*$"
)
MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^(#{1,6})\s+\S", re.MULTILINE)
FENCE = re.compile(r"^```([^\n]*)$", re.MULTILINE)


def _mask_fenced_code(markdown: str) -> str:
    """Hide fenced code contents from Markdown structure checks.

    Preserve line breaks so headings outside a fence keep their relative order.
    An unclosed fence is masked through EOF and reported separately by the
    existing fence validation.
    """
    fences = list(FENCE.finditer(markdown))
    if not fences:
        return markdown

    masked: list[str] = []
    cursor = 0
    for index in range(0, len(fences), 2):
        opening = fences[index]
        closing = fences[index + 1] if index + 1 < len(fences) else None
        end = closing.end() if closing else len(markdown)
        masked.append(markdown[cursor : opening.start()])
        masked.append("\n" * markdown[opening.start() : end].count("\n"))
        cursor = end
    masked.append(markdown[cursor:])
    return "".join(masked)


def normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        candidates = [str(part).strip() for part in value]
    else:
        return []

    result: list[str] = []
    seen: set[str] = set()
    for tag in candidates:
        normalized = re.sub(r"\s+", " ", tag).strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            result.append(normalized)
            seen.add(key)
    return result


def _add_error(
    report: ValidationReport, code: str, message: str, field: str | None = None
) -> None:
    report.errors.append(ValidationIssue(code=code, message=message, field=field))


def _add_warning(
    report: ValidationReport, code: str, message: str, field: str | None = None
) -> None:
    report.warnings.append(ValidationIssue(code=code, message=message, field=field))


def validate_document(
    document: MarkdownDocument,
    *,
    reviewer_approved: bool,
) -> ValidationReport:
    report = ValidationReport()
    metadata = document.metadata
    markdown = document.markdown

    if not reviewer_approved:
        _add_error(
            report,
            "reviewer_approval_required",
            "Explicit Reviewer approval is required before Publisher execution.",
        )
    report.checks["reviewer_approval"] = "passed" if reviewer_approved else "failed"

    title = metadata.get("title")
    if not isinstance(title, str) or not title.strip():
        _add_error(report, "missing_title", "title is required.", "title")

    category = metadata.get("category")
    if not isinstance(category, str) or not category.strip():
        _add_error(
            report,
            "missing_category",
            "category must be a non-empty Hunt News category name.",
            "category",
        )
    elif isinstance(category, str) and category.strip() not in EDITOR_CATEGORIES:
        _add_error(
            report,
            "unsupported_category",
            "category must be one of the Hunt News editorial categories.",
            "category",
        )

    publish_mode = metadata.get("publish_mode")
    if publish_mode is None:
        _add_error(
            report,
            "missing_publish_mode",
            "publish_mode is required by Frontmatter policy.",
            "publish_mode",
        )
    elif publish_mode not in {"draft", "publish"}:
        _add_error(
            report,
            "unsupported_publish_mode",
            "publish_mode must be draft or publish.",
            "publish_mode",
        )

    existing_post_id = metadata.get("existing_post_id")
    if existing_post_id is not None and (
        isinstance(existing_post_id, bool)
        or not isinstance(existing_post_id, int)
        or existing_post_id <= 0
    ):
        _add_error(
            report,
            "invalid_existing_post_id",
            "existing_post_id must be a positive WordPress post ID.",
            "existing_post_id",
        )

    if not markdown:
        _add_error(report, "missing_markdown", "Markdown body is required.", "markdown")

    tags = normalize_tags(metadata.get("tags"))
    if len(tags) < 3 or len(tags) > 4:
        _add_error(
            report,
            "invalid_tag_count",
            "After duplicate removal, tags must contain 3 to 4 reusable items.",
            "tags",
        )
    if metadata.get("tags") is not None and not tags:
        _add_error(report, "invalid_tags", "tags must be a list or comma-separated text.")
    report.checks["tags"] = f"{len(tags)} unique tag(s)"

    structural_markdown = _mask_fenced_code(markdown)
    h1_matches = re.findall(r"^#\s+\S", structural_markdown, flags=re.MULTILINE)
    if h1_matches:
        _add_error(
            report,
            "body_h1_not_allowed",
            "The WordPress title owns H1; Markdown body must start at H2.",
            "markdown",
        )

    heading_levels = [
        len(match.group(1)) for match in HEADING.finditer(structural_markdown)
    ]
    for previous, current in zip(heading_levels, heading_levels[1:]):
        if current > previous + 1:
            _add_error(
                report,
                "heading_level_skipped",
                f"Heading level jumps from H{previous} to H{current}.",
                "markdown",
            )
            break
    report.checks["heading_structure"] = (
        "failed"
        if any(issue.code.startswith(("body_h1", "heading_level")) for issue in report.errors)
        else "passed"
    )

    fences = list(FENCE.finditer(markdown))
    if len(fences) % 2:
        _add_error(
            report,
            "unclosed_code_fence",
            "A fenced code block is not closed.",
            "markdown",
        )
    else:
        for opening, closing in zip(fences[0::2], fences[1::2]):
            if not markdown[opening.end() : closing.start()].strip():
                _add_error(
                    report,
                    "empty_code_block",
                    "Empty fenced code blocks are not allowed.",
                    "markdown",
                )
                break

    for alt, src in MARKDOWN_IMAGE.findall(markdown):
        if not alt.strip():
            _add_error(
                report,
                "empty_image_alt",
                f"Image ALT is empty for {src}.",
                "markdown",
            )
        filename = Path(urlparse(src).path).stem.replace("-", " ").replace("_", " ")
        if alt.strip().casefold() == filename.strip().casefold():
            _add_error(
                report,
                "filename_only_image_alt",
                f"Image ALT must describe the image, not repeat its filename: {src}.",
                "markdown",
            )
        parsed = urlparse(src)
        if not parsed.scheme:
            image_path = Path(src)
            if not image_path.is_absolute():
                image_path = document.source_path.parent / image_path
            if not image_path.is_file():
                _add_error(
                    report,
                    "missing_local_image",
                    f"Local body image does not exist: {src}.",
                    "markdown",
                )

    for _, target in MARKDOWN_LINK.findall(markdown):
        parsed = urlparse(target)
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            _add_error(
                report,
                "unsafe_link_scheme",
                f"Unsupported link scheme: {parsed.scheme}.",
                "markdown",
            )
        elif parsed.scheme in {"http", "https"} and not parsed.netloc:
            _add_error(
                report,
                "invalid_link",
                f"Invalid absolute link: {target}.",
                "markdown",
            )
    report.checks["link_syntax"] = (
        "failed"
        if any(issue.code in {"unsafe_link_scheme", "invalid_link"} for issue in report.errors)
        else "passed"
    )

    detected_terms = [term for term in FORBIDDEN_TERMS if term in markdown]
    if detected_terms:
        message = (
            "Potentially prohibited expressions require contextual human review: "
            + ", ".join(detected_terms)
        )
        if reviewer_approved:
            _add_warning(
                report,
                "reviewed_sensitive_expression",
                message,
                "markdown",
            )
        else:
            _add_error(
                report,
                "forbidden_expression_requires_review",
                message,
                "markdown",
            )

    secret_scan_text = SAFE_SECRET_PLACEHOLDER.sub("", markdown)
    for pattern in SECRET_PATTERNS:
        if pattern.search(secret_scan_text):
            _add_error(
                report,
                "possible_secret_exposure",
                "Markdown may contain an API credential or authorization secret.",
                "markdown",
            )
            break

    featured_image = metadata.get("featured_image")
    featured_alt = metadata.get("featured_image_alt")
    if featured_image and not (
        isinstance(featured_image, str) and featured_image.strip()
    ):
        _add_error(
            report,
            "invalid_featured_image",
            "featured_image must be a local path string.",
            "featured_image",
        )
    if featured_image and not (
        isinstance(featured_alt, str) and featured_alt.strip()
    ):
        _add_error(
            report,
            "missing_featured_image_alt",
            "featured_image_alt is required when featured_image is provided.",
            "featured_image_alt",
        )
    if isinstance(featured_image, str) and featured_image.strip():
        featured_path = Path(featured_image)
        if not featured_path.is_absolute():
            featured_path = document.source_path.parent / featured_path
        if not featured_path.is_file():
            _add_error(
                report,
                "missing_featured_image",
                f"Featured image file does not exist: {featured_image}.",
                "featured_image",
            )
    if not featured_image:
        _add_warning(
            report,
            "featured_image_missing",
            "Draft will be created without a featured image.",
            "featured_image",
        )

    report.checks["frontmatter"] = (
        "passed"
        if not any(issue.field and issue.field != "markdown" for issue in report.errors)
        else "failed"
    )
    report.checks["markdown"] = (
        "passed"
        if not any(issue.field == "markdown" for issue in report.errors)
        else "failed"
    )
    report.checks["publish_mode"] = str(publish_mode)
    return report
