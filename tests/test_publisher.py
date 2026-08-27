from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from publisher.frontmatter import load_document
from publisher.service import DraftPublisher
from publisher.validation import EDITOR_CATEGORIES, validate_document


VALID_MARKDOWN = """---
title: HuntLab Publisher 테스트
slug: huntlab-publisher-test
category: Tech
tags:
  - WordPress
  - Publisher
  - Automation
publish_mode: draft
meta_description: HuntLab Publisher의 Draft 생성 검증 문서입니다.
---

## Publisher 개요

Reviewer가 승인한 문서를 Draft로 전달합니다.

### 검증 항목

- Frontmatter
- Markdown
- Audit Log
"""


class FakeWordPressClient:
    def __init__(self) -> None:
        self.created_payload: dict[str, Any] | None = None
        self.tags: dict[str, int] = {}
        self.categories: dict[str, int] = {
            name: index + 7 for index, name in enumerate(sorted(EDITOR_CATEGORIES))
        }
        self.create_category_calls: list[str] = []
        self.posts: dict[int, dict[str, Any]] = {}
        self.media: dict[int, dict[str, Any]] = {}
        self.upload_calls: list[tuple[Path, str]] = []
        self.config = type(
            "Config",
            (),
            {"base_url": "https://huntlab.app"},
        )()

    def find_posts(self, *, title: str | None = None, slug: str | None = None):
        posts = list(self.posts.values())
        if title is not None:
            posts = [post for post in posts if title in post["title"]["rendered"]]
        if slug is not None:
            posts = [post for post in posts if post.get("slug") == slug]
        return posts

    def get_post(self, post_id: int):
        return self.posts[post_id]

    def get_media(self, media_id: int):
        return self.media[media_id]

    def find_media_by_source_url(self, source_url: str):
        matches = [
            media
            for media in self.media.values()
            if media.get("source_url") == source_url
        ]
        return matches[0] if len(matches) == 1 else None

    def find_term(self, taxonomy: str, name: str):
        if taxonomy == "categories" and name in self.categories:
            return {"id": self.categories[name], "name": name}
        if taxonomy == "tags" and name in self.tags:
            return {"id": self.tags[name], "name": name}
        return None

    def create_tag(self, name: str):
        tag_id = len(self.tags) + 20
        self.tags[name] = tag_id
        return {"id": tag_id, "name": name}

    def create_category(self, name: str):
        self.create_category_calls.append(name)
        category_id = len(self.categories) + 7
        self.categories[name] = category_id
        return {"id": category_id, "name": name}

    def upload_media(self, path: Path, *, alt_text: str):
        self.upload_calls.append((path, alt_text))
        media_id = 99 + len(self.upload_calls) - 1
        return {
            "id": media_id,
            "alt_text": alt_text,
            "source_url": f"https://huntlab.app/wp-content/uploads/{path.name}",
        }

    def create_draft(self, payload: dict[str, Any]):
        return self.create_post(payload, status="draft")

    def create_post(self, payload: dict[str, Any], *, status: str):
        self.created_payload = payload
        self.created_payload["status"] = status
        return {
            "id": 123,
            "status": status,
            "slug": payload.get("slug"),
            "link": "https://huntlab.app/?p=123",
        }

    def update_post(self, post_id: int, payload: dict[str, Any], *, status: str):
        self.created_payload = dict(payload)
        self.created_payload["status"] = status
        return {
            "id": post_id,
            "status": status,
            "slug": payload.get("slug"),
            "link": f"https://huntlab.app/?p={post_id}",
        }


