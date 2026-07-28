from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_daily_pipeline import (
    PipelineError,
    TopicContext,
    make_topic_context,
    topic_stages,
    validate_publish_contract,
    write_planner_context,
)


class DailyPipelineIsolationTests(unittest.TestCase):
    def test_topic_ids_and_directories_are_isolated(self):
        first = make_topic_context("run-1", "Docker Engine 보안 업데이트")
        second = make_topic_context("run-1", "Python 호환성 테스트")

        self.assertNotEqual(first.topic_id, second.topic_id)
        self.assertNotEqual(first.directory, second.directory)
        self.assertEqual(first.directory.parent, second.directory.parent)
        self.assertIn("run-1", str(first.directory))

    def test_publisher_prompt_uses_only_current_topic_publish_path(self):
        context = make_topic_context("run-2", "Docker Engine 보안 업데이트")
        publisher = next(
            stage for stage in topic_stages(context) if stage.name == "Publisher Agent"
        )

        self.assertIn(str(context.directory / "publish.md"), publisher.prompt)
        self.assertIn(context.run_id, publisher.prompt)
        self.assertIn(context.topic_id, publisher.prompt)
        self.assertNotIn("AWS Lightsail", publisher.prompt)

    def test_reviewer_can_read_project_guides_without_reusing_other_outputs(self):
        context = make_topic_context("run-guides", "Python 호환성 테스트")
        reviewer = next(
            stage for stage in topic_stages(context) if stage.name == "Reviewer Agent"
        )

        self.assertIn("guides/style-guide.md", reviewer.prompt)
        self.assertIn("guides/seo-guide.md", reviewer.prompt)
        self.assertIn("guides/publisher-guide.md", reviewer.prompt)
        self.assertIn("guides/monetization-guide.md", reviewer.prompt)
        self.assertIn("planner-context.json", reviewer.prompt)
        self.assertIn("정책 문서는 읽기만", reviewer.prompt)
        self.assertIn(
            "다른 주제 디렉터리를 입력 후보로 검색하거나 재사용하지 마세요",
            reviewer.prompt,
        )

    def test_selected_planner_evidence_is_copied_into_topic_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run-planner" / "topic-test"
            directory.mkdir(parents=True)
            context = TopicContext(
                title="AI 평가 환경 권한 격리",
                run_id="run-planner",
                topic_id="topic-test",
                directory=directory,
                category="AI",
                tags=("AI", "Security", "Sandbox"),
                reason="공식 사고 원문 확인",
                research_focus="권한과 egress 검증",
            )
            path = write_planner_context(
                context,
                {
                    "title": context.title,
                    "duplicate_check": "공개 글과 Draft에 동일 검색 의도 없음",
                    "search_intent": "격리 체크리스트 확인",
                    "sources": "https://example.com/source",
                },
            )

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], context.run_id)
            self.assertEqual(payload["topic_id"], context.topic_id)
            self.assertEqual(
                payload["duplicate_check"],
                "공개 글과 Draft에 동일 검색 의도 없음",
            )

    def test_planner_context_rejects_missing_duplicate_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run-planner" / "topic-test"
            directory.mkdir(parents=True)
            context = TopicContext(
                title="중복 검사 없는 주제",
                run_id="run-planner",
                topic_id="topic-test",
                directory=directory,
            )

            with self.assertRaises(PipelineError):
                write_planner_context(context, {"title": context.title})

    def test_publish_contract_requires_matching_identity_and_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run-3" / "topic-test"
            directory.mkdir(parents=True)
            context = TopicContext(
                title="Docker Engine 보안 업데이트",
                run_id="run-3",
                topic_id="topic-test",
                directory=directory,
                category="Tech",
                tags=("Docker", "Security", "Upgrade"),
            )
            publish = directory / "publish.md"
            publish.write_text(
                "---\n"
                'title: "Docker Engine 보안 업데이트"\n'
                'run_id: "run-3"\n'
                'topic_id: "topic-test"\n'
                'source_id: "huntlab:run-3:topic-test"\n'
                'publish_mode: "publish"\n'
                'category: "Tech"\n'
                "tags:\n"
                '  - "Docker"\n'
                '  - "Security"\n'
                '  - "Upgrade"\n'
                "---\n\n"
                "## 안전한 업그레이드\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(publish.read_bytes()).hexdigest()
            (directory / "review.md").write_text(
                f"APPROVED\nrun-3\ntopic-test\n{digest}\n",
                encoding="utf-8",
            )

            self.assertEqual(validate_publish_contract(context), digest)

    def test_publish_contract_rejects_previous_topic_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run-4" / "topic-docker"
            directory.mkdir(parents=True)
            context = TopicContext(
                title="Docker Engine 보안 업데이트",
                run_id="run-4",
                topic_id="topic-docker",
                directory=directory,
                category="Tech",
                tags=("Docker", "Security", "Upgrade"),
            )
            publish = directory / "publish.md"
            publish.write_text(
                "---\n"
                'title: "AWS Lightsail로 WordPress 구축하기"\n'
                'run_id: "old-run"\n'
                'topic_id: "old-topic"\n'
                'source_id: "huntlab:old-run:old-topic"\n'
                'publish_mode: "publish"\n'
                'category: "WordPress"\n'
                "tags:\n"
                '  - "AWS"\n'
                '  - "WordPress"\n'
                '  - "Cloudflare"\n'
                "---\n\n"
                "## 이전 글\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(publish.read_bytes()).hexdigest()
            (directory / "review.md").write_text(
                f"APPROVED\nrun-4\ntopic-docker\n{digest}\n",
                encoding="utf-8",
            )

            with self.assertRaises(PipelineError):
                validate_publish_contract(context)


if __name__ == "__main__":
    unittest.main()
