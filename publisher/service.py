"""WordPress Publisher service governed by publisher-guide.md."""

from __future__ import annotations

import json
import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import markdown as markdown_lib

from .frontmatter import FrontmatterError, MarkdownDocument, load_document
from .models import PublishResult, ValidationIssue, ValidationReport
from .validation import EDITOR_CATEGORIES, normalize_tags, validate_document
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
        if document.metadata.get("publish_mode") == "publish":
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
            return self._failed(
                audit_id=audit_id,
                report=report,
                stage="wordpress_api",
                category=exc.category,
                message=exc.message,
                status_code=exc.status_code,
                wp_code=exc.wp_code,
                retry_count=exc.retry_count,
            )

    def _create_post(
        self,
        *,
        audit_id: str,
        document: MarkdownDocument,
        report: ValidationReport,
    ) -> PublishResult:
        metadata = document.metadata
        title = str(metadata["title"]).strip()
        slug = str(metadata.get("slug", "")).strip() or None
        publish_mode = str(metadata["publish_mode"])
        existing_post_id = metadata.get("existing_post_id")
        target_post_id = int(existing_post_id) if existing_post_id is not None else None

        if target_post_id is not None:
            target = self.client.get_post(target_post_id)
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

        categories: dict[str, dict[str, Any]] = {}
        for category_name in sorted(EDITOR_CATEGORIES):
            term = self.client.find_term("categories", category_name)
            if term is None:
                term = self.client.create_category(category_name)
                self.audit.write(
                    {
                        "audit_id": audit_id,
                        "event": "category_created",
                        "category_id": term.get("id"),
                        "category_name": category_name,
                    }
                )
            categories[category_name] = term
        category_value = str(metadata["category"]).strip()
        category = categories[category_value]
        category_id = int(category["id"])

        tag_ids: list[int] = []
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
            media = self.client.upload_media(
                image_path,
                alt_text=str(metadata["featured_image_alt"]).strip(),
            )
            featured_media_id = int(media["id"])
            self.audit.write(
                {
                    "audit_id": audit_id,
                    "event": "featured_media_uploaded",
                    "media_id": featured_media_id,
                    "filename": image_path.name,
                }
            )

        uploaded_body_media: dict[Path, tuple[int, str]] = {}

        def upload_body_image(match: re.Match[str]) -> str:
            alt_text, source = match.groups()
            if source.startswith(("http://", "https://")):
                return match.group(0)
            image_path = Path(source)
            if not image_path.is_absolute():
                image_path = (document.source_path.parent / image_path).resolve()
            if image_path not in uploaded_body_media:
                media = self.client.upload_media(image_path, alt_text=alt_text.strip())
                source_url = str(media.get("source_url", "")).strip()
                if not source_url:
                    raise WordPressError(
                        "api",
                        "WordPress media response did not include source_url.",
                    )
                media_id = int(media["id"])
                uploaded_body_media[image_path] = (media_id, source_url)
                self.audit.write(
                    {
                        "audit_id": audit_id,
                        "event": "body_media_uploaded",
                        "media_id": media_id,
                        "filename": image_path.name,
                    }
                )
            _, source_url = uploaded_body_media[image_path]
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
            "status": publish_mode,
            "tags": tag_ids,
            "categories": [category_id],
        }
        if slug:
            payload["slug"] = slug
        if featured_media_id is not None:
            payload["featured_media"] = featured_media_id
        excerpt = metadata.get("excerpt") or metadata.get("meta_description")
        if isinstance(excerpt, str) and excerpt.strip():
            payload["excerpt"] = excerpt.strip()

        if target_post_id is None:
            post = self.client.create_post(payload, status=publish_mode)
        else:
            post = self.client.update_post(
                target_post_id,
                payload,
                status=publish_mode,
            )
        post_id = int(post["id"])
        draft_url = (
            f"{self.client.config.base_url}/wp-admin/post.php"
            f"?post={post_id}&action=edit"
        )
        published_url = str(post.get("link", "")).strip() or None
        if target_post_id is not None:
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
                media_id for media_id, _ in uploaded_body_media.values()
            ],
            "completed_at": datetime.now(UTC).isoformat(),
        }
        self.audit.write(
            {
                "audit_id": audit_id,
                "status": "Success",
                "event": event_name,
                "post_id": post_id,
                "post_status": post.get("status", "draft"),
                "slug": post.get("slug") or slug,
                "category_id": category_id,
                "tag_ids": tag_ids,
                "featured_media_id": featured_media_id,
                "body_media_ids": [
                    media_id for media_id, _ in uploaded_body_media.values()
                ],
                "published_url": published_url,
                "edit_url": draft_url,
            }
        )
        return PublishResult(
            status="Success",
            action=action,
            post_id=post_id,
            draft_url=draft_url if publish_mode == "draft" else None,
            published_url=published_url if publish_mode == "publish" else None,
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