class PublisherTests(unittest.TestCase):
    def _write_document(self, root: Path, text: str = VALID_MARKDOWN) -> Path:
        path = root / "post.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_validation_requires_reviewer_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = load_document(self._write_document(Path(tmp)))
            report = validate_document(document, reviewer_approved=False)
            self.assertFalse(report.passed)
            self.assertIn(
                "reviewer_approval_required",
                {issue.code for issue in report.errors},
            )

    def test_validation_accepts_every_active_hunt_news_category(self):
        for category in (
            "AI/ML 핵심",
            "개발 트렌드",
            "AI 공식 블로그",
            "국내 IT",
            "국내 시사",
        ):
            with self.subTest(category=category), tempfile.TemporaryDirectory() as tmp:
                markdown = VALID_MARKDOWN.replace("category: Tech", f"category: {category}")
                document = load_document(self._write_document(Path(tmp), markdown))
                report = validate_document(document, reviewer_approved=True)
                self.assertNotIn(
                    "unsupported_category",
                    {issue.code for issue in report.errors},
                )

    def test_validation_rejects_category_outside_hunt_news_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            markdown = VALID_MARKDOWN.replace("category: Tech", "category: 스포츠")
            document = load_document(self._write_document(Path(tmp), markdown))
            report = validate_document(document, reviewer_approved=True)
            self.assertIn(
                "unsupported_category",
                {issue.code for issue in report.errors},
            )

    def test_publisher_does_not_create_a_missing_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = FakeWordPressClient()
            client.categories.pop("Tech")
            publisher = DraftPublisher(client, audit_log=root / "publisher-audit.jsonl")

            result = publisher.publish_file(
                self._write_document(root),
                reviewer_approved=True,
            )

            self.assertEqual(result.status, "Failed")
            self.assertEqual(client.create_category_calls, [])

    def test_schedule_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_MARKDOWN.replace(
                "publish_mode: draft", "publish_mode: schedule"
            )
            document = load_document(self._write_document(Path(tmp), text))
            report = validate_document(document, reviewer_approved=True)
            self.assertFalse(report.passed)
            self.assertIn(
                "unsupported_publish_mode",
                {issue.code for issue in report.errors},
            )

    def test_missing_publish_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_MARKDOWN.replace("publish_mode: draft\n", "")
            document = load_document(self._write_document(Path(tmp), text))
            report = validate_document(document, reviewer_approved=True)
            self.assertFalse(report.passed)
            self.assertIn(
                "missing_publish_mode",
                {issue.code for issue in report.errors},
            )

    def test_successful_draft_uses_draft_status_and_audit_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = FakeWordPressClient()
            audit_log = root / "publisher-audit.jsonl"
            publisher = DraftPublisher(client, audit_log=audit_log)
            result = publisher.publish_file(
                self._write_document(root),
                reviewer_approved=True,
            )

            self.assertEqual(result.status, "Success")
            self.assertEqual(result.action, "Draft")
            self.assertEqual(result.post_id, 123)
            self.assertEqual(
                result.draft_url,
                "https://huntlab.app/wp-admin/post.php?post=123&action=edit",
            )
            self.assertIsNotNone(client.created_payload)
            self.assertEqual(client.created_payload["status"], "draft")
            self.assertEqual(
                client.created_payload["categories"],
                [client.categories["Tech"]],
            )
            self.assertEqual(
                set(client.categories),
                EDITOR_CATEGORIES,
            )
            self.assertEqual(client.create_category_calls, [])
            self.assertEqual(len(client.created_payload["tags"]), 3)
            self.assertIn("<h2>", client.created_payload["content"])

            events = [
                json.loads(line)
                for line in audit_log.read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(any(event.get("event") == "draft_created" for event in events))
            self.assertFalse(
                any("password" in json.dumps(event).lower() for event in events)
            )

    def test_validation_failure_does_not_call_wordpress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = FakeWordPressClient()
            publisher = DraftPublisher(client, audit_log=root / "audit.jsonl")
            invalid = VALID_MARKDOWN.replace(
                "  - Automation\n", ""
            )
            result = publisher.publish_file(
                self._write_document(root, invalid),
                reviewer_approved=True,
            )
            self.assertEqual(result.status, "Failed")
            self.assertIsNone(client.created_payload)

    def test_validation_rejects_more_than_four_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_MARKDOWN.replace(
                "  - Automation\n",
                "  - Automation\n  - Security\n  - Performance\n",
            )
            document = load_document(self._write_document(Path(tmp), text))
            report = validate_document(document, reviewer_approved=True)
            self.assertFalse(report.passed)
            self.assertIn(
                "invalid_tag_count",
                {issue.code for issue in report.errors},
            )

    def test_validation_allows_explicit_secret_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_MARKDOWN + (
                "\n```http\n"
                "Authorization: Bearer {API_TOKEN}\n"
                "```\n"
            )
            document = load_document(self._write_document(Path(tmp), text))
            report = validate_document(document, reviewer_approved=True)
            self.assertTrue(report.passed)

    def test_validation_ignores_shell_comments_inside_fenced_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_MARKDOWN.replace(
                "### 검증 항목",
                "```bash\n"
                "# 1) predicate descriptor 조회\n"
                "# 2) statement 원문 조회\n"
                "```\n\n"
                "### 검증 항목",
            )
            document = load_document(self._write_document(Path(tmp), text))
            report = validate_document(document, reviewer_approved=True)
            self.assertTrue(report.passed)
            self.assertEqual(report.checks["heading_structure"], "passed")

    def test_validation_still_rejects_h1_outside_fenced_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_MARKDOWN + (
                "\n```bash\n"
                "# harmless shell comment\n"
                "```\n\n"
                "# 실제 본문 H1\n"
            )
            document = load_document(self._write_document(Path(tmp), text))
            report = validate_document(document, reviewer_approved=True)
            self.assertFalse(report.passed)
            self.assertIn(
                "body_h1_not_allowed",
                {issue.code for issue in report.errors},
            )

    def test_validation_rejects_realistic_bearer_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_MARKDOWN + (
                "\n```http\n"
                "Authorization: Bearer abcdefghijklmnop1234567890\n"
                "```\n"
            )
            document = load_document(self._write_document(Path(tmp), text))
            report = validate_document(document, reviewer_approved=True)
            self.assertFalse(report.passed)
            self.assertIn(
                "possible_secret_exposure",
                {issue.code for issue in report.errors},
            )

    def test_validation_allows_typescript_secret_type_declaration(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_MARKDOWN + (
                "\n```ts\n"
                "interface Env { API_KEY: string; }\n"
                "```\n"
            )
            document = load_document(self._write_document(Path(tmp), text))
            report = validate_document(document, reviewer_approved=True)
            self.assertTrue(report.passed)

    def test_local_body_image_is_uploaded_and_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_dir = root / "images"
            image_dir.mkdir()
            (image_dir / "diagram.png").write_bytes(b"fake-png")
            text = VALID_MARKDOWN + (
                "\n![Publisher 처리 흐름 다이어그램](./images/diagram.png)\n"
            )
            client = FakeWordPressClient()
            publisher = DraftPublisher(client, audit_log=root / "audit.jsonl")

            result = publisher.publish_file(
                self._write_document(root, text),
                reviewer_approved=True,
            )

            self.assertEqual(result.status, "Success")
            self.assertIsNotNone(client.created_payload)
            content = client.created_payload["content"]
            self.assertIn(
                "https://huntlab.app/wp-content/uploads/diagram.png",
                content,
            )
            self.assertNotIn("./images/diagram.png", content)

    def test_publish_requires_matching_reviewer_hash_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = VALID_MARKDOWN.replace(
                "publish_mode: draft\n",
                "publish_mode: publish\n"
                "run_id: run-1\n"
                "topic_id: topic-1\n"
                "source_id: huntlab:run-1:topic-1\n",
            )
            path = self._write_document(root, text)
            digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
            review = root / "review.md"
            review.write_text(
                f"APPROVED\nrun-1\ntopic-1\n{digest}\n",
                encoding="utf-8",
            )
            client = FakeWordPressClient()
            result = DraftPublisher(
                client,
                audit_log=root / "audit.jsonl",
            ).publish_file(
                path,
                reviewer_approved=True,
                review_path=review,
                expected_identity={
                    "run_id": "run-1",
                    "topic_id": "topic-1",
                    "source_id": "huntlab:run-1:topic-1",
                    "category": "Tech",
                },
            )

            self.assertEqual(result.status, "Success")
            self.assertEqual(result.action, "Publish")
            self.assertEqual(result.published_url, "https://huntlab.app/?p=123")
            self.assertEqual(client.created_payload["status"], "publish")

    def test_approved_existing_post_id_updates_matching_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = VALID_MARKDOWN.replace(
                "publish_mode: draft\n",
                "publish_mode: publish\n"
                "run_id: run-1\n"
                "topic_id: topic-1\n"
                "source_id: huntlab:run-1:topic-1\n"
                "existing_post_id: 195\n",
            )
            path = self._write_document(root, text)
            digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
            review = root / "review.md"
            review.write_text(
                f"APPROVED\nrun-1\ntopic-1\n{digest}\n",
                encoding="utf-8",
            )
            client = FakeWordPressClient()
            client.posts[195] = {
                "id": 195,
                "title": {"rendered": "HuntLab Publisher 테스트"},
                "slug": "huntlab-publisher-test",
                "status": "publish",
            }

            result = DraftPublisher(
                client,
                audit_log=root / "audit.jsonl",
            ).publish_file(
                path,
                reviewer_approved=True,
                review_path=review,
                expected_identity={
                    "run_id": "run-1",
                    "topic_id": "topic-1",
                    "source_id": "huntlab:run-1:topic-1",
                    "category": "Tech",
                },
            )

            self.assertEqual(result.status, "Success")
            self.assertEqual(result.action, "Update")
            self.assertEqual(result.post_id, 195)
            self.assertEqual(result.published_url, "https://huntlab.app/?p=195")

    def test_update_reuses_exact_existing_featured_and_body_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "thumbnail.png").write_bytes(b"featured")
            (root / "body-1.png").write_bytes(b"body")
            text = VALID_MARKDOWN.replace(
                "publish_mode: draft\n",
                "publish_mode: publish\n"
                "run_id: run-1\n"
                "topic_id: topic-1\n"
                "source_id: huntlab:run-1:topic-1\n"
                "existing_post_id: 195\n"
                "featured_image: thumbnail.png\n"
                "featured_image_alt: 격리 트리 구조\n",
            ) + "\n![수도 이상 탐지 결과](body-1.png)\n"
            path = self._write_document(root, text)
            digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
            review = root / "review.md"
            review.write_text(
                f"APPROVED\nrun-1\ntopic-1\n{digest}\n",
                encoding="utf-8",
            )
            client = FakeWordPressClient()
            body_url = "https://huntlab.app/wp-content/uploads/body-1-10.webp"
            client.posts[195] = {
                "id": 195,
                "title": {"rendered": "HuntLab Publisher 테스트"},
                "slug": "huntlab-publisher-test",
                "status": "publish",
                "featured_media": 258,
                "content": {
                    "rendered": (
                        '<p><img class="wp-image-259" '
                        'src="https://huntlab.app/wp-content/uploads/body-1-10.webp" '
                        'alt="수도 이상 탐지 결과"></p>'
                    )
                },
            }
            client.media[258] = {
                "id": 258,
                "source_url": "https://huntlab.app/wp-content/uploads/thumbnail-10.webp",
                "alt_text": "격리 트리 구조",
            }
            client.media[259] = {
                "id": 259,
                "source_url": body_url,
                "alt_text": "수도 이상 탐지 결과",
            }

            result = DraftPublisher(
                client,
                audit_log=root / "audit.jsonl",
            ).publish_file(
                path,
                reviewer_approved=True,
                review_path=review,
                expected_identity={
                    "run_id": "run-1",
                    "topic_id": "topic-1",
                    "source_id": "huntlab:run-1:topic-1",
                    "category": "Tech",
                },
            )

            self.assertEqual(result.status, "Success")
            self.assertEqual(client.upload_calls, [])
            self.assertEqual(client.created_payload["featured_media"], 258)
            self.assertIn(body_url, client.created_payload["content"])
            self.assertEqual(result.publish_summary["featured_media_id"], 258)
            self.assertEqual(result.publish_summary["body_media_ids"], [259])
            events = [
                json.loads(line)
                for line in (root / "audit.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertTrue(
                any(event.get("event") == "featured_media_reused" for event in events)
            )
            self.assertTrue(
                any(event.get("event") == "body_media_reused" for event in events)
            )

    def test_new_post_still_uploads_featured_and_body_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "featured.png").write_bytes(b"featured")
            (root / "body.png").write_bytes(b"body")
            text = VALID_MARKDOWN.replace(
                "meta_description: HuntLab Publisher의 Draft 생성 검증 문서입니다.\n",
                "meta_description: HuntLab Publisher의 Draft 생성 검증 문서입니다.\n"
                "featured_image: featured.png\n"
                "featured_image_alt: 격리 트리 구조\n",
            ) + "\n![수도 이상 탐지 결과](body.png)\n"
            client = FakeWordPressClient()

            result = DraftPublisher(
                client,
                audit_log=root / "audit.jsonl",
            ).publish_file(
                self._write_document(root, text),
                reviewer_approved=True,
            )

            self.assertEqual(result.status, "Success")
            self.assertEqual(len(client.upload_calls), 2)
            self.assertEqual(result.publish_summary["featured_media_id"], 99)
            self.assertEqual(result.publish_summary["body_media_ids"], [100])

    def test_update_uploads_when_media_suffix_is_not_numeric(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "thumbnail.png").write_bytes(b"featured")
            (root / "body-1.png").write_bytes(b"body")
            text = VALID_MARKDOWN.replace(
                "publish_mode: draft\n",
                "publish_mode: publish\n"
                "run_id: run-1\n"
                "topic_id: topic-1\n"
                "source_id: huntlab:run-1:topic-1\n"
                "existing_post_id: 195\n"
                "featured_image: thumbnail.png\n"
                "featured_image_alt: 격리 트리 구조\n",
            ) + "\n![수도 이상 탐지 결과](body-1.png)\n"
            path = self._write_document(root, text)
            digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
            review = root / "review.md"
            review.write_text(
                f"APPROVED\nrun-1\ntopic-1\n{digest}\n",
                encoding="utf-8",
            )
            client = FakeWordPressClient()
            client.posts[195] = {
                "id": 195,
                "title": {"rendered": "HuntLab Publisher 테스트"},
                "slug": "huntlab-publisher-test",
                "status": "publish",
                "featured_media": 258,
                "content": {
                    "rendered": (
                        '<p><img src="https://huntlab.app/wp-content/uploads/body-1-old.webp" '
                        'alt="수도 이상 탐지 결과"></p>'
                    )
                },
            }
            client.media[258] = {
                "id": 258,
                "source_url": "https://huntlab.app/wp-content/uploads/thumbnail-copy.webp",
                "alt_text": "격리 트리 구조",
            }

            result = DraftPublisher(
                client,
                audit_log=root / "audit.jsonl",
            ).publish_file(
                path,
                reviewer_approved=True,
                review_path=review,
                expected_identity={
                    "run_id": "run-1",
                    "topic_id": "topic-1",
                    "source_id": "huntlab:run-1:topic-1",
                    "category": "Tech",
                },
            )

            self.assertEqual(result.status, "Success")
            self.assertEqual(len(client.upload_calls), 2)
            self.assertEqual(result.publish_summary["featured_media_id"], 99)
            self.assertEqual(result.publish_summary["body_media_ids"], [100])

    def test_publish_rejects_mismatched_reviewer_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = VALID_MARKDOWN.replace(
                "publish_mode: draft\n",
                "publish_mode: publish\n"
                "run_id: run-1\n"
                "topic_id: topic-1\n"
                "source_id: huntlab:run-1:topic-1\n",
            )
            path = self._write_document(root, text)
            review = root / "review.md"
            review.write_text("APPROVED\nrun-1\ntopic-1\nwrong-hash\n", encoding="utf-8")
            client = FakeWordPressClient()
            result = DraftPublisher(
                client,
                audit_log=root / "audit.jsonl",
            ).publish_file(
                path,
                reviewer_approved=True,
                review_path=review,
                expected_identity={
                    "run_id": "run-1",
                    "topic_id": "topic-1",
                    "source_id": "huntlab:run-1:topic-1",
                    "category": "Tech",
                },
            )

            self.assertEqual(result.status, "Failed")
            self.assertIsNone(client.created_payload)


if __name__ == "__main__":
    unittest.main()
