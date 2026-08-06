from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_daily_pipeline import (
    PipelineError,
    Stage,
    TopicContext,
    has_successful_publish,
    make_topic_context,
    parse_topic_plan,
    planner_stage,
    read_review_decision,
    review_repair_stages,
    run_stage,
    topic_stages,
    validate_publish_contract,
    write_planner_context,
)
from scripts.retry_daily_pipeline import choose_command


class DailyPipelineIsolationTests(unittest.TestCase):
    def test_agent_subprocess_closes_stdin_for_noninteractive_runs(self):
        completed = subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout="CODEX_OK\n",
        )
        with patch(
            "scripts.run_daily_pipeline.subprocess.run",
            return_value=completed,
        ) as mocked_run:
            output = run_stage(
                "/usr/local/bin/codex",
                Stage("Smoke Agent", None, "CODEX_OK"),
                logging.getLogger("test-agent-stdin"),
                timeout_seconds=10,
            )

        self.assertEqual(output, "CODEX_OK\n")
        self.assertIs(mocked_run.call_args.kwargs["stdin"], subprocess.DEVNULL)

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

    def test_harness_routes_only_selected_content_type_guide(self):
        context = make_topic_context(
            "run-content-type",
            "이벤트 기반 아키텍처 선택 기준",
            category="System Architecture",
            content_type="concept_architecture",
        )
        stages = topic_stages(context)

        for stage in stages[:2]:
            self.assertIn("concept-architecture.md", stage.prompt)
            self.assertNotIn("ai-ml-experiment.md", stage.prompt)
            self.assertNotIn("build-log-operations.md", stage.prompt)
        writer = next(stage for stage in stages if stage.name == "Writer Agent")
        reviewer = next(stage for stage in stages if stage.name == "Reviewer Agent")
        self.assertIn("content_type='concept_architecture'", writer.prompt)
        self.assertIn("content_type='concept_architecture'", reviewer.prompt)
        self.assertIn("concept-architecture.md", reviewer.prompt)
        publisher = next(stage for stage in stages if stage.name == "Publisher Agent")
        self.assertNotIn("guides/content-types/", publisher.prompt)

    def test_legacy_topic_plan_infers_content_type_from_category(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "topics.md"
            candidates = []
            for index in range(1, 36):
                title = f"AI 후보 {index}"
                candidates.append(
                    f"## {index}. {title}\n\n"
                    f"- title: {title}\n"
                    "- category: AI\n"
                    "- tags: AI, Test, HuntLab\n"
                    "- score: 80/90\n"
                    "- score_breakdown: 계약 검증\n"
                    "- reason: 하위 호환 검증\n"
                    "- evergreen: 중간\n"
                    f"- primary_keyword: {title}\n"
                    "- search_intent: 개념 확인\n"
                    "- research_focus: 공식 자료\n"
                    "- recommended_images: 구조도\n"
                    "- duplicate_check: 중복 없음\n"
                    "- internal_link_candidates: 없음\n"
                    "- topic_cluster: AI\n"
                    "- pillar_candidate: 없음\n"
                    "- problem_origin: official_change\n"
                    "- editorial_thesis: 하위 호환을 검증한다\n"
                    "- chosen_focus: content_type 추론\n"
                    "- rejected_angle: 발행 동작은 제외\n"
                    "- structure_mode: decision_memo\n"
                )
            top10 = "\n".join(f"{index}. AI 후보 {index}" for index in range(1, 11))
            path.write_text(
                "# Topic Candidates\n\n"
                + "\n".join(candidates)
                + "\n## TOP10\n\n"
                + top10
                + "\n\n## TOP2\n\n1. AI 후보 1\n2. AI 후보 2\n",
                encoding="utf-8",
            )

            plans = parse_topic_plan(path)
            self.assertEqual(
                [plan["content_type"] for plan in plans],
                ["ai_ml_experiment", "ai_ml_experiment"],
            )

    def test_planner_prioritizes_ml_thinking_without_forcing_top2(self):
        planner = planner_stage("", "run-ml-thinking", Path("/tmp/topics.md"))

        self.assertIn("ML적 사고력", planner.prompt)
        self.assertIn("문제 정의", planner.prompt)
        self.assertIn("평가지표", planner.prompt)
        self.assertIn("실제 적용 판단", planner.prompt)
        self.assertIn("TOP2 의무 할당은 두지 말고", planner.prompt)
        self.assertIn("후속 관점 또는 Refresh", planner.prompt)
        self.assertIn("demand_signal_source", planner.prompt)
        self.assertIn("observed_problem_phrase", planner.prompt)
        self.assertIn("user_action", planner.prompt)
        self.assertIn("확인하지 못한 장애를 창작하지 말고", planner.prompt)

    def test_planner_uses_velog_only_as_a_guarded_discovery_signal(self):
        planner = planner_stage("", "run-velog-signal", Path("/tmp/topics.md"))

        self.assertIn("Velog 공개 트렌딩(https://velog.io/)", planner.prompt)
        self.assertIn("한국 개발자 관심사의 보조 신호", planner.prompt)
        self.assertIn("제목이나 구성을 복제하지 말고", planner.prompt)
        self.assertIn("Velog 인기만으로", planner.prompt)
        self.assertIn("같은 주제 흐름이 2회 이상", planner.prompt)
        self.assertIn("검색 수요 점수에 최대 1점", planner.prompt)
        self.assertIn("TOP2로 선정해 실제 발행", planner.prompt)
        self.assertIn("Search Console 관측값", planner.prompt)
        self.assertIn("공식 1차 자료", planner.prompt)
        self.assertIn("Velog 신호 없음으로 계속 진행", planner.prompt)

    def test_planner_broadens_ml_beyond_isolation_forest(self):
        planner = planner_stage("", "run-ml-breadth", Path("/tmp/topics.md"))

        self.assertIn("Isolation Forest 한 알고리즘에 편중하지 말고", planner.prompt)
        self.assertIn("군집화", planner.prompt)
        self.assertIn("차원 축소", planner.prompt)
        self.assertIn("추천", planner.prompt)
        self.assertIn("시계열", planner.prompt)
        self.assertIn("신경망", planner.prompt)
        self.assertIn("베이스라인과 대안을 비교", planner.prompt)
        self.assertIn("TOP2 의무 할당은 두지 말고", planner.prompt)

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
                    "- problem_origin: real_project\n"
                    "- editorial_thesis: 기술 문제를 실제 근거로 해결한다\n"
                    "- chosen_focus: 구현 방법\n"
                    "- rejected_angle: 일반론은 제외\n"
                    "- structure_mode: problem_first\n"
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
                    "- problem_origin: observed_search_question\n"
                    "- editorial_thesis: 검색 의도와 제목을 맞춘다\n"
                    "- chosen_focus: primary keyword\n"
                    "- rejected_angle: 주변 키워드는 제외\n"
                    "- structure_mode: field_note\n"
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

    def test_all_posts_keep_toc_and_require_grounded_quick_summary(self):
        context = make_topic_context(
            "run-quick-view",
            "Transactional Outbox 패턴",
            category="System Architecture",
        )
        stages = topic_stages(context)
        writer = next(stage for stage in stages if stage.name == "Writer Agent")
        reviewer = next(stage for stage in stages if stage.name == "Reviewer Agent")

        self.assertIn("`## 20초 핵심 요약`", writer.prompt)
        self.assertIn("`무엇`, `왜`, `어떻게`", writer.prompt)
        self.assertIn("기존 `한눈에 보기` 자동 목차", writer.prompt)
        self.assertIn("삭제하거나 대체하지 마세요", writer.prompt)
        self.assertIn("research.md에 없는 사실", writer.prompt)
        self.assertIn("REJECT하세요", reviewer.prompt)

    def test_non_technical_posts_also_require_quick_summary(self):
        context = make_topic_context(
            "run-no-quick-view",
            "공식 통계 해설",
            category="Economy",
        )
        writer = next(
            stage for stage in topic_stages(context) if stage.name == "Writer Agent"
        )

        self.assertIn("`## 20초 핵심 요약`", writer.prompt)
        self.assertIn("`무엇`, `왜`, `어떻게`", writer.prompt)

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
                    "original_value_plan": "격리 전후 동작 비교",
                    "evidence_plan": "command_and_output과 failed_attempt 검증",
                    "sources": "https://example.com/source",
                    "problem_origin": "real_project",
                    "editorial_thesis": "격리는 권한 경계로 검증해야 한다",
                    "chosen_focus": "egress 차단",
                    "rejected_angle": "제품 기능 나열은 제외",
                    "structure_mode": "problem_first",
                },
            )

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], context.run_id)
            self.assertEqual(payload["topic_id"], context.topic_id)
            self.assertEqual(payload["content_type"], "tutorial_troubleshooting")
            self.assertEqual(
                payload["duplicate_check"],
                "공개 글과 Draft에 동일 검색 의도 없음",
            )
            self.assertEqual(payload["original_value_plan"], "격리 전후 동작 비교")
            self.assertIn("command_and_output", payload["evidence_plan"])
            self.assertEqual(payload["problem_origin"], "real_project")
            self.assertEqual(payload["structure_mode"], "problem_first")

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
                "## 20초 핵심 요약\n\n"
                "- **무엇:** Docker 보안 업데이트\n"
                "- **왜:** 취약점 대응\n"
                "- **어떻게:** 검증 후 적용\n\n"
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

    def test_review_decision_uses_explicit_status_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run-review" / "topic-review"
            directory.mkdir(parents=True)
            context = TopicContext(
                title="검토 상태 판정",
                run_id="run-review",
                topic_id="topic-review",
                directory=directory,
            )
            review = directory / "review.md"
            review.write_text(
                "# Review Result\n\n- status: `REJECTED`\n\n"
                "수정 후 APPROVED가 필요합니다.\n",
                encoding="utf-8",
            )

            self.assertEqual(read_review_decision(context), "REJECTED")

    def test_repair_cycle_reuses_existing_agents_and_preserves_reviewer(self):
        context = make_topic_context("run-repair", "검증 근거 보정")
        stages = review_repair_stages(context, attempt=1)

        self.assertEqual(
            [stage.name for stage in stages],
            [
                "Research Agent",
                "Writer Agent",
                "Image Maker Agent",
                "Assembler Agent",
                "Reviewer Agent",
            ],
        )
        self.assertTrue(all("review.md" in stage.prompt for stage in stages))
        self.assertTrue(all("실제 원문" in stage.prompt for stage in stages))
        self.assertNotIn("Publisher Agent", [stage.name for stage in stages])

    def test_publish_contract_reports_explicit_reviewer_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run-rejected" / "topic-rejected"
            directory.mkdir(parents=True)
            context = TopicContext(
                title="거절된 글",
                run_id="run-rejected",
                topic_id="topic-rejected",
                directory=directory,
                category="Tech",
                tags=("Review",),
            )
            (directory / "publish.md").write_text(
                "---\n"
                'title: "거절된 글"\n'
                'run_id: "run-rejected"\n'
                'topic_id: "topic-rejected"\n'
                'source_id: "huntlab:run-rejected:topic-rejected"\n'
                'publish_mode: "publish"\n'
                'category: "Tech"\n'
                'featured_image: "./images/thumbnail.png"\n'
                'featured_image_alt: "거절된 글 대표 이미지"\n'
                "tags:\n"
                '  - "Review"\n'
                "---\n\n## 본문\n",
                encoding="utf-8",
            )
            (directory / "images").mkdir()
            (directory / "images/thumbnail.png").write_bytes(b"png")
            (directory / "review.md").write_text(
                "# Review Result\n\n- status: `REJECTED`\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(PipelineError, "Reviewer가 발행을 거절"):
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
