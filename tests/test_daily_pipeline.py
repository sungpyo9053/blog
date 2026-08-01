from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_daily_pipeline import (
    PipelineError,
    TopicContext,
    has_successful_publish,
    make_topic_context,
    parse_topic_plan,
    planner_stage,
    topic_stages,
    validate_publish_contract,
    write_planner_context,
)
from scripts.retry_daily_pipeline import choose_command


class DailyPipelineIsolationTests(unittest.TestCase):
    def test_failed_publisher_audit_is_not_resume_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run-failed" / "topic-failed"
            directory.mkdir(parents=True)
            context = TopicContext(
                title="실패한 발행",
                run_id="run-failed",
                topic_id="topic-failed",
                directory=directory,
                category="Tech",
                tags=("API",),
            )
            (directory / "publisher-audit.jsonl").write_text(
                '{"event":"validation","status":"failed"}\n',
                encoding="utf-8",
            )
            self.assertFalse(has_successful_publish(context))

    def test_harness_explicitly_injects_analytics_report_path(self):
        planner = planner_stage("", "run-analytics", Path("/tmp/topics.md"))
        self.assertIn("Harness가 분석 리포트 경로", planner.prompt)
        self.assertIn("output/analytics/latest.md", planner.prompt)

        context = make_topic_context("run-analytics", "Python 운영 분석")
        writer = next(
            stage for stage in topic_stages(context) if stage.name == "Writer Agent"
        )
        self.assertIn("Harness가 분석 리포트 경로", writer.prompt)
        self.assertIn("output/analytics/latest.md", writer.prompt)

    def test_planner_allows_two_technical_topics_without_category_quota(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "topics.md"
            candidates = []
            for index in range(1, 36):
                title = f"기술 후보 {index}"
                candidates.append(
                    f"## {index}. {title}\n\n"
                    f"- title: {title}\n"
                    "- category: Tech\n"
                    "- tags: Tech, Python, Automation\n"
                    "- score: 80/90\n"
                    "- score_breakdown: 최신성 9; 검색 수요 9; 공식 출처 9; Evergreen 9; HuntLab 적합성 9; 기술적 깊이 9; 독창성 9; 최근 작성 여부 9; 카테고리 균형 8\n"
                    "- reason: 기술 독자의 실제 문제 해결\n"
                    "- evergreen: 높음\n"
                    f"- primary_keyword: {title}\n"
                    "- search_intent: 구현 방법 확인\n"
                    "- research_focus: 공식 문서와 재현 절차\n"
                    "- recommended_images: 구조도\n"
                    "- duplicate_check: 중복 없음\n"
                    "- internal_link_candidates: 없음\n"
                    "- topic_cluster: 기술 운영\n"
                    "- pillar_candidate: 향후 검토\n"
                )
            top10 = "\n".join(f"{index}. 기술 후보 {index}" for index in range(1, 11))
            path.write_text(
                "# Topic Candidates\n\n"
                + "\n".join(candidates)
                + "\n## TOP10\n\n"
                + top10
                + "\n\n## TOP2\n\n1. 기술 후보 1\n2. 기술 후보 2\n",
                encoding="utf-8",
            )

            selected = parse_topic_plan(path)
            self.assertEqual([item["category"] for item in selected], ["Tech", "Tech"])

    def test_selected_topic_requires_primary_keyword_in_title(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "topics.md"
            candidates = []
            for index in range(1, 36):
                title = f"기술 후보 {index}"
                primary_keyword = title if index != 1 else "검색 의도 불일치"
                candidates.append(
                    f"## {index}. {title}\n\n"
                    f"- title: {title}\n"
                    "- category: Tech\n"
                    "- tags: Tech, Python, Automation\n"
                    "- score: 80/90\n"
                    "- score_breakdown: 계약 검증\n"
                    "- reason: 기술 독자의 실제 문제 해결\n"
                    "- evergreen: 높음\n"
                    f"- primary_keyword: {primary_keyword}\n"
                    "- search_intent: 구현 방법 확인\n"
                    "- research_focus: 공식 문서와 재현 절차\n"
                    "- recommended_images: 구조도\n"
                    "- duplicate_check: 중복 없음\n"
                    "- internal_link_candidates: 없음\n"
                    "- topic_cluster: 기술 운영\n"
                    "- pillar_candidate: 향후 검토\n"
                )
            top10 = "\n".join(
                f"{index}. 기술 후보 {index}" for index in range(1, 11)
            )
            path.write_text(
                "# Topic Candidates\n\n"
                + "\n".join(candidates)
                + "\n## TOP10\n\n"
                + top10
                + "\n\n## TOP2\n\n1. 기술 후보 1\n2. 기술 후보 2\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(PipelineError, "primary_keyword"):
                parse_topic_plan(path)

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
        self.assertIn("agents/reviewer.md", reviewer.prompt)
        self.assertIn("주제 유형별 고유 가치", reviewer.prompt)
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
                'featured_image: "./images/thumbnail.png"\n'
                'featured_image_alt: "Docker 보안 업데이트 대표 이미지"\n'
                "tags:\n"
                '  - "Docker"\n'
                '  - "Security"\n'
                '  - "Upgrade"\n'
                "---\n\n"
                "## 안전한 업그레이드\n",
                encoding="utf-8",
            )
            (directory / "images").mkdir()
            (directory / "images/thumbnail.png").write_bytes(b"png")
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
                'featured_image: "./images/thumbnail.png"\n'
                'featured_image_alt: "이전 글 대표 이미지"\n'
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


class DailyRetryTests(unittest.TestCase):
    def test_noon_retry_skips_after_daily_success(self):
        self.assertIsNone(
            choose_command(
                "pipeline event=end failed=false run_id="
                "20260728T170000Z-1234567890"
            )
        )

    def test_noon_retry_starts_fresh_without_a_run(self):
        command = choose_command("pipeline event=failed reason=planner")
        self.assertIsNotNone(command)
        self.assertNotIn("--resume-run-id", command)


if __name__ == "__main__":
    unittest.main()
