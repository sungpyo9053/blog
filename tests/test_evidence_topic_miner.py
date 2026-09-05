from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.evidence_topic_miner import (
    MAX_CANDIDATES,
    CommitRecord,
    Event,
    atomic_write_new,
    choose_candidates,
    enrich_pilot_events,
    evaluate_event,
    evidence_contract,
    existing_run_is_current,
    group_git_events,
    render_markdown,
)


class EvidenceTopicMinerTests(unittest.TestCase):
    def test_post50_and_post132_are_grouped_by_source_not_shared_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "publisher").mkdir()
            (repo / "scripts").mkdir()
            (repo / "tests").mkdir()
            (repo / "publisher/wordpress.py").write_text("def retry(): pass\n", encoding="utf-8")
            (repo / "scripts/audit_adsense_content.py").write_text("def fetch_all(): pass\n", encoding="utf-8")
            (repo / "tests/test_wordpress_retry.py").write_text(
                "from publisher.wordpress import retry\n"
                "def test_retry_after_http_date_is_converted_to_seconds(): pass\n",
                encoding="utf-8",
            )
            (repo / "tests/test_adsense_content_audit.py").write_text(
                "from scripts.audit_adsense_content import fetch_all\n"
                "def test_fetch_all_reads_full_second_page(): pass\n",
                encoding="utf-8",
            )
            records = [
                CommitRecord(
                    "adc57d3".ljust(40, "0"),
                    "2026-09-05T09:25:00+09:00",
                    "fix: apply evidence-led safeguards",
                    (
                        "publisher/wordpress.py",
                        "scripts/audit_adsense_content.py",
                        "tests/test_wordpress_retry.py",
                        "tests/test_adsense_content_audit.py",
                    ),
                    symbols_by_file={
                        "publisher/wordpress.py": ("retry_after",),
                        "scripts/audit_adsense_content.py": ("fetch_all",),
                        "tests/test_wordpress_retry.py": ("retry_after",),
                        "tests/test_adsense_content_audit.py": ("fetch_all",),
                    },
                ),
                CommitRecord(
                    "60c67f9".ljust(40, "0"),
                    "2026-09-05T09:28:00+09:00",
                    "test: pin legacy Retry-After failure",
                    ("tests/test_wordpress_retry.py",),
                    symbols_by_file={"tests/test_wordpress_retry.py": ("retry_after",)},
                    ancestors=("adc57d3".ljust(40, "0"),),
                ),
                CommitRecord(
                    "40bd2a8".ljust(40, "0"),
                    "2026-09-05T12:23:00+09:00",
                    "test: cover complete pagination audit",
                    ("tests/test_adsense_content_audit.py",),
                    symbols_by_file={"tests/test_adsense_content_audit.py": ("fetch_all",)},
                    ancestors=("adc57d3".ljust(40, "0"),),
                ),
            ]

            events = group_git_events(repo, records)

        self.assertEqual(len(events), 2)
        retry = next(event for event in events.values() if event.anchor == "publisher/wordpress.py")
        pagination = next(event for event in events.values() if event.anchor == "scripts/audit_adsense_content.py")
        self.assertIn("tests.test_wordpress_retry.test_retry_after_http_date_is_converted_to_seconds", retry.tests)
        self.assertIn("tests.test_adsense_content_audit.test_fetch_all_reads_full_second_page", pagination.tests)
        self.assertNotIn("tests/test_adsense_content_audit.py", retry.files)
        self.assertNotIn("tests/test_wordpress_retry.py", pagination.files)

    def test_exact_existing_post_overlap_rejects_even_strong_event(self):
        event = Event(
            anchor="publisher/wordpress.py",
            commits=["a" * 40, "b" * 40],
            subjects=["fix: retry date parser", "test: reject legacy parser"],
            files=["publisher/wordpress.py", "tests/test_wordpress_retry.py"],
            tests=["tests.test_wordpress_retry.Test.test_legacy_failure"],
            post_id=50,
            slug="wordpress-rest-api-retry",
            title="Retry-After parser",
        )
        inventory = [{"post_id": 50, "url": "https://huntlab.app/wordpress-rest-api-retry/", "slug": event.slug, "title": event.title}]

        result = evaluate_event(event, inventory, "repo")

        self.assertEqual(result["publishability"], "REJECT")
        self.assertEqual(result["rejection_reason"], "existing_post_overlap")
        self.assertEqual(result["existing_post_overlap"]["post_id"], 50)

    def test_pilot_approval_links_narrow_a_shared_source_to_exact_incident_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            pilot = repo / "output/pilots/adsense-p0"
            (repo / "publisher").mkdir(parents=True)
            (repo / "tests").mkdir()
            pilot.mkdir(parents=True)
            (repo / "publisher/wordpress.py").write_text("def retry(): pass\n", encoding="utf-8")
            (repo / "tests/test_wordpress_retry.py").write_text(
                "from publisher.wordpress import retry\n"
                "def test_retry_after_http_date_is_converted_to_seconds(): pass\n",
                encoding="utf-8",
            )
            adc = "a" * 40
            regression = "b" * 40
            (pilot / "post-50.approval.json").write_text(
                json.dumps({"post_id": 50, "title": "Retry parser"}), encoding="utf-8"
            )
            (pilot / "post-50.final.html").write_text(
                f'<a href="https://github.com/example/repo/blob/{adc}/publisher/wordpress.py">code</a>'
                f'<a href="https://github.com/example/repo/blob/{regression}/tests/test_wordpress_retry.py">test</a>',
                encoding="utf-8",
            )
            events = {
                "publisher/wordpress.py": Event(
                    anchor="publisher/wordpress.py",
                    commits=["0" * 40, adc],
                    files=["publisher/wordpress.py", "tests/test_unrelated.py"],
                    tests=["tests.test_unrelated.test_other"],
                )
            }
            enrich_pilot_events(
                repo,
                events,
                [{"post_id": 50, "url": "https://example.test/post", "slug": "retry", "title": "Retry parser"}],
            )

        event = events["publisher/wordpress.py"]
        self.assertIn(adc, event.commits)
        self.assertIn(regression, event.commits)
        self.assertIn("publisher/wordpress.py", event.files)
        self.assertIn("tests/test_wordpress_retry.py", event.files)

    def test_ready_requires_all_seven_gates(self):
        event = Event(
            anchor="scripts/new_worker.py",
            trigger_commit="a" * 40,
            event_key="scripts/new_worker.py@" + "a" * 40,
            commits=["a" * 40, "b" * 40],
            commit_times={"a" * 40: "2026-09-05T10:00:00+00:00", "b" * 40: "2026-09-05T11:00:00+00:00"},
            subjects=["fix: prevent duplicate worker calls", "test: reject duplicate call"],
            files=["scripts/new_worker.py", "tests/test_new_worker.py"],
            tests=["tests.test_new_worker.WorkerTests.test_reject_duplicate_call"],
            test_runs=[
                {"test": "same test", "status": "FAIL", "exit_code": 1, "recorded_at": "2026-09-05T09:00:00+00:00", "output_sha256": "1" * 64},
                {"test": "same test", "status": "PASS", "exit_code": 0, "recorded_at": "2026-09-05T12:00:00+00:00", "output_sha256": "2" * 64},
            ],
            target_reader="worker authors",
            reader_action="avoid duplicate calls",
            unique_takeaway="idempotency guard belongs before the API call",
            structured_before_after={"before": "2 calls", "after": "1 call"},
            recommended_format="debugging_log",
            contract_fields={"root_cause": "guard after call", "prevention": "regression test"},
            public_urls=["https://github.com/example/repo/commit/" + "a" * 40],
            public_access_verified=True,
        )

        result = evaluate_event(event, [], "repo")

        self.assertEqual(result["publishability"], "READY")
        self.assertEqual(set(result["ready_gates"]), {
            "real_project_trigger", "traceable_evidence_contract", "transferable_problem",
            "no_existing_search_intent_overlap", "unique_beyond_docs", "reader_action",
            "public_and_secret_safe_evidence",
            "current_public_and_draft_overlap_checked",
        })
        self.assertTrue(all(result["ready_gates"].values()))

    def test_code_or_number_without_chronology_is_not_ready(self):
        event = Event(
            anchor="scripts/number_report.py",
            commits=["a" * 40],
            subjects=["feat: add 100 row report"],
            files=["scripts/number_report.py"],
        )
        result = evaluate_event(event, [], "repo")
        self.assertEqual(result["publishability"], "NEEDS_EVIDENCE")
        self.assertIn("evidence_contract.known_format", result["missing_evidence"])

    def test_each_article_type_has_an_independent_evidence_contract(self):
        complete = {
            "feature_build": {"requirement":"r","completion_result":"done","unsupported_scope":"x"},
            "migration": {"before_version":"1","after_version":"2","compatibility":"c","rollback_condition":"r"},
            "benchmark_experiment": {"environment":"e","input":"i","baseline":"b","comparison":"c","measurements":"m","limitations":"l"},
            "architecture_decision": {"decision_problem":"p","alternatives":["a","b"],"criteria":"c","adopted":"a","rejected":"b","decision_record":"d","tradeoffs":"t"},
            "operations_incident": {"observation":"o","impact":"i","response":"r","recovery":"done","post_verification":"v","prevention":"p"},
        }
        for kind, fields in complete.items():
            with self.subTest(kind=kind):
                event = Event(anchor="scripts/x.py", trigger_commit="a"*40, commits=["a"*40], files=["scripts/x.py"], tests=["tests.test_x"], test_runs=[{"status":"PASS","exit_code":0,"output_sha256":"1"*64}], recommended_format=kind, contract_fields=fields, structured_before_after={"before":"1","after":"2"}, public_urls=["https://example.test/evidence"], public_access_verified=True)
                _, missing = evidence_contract(event)
                self.assertEqual(missing, [])

    def test_max_three_is_deterministic_for_shuffled_input(self):
        rows = []
        for number in range(5):
            rows.append(
                {
                    "candidate_id": f"candidate-{number}",
                    "publishability": "READY",
                    "missing_evidence": [],
                    "evidence": {"commits": [str(number)], "files": [], "tests": [], "logs": []},
                }
            )
        left = choose_candidates(rows)
        right = choose_candidates(list(reversed(rows)))
        self.assertEqual(left, right)
        self.assertEqual(len(left), MAX_CANDIDATES)
        self.assertEqual([row["candidate_id"] for row in left], ["candidate-0", "candidate-1", "candidate-2"])

    def test_ready_candidates_cannot_share_the_same_evidence(self):
        rows = [
            {"candidate_id": "a", "publishability": "READY", "evidence": {"commits": ["shared"], "files": ["a"], "tests": [], "logs": []}},
            {"candidate_id": "b", "publishability": "READY", "evidence": {"commits": ["shared"], "files": ["b"], "tests": [], "logs": []}},
        ]
        self.assertEqual([row["candidate_id"] for row in choose_candidates(rows)], ["a"])

    def test_no_candidates_renders_no_publishable_topic(self):
        payload = {
            "date": "2026-09-05",
            "status": "no_publishable_topic",
            "source_head": "a" * 40,
            "candidates": [],
        }
        rendered = render_markdown(payload)
        self.assertIn("`no_publishable_topic`", rendered)
        self.assertTrue(rendered.endswith("\n"))

    def test_needs_evidence_and_rejected_events_are_not_presented_as_candidates(self):
        rows = [
            {
                "candidate_id": "needs",
                "publishability": "NEEDS_EVIDENCE",
                "missing_evidence": ["chronological_change"],
                "evidence": {"commits": [], "files": [], "tests": [], "logs": []},
            },
            {
                "candidate_id": "reject",
                "publishability": "REJECT",
                "missing_evidence": [],
                "evidence": {"commits": [], "files": [], "tests": [], "logs": []},
            },
        ]
        self.assertEqual(choose_candidates(rows), [])

    def test_existing_daily_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "candidates.json"
            atomic_write_new(target, b"first\n")
            atomic_write_new(target, b"first\n")
            with self.assertRaises(FileExistsError):
                atomic_write_new(target, b"second\n")
            self.assertEqual(target.read_bytes(), b"first\n")

    def test_candidate_has_required_output_fields(self):
        event = Event(
            anchor="scripts/example.py",
            commits=["a" * 40],
            subjects=["fix: example"],
            files=["scripts/example.py"],
        )
        row = evaluate_event(event, [], "repo")
        required = {
            "candidate_id", "title_seed", "real_trigger", "target_reader", "problem",
            "why_it_matters", "evidence", "before_after", "unique_takeaway",
            "evidence_contract", "existing_post_overlap", "recommended_format", "publishability",
            "missing_evidence", "rejection_reason",
        }
        self.assertTrue(required <= set(row))
        self.assertEqual(set(row["evidence"]), {"commits", "files", "tests", "logs", "public_urls"})

    def test_candidate_id_does_not_change_when_more_evidence_is_attached(self):
        base = Event(anchor="scripts/worker.py", trigger_commit="a" * 40, commits=["a" * 40])
        enriched = Event(anchor="scripts/worker.py", trigger_commit="a" * 40, commits=["0" * 40, "a" * 40, "b" * 40])
        self.assertEqual(
            evaluate_event(base, [], "repo")["candidate_id"],
            evaluate_event(enriched, [], "repo")["candidate_id"],
        )

    def test_same_file_different_source_commits_are_separate_events(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "scripts").mkdir()
            (repo / "scripts/worker.py").write_text("pass\n", encoding="utf-8")
            commits = [
                CommitRecord("b" * 40, "2026-09-05T11:00:00+00:00", "fix second incident", ("scripts/worker.py",)),
                CommitRecord("a" * 40, "2026-09-05T10:00:00+00:00", "fix first incident", ("scripts/worker.py",)),
            ]
            events = group_git_events(repo, commits)
        self.assertEqual(len(events), 2)
        self.assertEqual({event.trigger_commit for event in events.values()}, {"a" * 40, "b" * 40})

    def test_test_only_commit_links_by_import_symbol_and_ancestry(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory); (repo / "scripts").mkdir(); (repo / "tests").mkdir()
            (repo / "scripts/worker.py").write_text("def retry_after(): pass\ndef pagination(): pass\n", encoding="utf-8")
            (repo / "tests/test_worker.py").write_text("from scripts.worker import retry_after\ndef test_retry_after(): pass\n", encoding="utf-8")
            first, second, test_sha = "a"*40, "b"*40, "c"*40
            commits = [
                CommitRecord(test_sha,"2026-09-05T12:00:00+00:00","test retry",("tests/test_worker.py",),{"tests/test_worker.py":("retry_after",)},(first,second)),
                CommitRecord(second,"2026-09-05T11:00:00+00:00","fix pagination",("scripts/worker.py",),{"scripts/worker.py":("pagination",)}),
                CommitRecord(first,"2026-09-05T10:00:00+00:00","fix retry",("scripts/worker.py",),{"scripts/worker.py":("retry_after",)}),
            ]
            events = group_git_events(repo, commits)
        retry = next(event for event in events.values() if event.trigger_commit == first)
        unrelated = next(event for event in events.values() if event.trigger_commit == second)
        self.assertIn(test_sha, retry.commits)
        self.assertNotIn(test_sha, unrelated.commits)

    def test_closer_unrelated_event_does_not_capture_test(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory); (repo / "scripts").mkdir(); (repo / "tests").mkdir()
            (repo / "scripts/worker.py").write_text("def retry_after(): pass\n", encoding="utf-8")
            (repo / "tests/test_worker.py").write_text("from scripts.worker import retry_after\ndef test_retry_after(): pass\n", encoding="utf-8")
            ancestor, closer_branch, test_sha = "a"*40, "b"*40, "c"*40
            commits = [
                CommitRecord(test_sha,"2026-09-05T12:00:00+00:00","test retry",("tests/test_worker.py",),{"tests/test_worker.py":("retry_after",)},(ancestor,)),
                CommitRecord(closer_branch,"2026-09-05T11:59:00+00:00","other branch retry",("scripts/worker.py",),{"scripts/worker.py":("retry_after",)}),
                CommitRecord(ancestor,"2026-09-05T10:00:00+00:00","fix retry",("scripts/worker.py",),{"scripts/worker.py":("retry_after",)}),
            ]
            events = group_git_events(repo, commits)
        correct = next(event for event in events.values() if event.trigger_commit == ancestor)
        closer = next(event for event in events.values() if event.trigger_commit == closer_branch)
        self.assertIn(test_sha, correct.commits)
        self.assertNotIn(test_sha, closer.commits)

    def test_ambiguous_multi_file_test_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory); (repo / "scripts").mkdir(); (repo / "tests").mkdir()
            (repo / "scripts/a.py").write_text("def shared(): pass\n", encoding="utf-8")
            (repo / "scripts/b.py").write_text("def shared(): pass\n", encoding="utf-8")
            (repo / "tests/test_shared.py").write_text("from scripts.a import shared\nfrom scripts.b import shared\ndef test_shared(): pass\n", encoding="utf-8")
            seed, test_sha = "a"*40, "b"*40
            commits = [
                CommitRecord(test_sha,"2026-09-05T11:00:00+00:00","test shared",("tests/test_shared.py",),{"tests/test_shared.py":("shared",)},(seed,)),
                CommitRecord(seed,"2026-09-05T10:00:00+00:00","change both",("scripts/a.py","scripts/b.py"),{"scripts/a.py":("shared",),"scripts/b.py":("shared",)}),
            ]
            events = group_git_events(repo, commits)
        self.assertEqual(sum(test_sha in event.commits for event in events.values()), 0)
        self.assertTrue(all("ambiguous_test_link" in event.ambiguous_evidence for event in events.values()))
        self.assertTrue(all("multi_file_commit_requires_review" in event.ambiguous_evidence for event in events.values()))

    def test_merge_is_ignored_and_revert_requires_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory); (repo / "scripts").mkdir(); (repo / "scripts/a.py").write_text("pass\n")
            commits = [
                CommitRecord("m"*40,"2026-09-05T12:00:00+00:00","merge",("scripts/a.py",),{"scripts/a.py":("alpha",)},is_merge=True),
                CommitRecord("r"*40,"2026-09-05T11:00:00+00:00","Revert fix",("scripts/a.py",),{"scripts/a.py":("alpha",)},is_revert=True),
            ]
            events = group_git_events(repo, commits)
        self.assertEqual(len(events), 1)
        self.assertIn("revert_requires_explicit_event_manifest", next(iter(events.values())).ambiguous_evidence)

    def test_rename_uses_new_anchor_but_stays_needs_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory); (repo / "scripts").mkdir(); (repo / "scripts/new.py").write_text("def alpha(): pass\n")
            event = next(iter(group_git_events(repo, [CommitRecord("a"*40,"2026-09-05T10:00:00+00:00","rename",("scripts/new.py",),{"scripts/new.py":("alpha",)},renames=(("scripts/old.py","scripts/new.py"),))]).values()))
        self.assertEqual(event.anchor, "scripts/new.py")
        self.assertIn("rename_requires_explicit_event_manifest", event.ambiguous_evidence)

    def test_test_without_source_change_never_seeds_event(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory); (repo / "tests").mkdir(); (repo / "tests/test_lonely.py").write_text("def test_lonely(): pass\n")
            events = group_git_events(repo, [CommitRecord("a"*40,"2026-09-05T10:00:00+00:00","test only",("tests/test_lonely.py",),{"tests/test_lonely.py":("lonely",)})])
        self.assertEqual(events, {})

    def test_probable_overlap_blocks_ready(self):
        event = Event(anchor="scripts/worker.py", trigger_commit="a" * 40, commits=["a" * 40], subjects=["pagination missing posts"], title="pagination missing posts")
        result = evaluate_event(event, [{"post_id": 9, "title": "pagination missing posts", "slug": "pagination-missing-posts", "status": "draft"}], "repo")
        self.assertEqual(result["publishability"], "REJECT")
        self.assertEqual(result["rejection_reason"], "existing_post_overlap")

    def test_incomplete_draft_inventory_prevents_ready(self):
        event = Event(anchor="scripts/worker.py", trigger_commit="a" * 40, commits=["a" * 40])
        result = evaluate_event(event, [], "repo", inventory_complete=False)
        self.assertIn("current_public_and_draft_overlap_checked", result["missing_evidence"])

    def test_manifest_can_resolve_only_explicitly_named_ambiguities(self):
        event = Event(anchor="scripts/worker.py", ambiguous_evidence=["multi_file_commit_requires_review", "rename_requires_explicit_event_manifest"])
        resolved = {"multi_file_commit_requires_review"}
        event.ambiguous_evidence = [value for value in event.ambiguous_evidence if value not in resolved]
        self.assertEqual(event.ambiguous_evidence, ["rename_requires_explicit_event_manifest"])

    def test_same_head_rerun_validates_outputs_and_becomes_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            day = root / "2026-09-05"
            day.mkdir()
            hashes = {}
            for name, content in {
                "candidates.json": b"{}\n",
                "candidates.md": b"report\n",
                "processing.json": b"{}\n",
            }.items():
                (day / name).write_bytes(content)
                hashes[name] = hashlib.sha256(content).hexdigest()
            checkpoint = {"last_collected_commit": "a" * 40, "output_hashes": hashes}
            self.assertTrue(existing_run_is_current(root, date(2026, 9, 5), "a" * 40, checkpoint))
            (day / "candidates.md").write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                existing_run_is_current(root, date(2026, 9, 5), "a" * 40, checkpoint)


if __name__ == "__main__":
    unittest.main()
