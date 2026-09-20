"""WordPress Publisher service governed by publisher-guide.md."""

from __future__ import annotations

import json
import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import markdown as markdown_lib

from .frontmatter import FrontmatterError, MarkdownDocument, load_document
from .models import PublishResult, ValidationIssue, ValidationReport
from .validation import PHYSICAL_AI_CATEGORIES, normalize_tags, validate_document
from .wordpress import WordPressClient, WordPressError

LOCAL_MARKDOWN_IMAGE = re.compile(
    r"!\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)"
)


def _plain_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("rendered", ""))
    return str(value or "")


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


class _ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.casefold() != "img":
            return
        values = {name.casefold(): value or "" for name, value in attrs}
        if values.get("src"):
            self.images.append(values)


def _existing_images(post: dict[str, Any]) -> list[dict[str, str]]:
    parser = _ImageParser()
    parser.feed(_plain_text(post.get("content")))
    return parser.images


def _media_stem(source_url: str) -> str:
    return Path(unquote(urlparse(source_url).path)).stem.casefold()


def _same_media_url(left: str, right: str) -> bool:
    left_url = urlparse(left)
    right_url = urlparse(right)
    return (
        left_url.scheme.casefold(),
        left_url.netloc.casefold(),
        unquote(left_url.path),
    ) == (
        right_url.scheme.casefold(),
        right_url.netloc.casefold(),
        unquote(right_url.path),
    )


def _is_site_media_url(source_url: str, base_url: str) -> bool:
    source = urlparse(source_url)
    site = urlparse(base_url)
    return (
        source.scheme in {"http", "https"}
        and source.netloc.casefold() == site.netloc.casefold()
        and "/wp-content/uploads/" in unquote(source.path)
    )


def _image_media_id(image: dict[str, str]) -> int | None:
    matches = re.findall(r"(?:^|\s)wp-image-(\d+)(?:\s|$)", image.get("class", ""))
    return int(matches[0]) if len(matches) == 1 else None


def _matches_local_image(
    *,
    image_path: Path,
    alt_text: str,
    source_url: str,
    existing_alt: str,
) -> bool:
    local_stem = image_path.stem.casefold()
    source_stem = _media_stem(source_url)
    stem_matches = source_stem == local_stem or bool(
        re.fullmatch(rf"{re.escape(local_stem)}-\d+", source_stem)
    )
    return (
        bool(source_url)
        and stem_matches
        and _normalized(existing_alt) == _normalized(alt_text)
    )


class AuditLogger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        safe_event = dict(event)
        safe_event["timestamp"] = datetime.now(UTC).isoformat()
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(safe_event, ensure_ascii=False) + "\n")


class DraftPublisher:
    def __init__(
        self,
        client: WordPressClient,
        *,
        audit_log: Path = Path("logs/publisher-audit.jsonl"),
    ) -> None:
        self.client = client
        self.audit = AuditLogger(audit_log)

    def publish_file(
        self,
        path: Path,
        *,
        reviewer_approved: bool,
        review_path: Path | None = None,
        expected_identity: dict[str, str] | None = None,
        scheduled_at: datetime | None = None,
    ) -> PublishResult:
        audit_id = str(uuid.uuid4())
        try:
            document = load_document(path)
        except FrontmatterError as exc:
            report = ValidationReport()
            result = self._failed(
                audit_id=audit_id,
                report=report,
                stage="frontmatter",
                category="validation",
                message=str(exc),
            )
            self.audit.write(
                {
                    "audit_id": audit_id,
                    "status": "Failed",
                    "stage": "frontmatter",
                    "error_category": "validation",
                }
            )
            return result

        report = validate_document(
            document,
            reviewer_approved=reviewer_approved,
        )
        if scheduled_at is not None:
            schedule_error = self._schedule_error(scheduled_at, document.metadata)
            if schedule_error:
                report.errors.append(ValidationIssue(code=schedule_error,
                    message="Scheduling requires an aware future 10:00 KST time within seven days, publish approval, and zero retries."))
            report.checks["schedule_envelope"] = "failed" if schedule_error else "passed"
        if document.metadata.get("publish_mode") == "publish":
            from publisher.foundation_links import enforce_foundation_links, FoundationLinkError
            try:
                enforce_foundation_links(document)
            except FoundationLinkError as exc:
                report.errors.append(ValidationIssue(code=str(exc), message="Foundation evidence must be linked in the article body."))
            if document.metadata.get("category") in PHYSICAL_AI_CATEGORIES:
                from scripts.physical_ai_quality_gate import enforce_quality, PhysicalAIQualityError
                try:
                    enforce_quality(path, path.parent / "physical-ai-quality-review.json")
                except PhysicalAIQualityError:
                    report.errors.append(ValidationIssue(
                        code="physical_quality_review_failed",
                        message="Physical AI publication requires current independent quality and naturalness approval.",
                    ))
            identity = expected_identity or {}
            for field in ("run_id", "topic_id", "source_id", "category"):
                expected_value = identity.get(field)
                if not expected_value or document.metadata.get(field) != expected_value:
                    report.errors.append(
                        ValidationIssue(
                            code=f"{field}_verification_failed",
                            message=f"{field} must match the Publisher invocation.",
                            field=field,
                        )
                    )
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if review_path is None or not review_path.is_file():
                report.errors.append(
                    ValidationIssue(
                        code="review_hash_missing",
                        message="Publish requires the exact Reviewer approval record.",
                    )
                )
            else:
                review = review_path.read_text(encoding="utf-8")
                required = (
                    "APPROVED",
                    digest,
                    str(document.metadata.get("run_id", "")),
                    str(document.metadata.get("topic_id", "")),
                )
                if not all(token and token in review for token in required):
                    report.errors.append(
                        ValidationIssue(
                            code="review_hash_mismatch",
                            message="Reviewer approval does not match this publish.md.",
                        )
                    )
            report.checks["publish_identity"] = (
                "passed"
                if not any(
                    issue.code.endswith("_verification_failed")
                    or issue.code.startswith("review_hash_")
                    for issue in report.errors
                )
                else "failed"
            )
        self.audit.write(
            {
                "audit_id": audit_id,
                "event": "validation",
                "status": "passed" if report.passed else "failed",
                "source": str(path),
                "requested_mode": document.metadata.get("publish_mode", "draft"),
                "reviewer_approved": reviewer_approved,
                "error_codes": [issue.code for issue in report.errors],
            }
        )
        if not report.passed:
            return self._failed(
                audit_id=audit_id,
                report=report,
                stage="validation",
                category="validation",
                message="Validation failed; no WordPress resources were created.",
            )

        try:
            return self._create_post(
                audit_id=audit_id,
                document=document,
                report=report,
                scheduled_at=scheduled_at,
            )
        except WordPressError as exc:
            self.audit.write(
                {
                    "audit_id": audit_id,
                    "status": "Failed",
                    "stage": "wordpress_api",
                    "error_category": exc.category,
                    "http_status": exc.status_code,
                    "wp_code": exc.wp_code,
                    "retry_count": exc.retry_count,
                }
            )
            result = self._failed(
                audit_id=audit_id,
                report=report,
                stage="wordpress_api",
                category=exc.category,
                message=exc.message,
                status_code=exc.status_code,
                wp_code=exc.wp_code,
                retry_count=exc.retry_count,
            )
            if scheduled_at is not None:
                # Media or the future post may already have been stored.
                # Never tell the caller it is safe to blindly repeat this run.
                result.error_report["resources_created"] = "unknown"
                result.error_report["requires_read_only_reconciliation"] = True
            return result

    def _schedule_error(self, scheduled_at: datetime, metadata: dict) -> str | None:
        if metadata.get("publish_mode") != "publish":
            return "schedule_requires_publish_approval"
        if not isinstance(scheduled_at, datetime) or scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
            return "schedule_timezone_required"
        current = datetime.now(UTC)
        if not current < scheduled_at.astimezone(UTC) <= current + timedelta(days=7):
            return "schedule_outside_window"
        local = scheduled_at.astimezone(ZoneInfo("Asia/Seoul"))
        if (local.hour, local.minute, local.second, local.microsecond) != (10, 0, 0, 0):
            return "schedule_requires_10_kst"
        if getattr(self.client, "max_retries", None) != 0:
            return "schedule_requires_zero_retries"
        return None

    def _create_post(
        self,
        *,
        audit_id: str,
        document: MarkdownDocument,
        report: ValidationReport,
        scheduled_at: datetime | None = None,
    ) -> PublishResult:
        metadata = document.metadata
        title = str(metadata["title"]).strip()
        slug = str(metadata.get("slug", "")).strip() or None
        publish_mode = str(metadata["publish_mode"])
        if scheduled_at is not None:
            error = self._schedule_error(scheduled_at, metadata)
            if error:
                raise WordPressError("validation", error)
        post_status = "future" if scheduled_at is not None else publish_mode
        existing_post_id = metadata.get("existing_post_id")
        target_post_id = int(existing_post_id) if existing_post_id is not None else None
        target: dict[str, Any] | None = None

        if target_post_id is not None:
            target = self.client.get_post(target_post_id)
            if scheduled_at is not None and target.get("status") != "draft":
                raise WordPressError("validation", "Scheduling an existing target requires a draft; published or future posts are not overwritten.")
            target_title = _normalized(_plain_text(target.get("title")))
            target_slug = str(target.get("slug", "")).strip()
            if target_title != _normalized(title):
                raise WordPressError(
                    "validation",
                    "existing_post_id title does not match the approved document.",
                )
            if slug and target_slug != slug:
                raise WordPressError(
                    "validation",
                    "existing_post_id slug does not match the approved document.",
                )

        title_matches = self.client.find_posts(title=title)
        exact_title_matches = [
            post
            for post in title_matches
            if _normalized(_plain_text(post.get("title"))) == _normalized(title)
            and int(post.get("id", 0)) != target_post_id
        ]
        if exact_title_matches:
            raise WordPressError(
                "duplicate",
                "An existing WordPress post has the same normalized title.",
            )
        slug_matches = self.client.find_posts(slug=slug) if slug else []
        if slug and any(int(post.get("id", 0)) != target_post_id for post in slug_matches):
            raise WordPressError(
                "duplicate",
                "An existing WordPress post already uses the requested slug.",
            )
        report.checks["duplicate_title"] = "passed"
        report.checks["duplicate_slug"] = "passed" if slug else "not provided"

        category_value = str(metadata["category"]).strip()
        category = self.client.find_term("categories", category_value)
        if category is None:
            raise WordPressError(
                "validation",
                f"WordPress category does not exist: {category_value}",
            )
        category_id = int(category["id"])

        tag_ids: list[int] = []
        if scheduled_at is not None:
            error = self._schedule_error(scheduled_at, metadata)
            if error:
                raise WordPressError("validation", error)
        for tag_name in normalize_tags(metadata.get("tags")):
            term = self.client.find_term("tags", tag_name)
            if term is None:
                term = self.client.create_tag(tag_name)
                self.audit.write(
                    {
                        "audit_id": audit_id,
                        "event": "tag_created",
                        "tag_id": term.get("id"),
                        "tag_name": tag_name,
                    }
                )
            tag_ids.append(int(term["id"]))

        can_reuse_existing_media = (
            target is not None
            and bool(str(metadata.get("source_id", "")).strip())
            and report.checks.get("publish_identity") == "passed"
        )
        featured_media_id: int | None = None
        featured_image = metadata.get("featured_image")
        if featured_image:
            image_path = Path(str(featured_image))
            if not image_path.is_absolute():
                image_path = document.source_path.parent / image_path
            if not image_path.is_file():
                raise WordPressError(
                    "validation",
                    "Featured image file does not exist.",
                )
            featured_alt = str(metadata["featured_image_alt"]).strip()
            existing_featured_id = (
                int(target.get("featured_media", 0)) if target else 0
            )
            if can_reuse_existing_media and existing_featured_id:
                existing_featured = self.client.get_media(existing_featured_id)
                source_url = str(existing_featured.get("source_url", "")).strip()
                existing_alt = str(existing_featured.get("alt_text", "")).strip()
                if _matches_local_image(
                    image_path=image_path,
                    alt_text=featured_alt,
                    source_url=source_url,
                    existing_alt=existing_alt,
                ):
                    featured_media_id = existing_featured_id
                    self.audit.write(
                        {
                            "audit_id": audit_id,
                            "event": "featured_media_reused",
                            "media_id": featured_media_id,
                            "filename": image_path.name,
                        }
                    )
            if featured_media_id is None:
                media = self.client.upload_media(image_path, alt_text=featured_alt)
                featured_media_id = int(media["id"])
                self.audit.write(
                    {
                        "audit_id": audit_id,
                        "event": "featured_media_uploaded",
                        "media_id": featured_media_id,
                        "filename": image_path.name,
                    }
                )

        body_media: dict[Path, tuple[int, str]] = {}
        target_images = (
            _existing_images(target)
            if can_reuse_existing_media and target
            else []
        )

        def upload_body_image(match: re.Match[str]) -> str:
            alt_text, source = match.groups()
            if source.startswith(("http://", "https://")):
                return match.group(0)
            image_path = Path(source)
            if not image_path.is_absolute():
                image_path = (document.source_path.parent / image_path).resolve()
            if image_path not in body_media:
                clean_alt = alt_text.strip()
                candidates = [
                    image
                    for image in target_images
                    if _is_site_media_url(
                        image.get("src", ""),
                        self.client.config.base_url,
                    )
                    and _matches_local_image(
                        image_path=image_path,
                        alt_text=clean_alt,
                        source_url=image.get("src", ""),
                        existing_alt=image.get("alt", ""),
                    )
                ]
                if len(candidates) == 1:
                    source_url = candidates[0]["src"]
                    existing_media_id = _image_media_id(candidates[0])
                    existing_media = (
                        self.client.get_media(existing_media_id)
                        if existing_media_id is not None
                        else self.client.find_media_by_source_url(source_url)
                    )
                    if (
                        existing_media is not None
                        and _same_media_url(
                            str(existing_media.get("source_url", "")),
                            source_url,
                        )
                        and _normalized(str(existing_media.get("alt_text", "")))
                        == _normalized(clean_alt)
                    ):
                        media_id = int(existing_media["id"])
                        body_media[image_path] = (media_id, source_url)
                        self.audit.write(
                            {
                                "audit_id": audit_id,
                                "event": "body_media_reused",
                                "media_id": media_id,
                                "filename": image_path.name,
                            }
                        )
                if image_path not in body_media:
                    media = self.client.upload_media(image_path, alt_text=clean_alt)
                    source_url = str(media.get("source_url", "")).strip()
                    if not source_url:
                        raise WordPressError(
                            "api",
                            "WordPress media response did not include source_url.",
                        )
                    media_id = int(media["id"])
                    body_media[image_path] = (media_id, source_url)
                    self.audit.write(
                        {
                            "audit_id": audit_id,
                            "event": "body_media_uploaded",
                            "media_id": media_id,
                            "filename": image_path.name,
                        }
                    )
            _, source_url = body_media[image_path]
            return f"![{alt_text}]({source_url})"

        wordpress_markdown = LOCAL_MARKDOWN_IMAGE.sub(
            upload_body_image,
            document.markdown,
        )
        html = markdown_lib.markdown(
            wordpress_markdown,
            extensions=["extra", "sane_lists"],
            output_format="html5",
        )
        payload: dict[str, Any] = {
            "title": title,
            "content": html,
            "status": post_status,
            "tags": tag_ids,
            "categories": [category_id],
        }
        if scheduled_at is not None:
            payload["date_gmt"] = scheduled_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")
            payload["date"] = scheduled_at.astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%dT%H:%M:%S")
        if slug:
            payload["slug"] = slug
        if featured_media_id is not None:
            payload["featured_media"] = featured_media_id
        excerpt = metadata.get("excerpt") or metadata.get("meta_description")
        if isinstance(excerpt, str) and excerpt.strip():
            payload["excerpt"] = excerpt.strip()
        if metadata.get("content_type"):
            payload["meta"] = {
                "_hunt_news_content_type": str(metadata.get("content_type", "")),
                "_hunt_news_problem_group": str(metadata.get("problem_group", "")),
                "_hunt_news_verification_method": str(metadata.get("verification_method", "")),
                "_hunt_news_evidence_date": str(metadata.get("evidence_date", "")),
                "_hunt_news_evidence_badges": json.dumps(metadata.get("evidence_badges") or [], ensure_ascii=False),
                "_hunt_news_evidence_url": str(metadata.get("evidence_url", "")),
                "_hunt_news_asset_url": str(metadata.get("asset_url", "")),
            }

        if scheduled_at is not None:
            error = self._schedule_error(scheduled_at, metadata)
            if error:
                raise WordPressError("validation", error)
        if target_post_id is None:
            if scheduled_at is not None:
                # First use of the scheduling workflow must prove a stored draft
                # before converting that same resource to native WP future.
                draft_payload = {key: value for key, value in payload.items()
                                 if key not in {"date", "date_gmt"}}
                post = self.client.create_post(draft_payload, status="draft")
                draft_id = int(post["id"])
                draft_readback = self.client.get_post(draft_id)
                if (draft_readback.get("id") != draft_id
                    or draft_readback.get("status") != "draft"
                    or _normalized(_plain_text(draft_readback.get("title"))) != _normalized(title)
                    or (slug and draft_readback.get("slug") != slug)
                    or draft_readback.get("content", {}).get("raw") != html):
                    raise WordPressError("readback", "Scheduling draft-first identity/body verification failed.")
                report.checks["schedule_draft_first"] = "passed"
                self.audit.write({"audit_id": audit_id, "event": "schedule_draft_verified",
                                  "post_id": draft_id, "post_status": "draft"})
                error = self._schedule_error(scheduled_at, metadata)
                if error:
                    raise WordPressError("validation", error)
                post = self.client.update_post(draft_id, payload, status="future")
            else:
                post = self.client.create_post(payload, status=post_status)
        else:
            post = self.client.update_post(
                target_post_id,
                payload,
                status=post_status,
            )
        post_id = int(post["id"])
        readback = self.client.get_post(post_id)
        readback_title = _normalized(_plain_text(readback.get("title")))
        readback_slug = str(readback.get("slug", "")).strip()
        readback_status = str(readback.get("status", "")).strip()
        if (
            int(readback.get("id", 0)) != post_id
            or readback_title != _normalized(title)
            or (slug and readback_slug != slug)
            or readback_status != post_status
        ):
            raise WordPressError(
                "readback",
                "WordPress REST read-back did not match the approved post identity.",
            )
        if scheduled_at is not None:
            if any(readback.get(field) != payload[field] for field in ("date", "date_gmt")):
                raise WordPressError("readback", "WordPress scheduled dates do not match the scheduling envelope.")
            if readback.get("content", {}).get("raw") != html:
                raise WordPressError("readback", "WordPress scheduled content does not match the approved body.")
            report.checks["wordpress_schedule_readback"] = "passed"
        report.checks["wordpress_readback"] = "passed"
        post = readback
        draft_url = (
            f"{self.client.config.base_url}/wp-admin/post.php"
            f"?post={post_id}&action=edit"
        )
        published_url = (str(post.get("link", "")).strip() or None) if post_status == "publish" else None
        if scheduled_at is not None:
            action = "Schedule"
            event_name = "post_scheduled"
        elif target_post_id is not None:
            action = "Update"
            event_name = "post_updated"
        else:
            action = "Publish" if publish_mode == "publish" else "Draft"
            event_name = "post_published" if publish_mode == "publish" else "draft_created"
        summary = {
            "action": action,
            "final_status": post.get("status", publish_mode),
            "title": title,
            "slug": post.get("slug") or slug,
            "post_id": post_id,
            "category_id": category_id,
            "tag_ids": tag_ids,
            "featured_media_id": featured_media_id,
            "body_media_ids": [
                media_id for media_id, _ in body_media.values()
            ],
            "completed_at": datetime.now(UTC).isoformat(),
        }
        if scheduled_at is not None:
            summary.update(scheduled_at=scheduled_at.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
                           date=post["date"], date_gmt=post["date_gmt"], publicly_published=False)
        self.audit.write(
            {
                "audit_id": audit_id,
                "status": "Success",
                "event": event_name,
                "action": action,
                "post_id": post_id,
                "post_status": post.get("status", "draft"),
                "slug": post.get("slug") or slug,
                "category_id": category_id,
                "tag_ids": tag_ids,
                "featured_media_id": featured_media_id,
                "body_media_ids": [
                    media_id for media_id, _ in body_media.values()
                ],
                "published_url": published_url,
                "edit_url": draft_url,
                **({"date": post["date"], "date_gmt": post["date_gmt"],
                    "scheduled_at": summary["scheduled_at"]} if scheduled_at is not None else {}),
            }
        )
        return PublishResult(
            status="Success",
            action=action,
            post_id=post_id,
            draft_url=draft_url if post_status in {"draft", "future"} else None,
            published_url=published_url,
            validation_report=report,
            error_report=None,
            publish_summary=summary,
            audit_id=audit_id,
        )

    @staticmethod
    def _failed(
        *,
        audit_id: str,
        report: ValidationReport,
        stage: str,
        category: str,
        message: str,
        status_code: int | None = None,
        wp_code: str | None = None,
        retry_count: int = 0,
    ) -> PublishResult:
        return PublishResult(
            status="Failed",
            action="None",
            post_id=None,
            draft_url=None,
            published_url=None,
            validation_report=report,
            error_report={
                "stage": stage,
                "category": category,
                "message": message,
                "http_status": status_code,
                "wordpress_code": wp_code,
                "retry_count": retry_count,
                "resources_created": False,
            },
            publish_summary={
                "action": "None",
                "final_status": "Failed",
                "completed_at": datetime.now(UTC).isoformat(),
            },
            audit_id=audit_id,
        )
