import copy
import json
import os
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch, Mock

from scripts.editorial_epoch import (EpochError, digest, evidence_fingerprint, load_epoch,
                                    reject_legacy_run, reject_retired_publication, validate_candidate)
from scripts.run_evidence_deep_article import PipelineError, execute, published_today


class EditorialEpochTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name); self.root = self.repo / "runs"; self.root.mkdir()
        self.command("init", "-q"); self.command("config", "user.email", "test@example.test")
        self.command("config", "user.name", "Test")
        self.command("remote", "add", "origin", "https://example.test/huntlab.git")
        self.source = self.repo / "source.py"; self.source.write_text("value = 1\n")
        self.cutoff = self.commit("initial", "2026-09-01T00:00:00+00:00")
        self.old = "20260905T010000Z-unknown"
        directory = self.root / self.old; directory.mkdir()
        (directory / "progress.json").write_text(json.dumps({"wordpress_write_count": "unknown"}))
        inventory = {"metadata": {"site": "https://huntlab.app", "complete": True, "collected_at": "2026-09-10T00:00:00+00:00",
                                   "statuses": {s: int(s == "publish") for s in ("publish", "draft", "pending", "private", "future", "trash")}},
                     "posts": [{"id": 706, "status": "publish"}]}
        trace = self.artifact("quiescence-trace.json", {"command": "inspected executors", "processes": [], "requests": []})
        quiet = {"checked_at": "2026-09-10T00:00:00+00:00",
                 "local_executor": {"active_jobs": 0, "in_flight_requests": 0, "command": "process status", "evidence": trace},
                 "downstream_executor": {"active_jobs": 0, "in_flight_requests": 0, "command": "request queue status", "evidence": trace}}
        self.seal = {"schema_version": 1, "mode": "retired_unknown_never_retry", "sealed_at": "2026-09-10T00:01:00+00:00",
                     "starts_on": "2026-09-10", "cutoff_commit": self.cutoff,
                     "repository_identity_sha256": digest(b"https://example.test/huntlab.git"),
                     "inventory": self.artifact("inventory.json", inventory), "quiescence": self.artifact("quiet.json", quiet),
                     "retired_runs": [{"run_id": self.old, "state_sha256": {p.name: digest(p.read_bytes()) for p in directory.iterdir()}}],
                     "denied": {"candidate_ids": ["old"], "titles": ["Old WordPress issue"], "slugs": ["old-wordpress-issue"], "evidence_fingerprints": []}}
        self.save()

    def command(self, *args, env=None):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, env=env).stdout.decode().strip()

    def commit(self, message, date):
        self.command("add", "source.py")
        env = {**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        self.command("commit", "-qm", message, env=env)
        return self.command("rev-parse", "HEAD")

    def artifact(self, name, data):
        path = self.root / name; path.write_text(json.dumps(data))
        return {"path": name, "sha256": digest(path.read_bytes())}

    def save(self):
        path = self.root / "epoch.json"; path.write_text(json.dumps(self.seal))
        (self.root / "epoch-approval.json").write_text(json.dumps({"status": "RETIREMENT_APPROVED",
            "epoch_sha256": digest(path.read_bytes()), "reviewed_by": "independent reviewer", "reviewer_kind": "ai",
            "reviewed_at": "2026-09-10T00:02:00+00:00"}))

    def candidate(self):
        self.source.write_text("value = 2\n")
        sha = self.commit("new real fix", "2026-09-11T00:00:00+00:00")
        return {"candidate_id": "new", "title_seed": "New WordPress issue", "source_anchor": "source.py",
                "event_key": "source.py@" + sha, "evidence": {"commits": [sha], "files": ["source.py"],
                "public_urls": [f"https://example.test/commit/{sha}", f"https://example.test/blob/{sha}/source.py"]}}

    def test_no_epoch_is_noop_even_for_old_noncanonical_run(self):
        empty = self.repo / "empty"
        self.assertIsNone(load_epoch(empty, self.repo))
        reject_legacy_run("legacy-name", empty, self.repo)
        reject_retired_publication({}, empty, self.repo)

    def test_retirement_preserves_unknown_and_does_not_expire_after_hour(self):
        path = self.root / self.old / "progress.json"; before = path.read_bytes()
        self.assertIsNotNone(load_epoch(self.root, self.repo, now=datetime(2026, 10, 1, tzinfo=UTC)))
        self.assertEqual(published_today(self.root, "2026-09-16", repo=self.repo), 0)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(json.loads(before)["wordpress_write_count"], "unknown")

    def test_changed_added_or_missing_old_state_invalidates_retirement(self):
        for mutation in ("changed", "added", "missing"):
            with self.subTest(mutation=mutation):
                directory = self.root / self.old; path = directory / "progress.json"; before = path.read_bytes()
                if mutation == "changed": path.write_text("{}")
                elif mutation == "added": (directory / "result.json").write_text("{}")
                else: path.unlink()
                with self.assertRaises(EpochError): load_epoch(self.root, self.repo)
                path.write_bytes(before)
                if (directory / "result.json").exists(): (directory / "result.json").unlink()

    def test_unapproved_seal_tamper_fails_closed(self):
        (self.root / "epoch.json").write_text("{}")
        with self.assertRaises(EpochError): load_epoch(self.root, self.repo)

    def test_different_repository_or_site_cannot_activate_seal(self):
        self.command("remote", "set-url", "origin", "https://example.test/different.git")
        with self.assertRaises(EpochError): load_epoch(self.root, self.repo)
        self.command("remote", "set-url", "origin", "https://example.test/huntlab.git")
        inv = json.loads((self.root / "inventory.json").read_text()); inv["metadata"]["site"] = "https://different.test"
        self.seal["inventory"] = self.artifact("inventory.json", inv); self.save()
        with self.assertRaises(EpochError): load_epoch(self.root, self.repo)

    def test_incomplete_inventory_duplicate_id_or_queued_write_rejected(self):
        original = json.loads((self.root / "inventory.json").read_text())
        for problem in ("missing_status", "duplicate", "future", "stale"):
            inv = copy.deepcopy(original)
            if problem == "missing_status": del inv["metadata"]["statuses"]["trash"]
            elif problem == "duplicate": inv["posts"].append(inv["posts"][0]); inv["metadata"]["statuses"]["publish"] = 2
            elif problem == "future": inv["posts"].append({"id": 777, "status": "future"}); inv["metadata"]["statuses"]["future"] = 1
            else: inv["metadata"]["collected_at"] = "2026-09-09T00:00:00+00:00"
            self.seal["inventory"] = self.artifact("inventory.json", inv); self.save()
            with self.subTest(problem=problem), self.assertRaises(EpochError): load_epoch(self.root, self.repo)

    def test_downstream_activity_blocks_seal(self):
        quiet = json.loads((self.root / "quiet.json").read_text())
        quiet["downstream_executor"]["in_flight_requests"] = 1
        self.seal["quiescence"] = self.artifact("quiet.json", quiet); self.save()
        with self.assertRaises(EpochError): load_epoch(self.root, self.repo)

    def test_canonical_id_conflicting_date_rejected(self):
        path = self.root / self.old / "progress.json"
        path.write_text(json.dumps({"wordpress_write_count": "unknown", "kst_date": "2026-09-10"}))
        self.seal["retired_runs"][0]["state_sha256"] = {path.name: digest(path.read_bytes())}; self.save()
        with self.assertRaises(EpochError): load_epoch(self.root, self.repo)

    def test_new_unknown_still_blocks_and_confirmed_write_counts(self):
        run = self.root / "20260911T010000Z-new"; run.mkdir()
        path = run / "progress.json"; path.write_text(json.dumps({"wordpress_write_count": "unknown"}))
        with self.assertRaises(PipelineError): published_today(self.root, "2026-09-16", repo=self.repo)
        path.write_text(json.dumps({"wordpress_write_count": 1, "kst_date": "2026-09-16"}))
        self.assertEqual(published_today(self.root, "2026-09-16", repo=self.repo), 1)

    def test_old_resume_forbidden_new_run_allowed(self):
        with self.assertRaises(EpochError): reject_legacy_run(self.old, self.root, self.repo)
        reject_legacy_run("20260911T010000Z-new", self.root, self.repo)

    def test_same_day_and_malformed_retirement_allowlist_is_rejected(self):
        original = self.seal["retired_runs"][0]["run_id"]
        for value in ("20260910T000000Z-sameday", "20260230T000000Z-invalid", "20260905T010000-nozone", "legacy-name"):
            self.seal["retired_runs"][0]["run_id"] = value; self.save()
            with self.subTest(value=value), self.assertRaises(EpochError): load_epoch(self.root, self.repo)
        self.seal["retired_runs"][0]["run_id"] = original

    def test_general_topic_resume_guard_runs_before_any_stage(self):
        from scripts.run_daily_pipeline import run_topic_pipeline
        context = Mock(run_id=self.old)
        with patch("scripts.editorial_epoch.load_epoch", return_value=self.seal), patch("scripts.run_daily_pipeline.run_stage") as stage:
            with self.assertRaises(EpochError):
                run_topic_pipeline("codex", context, {}, Mock(), timeout_seconds=1, resume=True,
                                   publish_lock=Mock(), humanize_lock=Mock())
            stage.assert_not_called()

    def test_new_real_patch_is_eligible_but_old_identity_is_not(self):
        candidate = self.candidate(); validate_candidate(candidate, self.seal, self.repo)
        candidate["title_seed"] = "OLD_wordpress ISSUE!"
        with self.assertRaises(EpochError): validate_candidate(candidate, self.seal, self.repo)

    def test_quarantine_precedes_top_three_selection_and_keeps_new_candidate(self):
        candidate = self.candidate()
        candidate.update(publishability="READY", problem="WordPress publishing", evidence_contract={})
        old = [{**candidate, "candidate_id": "old-" + str(i), "title_seed": "Old WordPress issue"} for i in range(3)]
        payload = {"candidates": old, "status": "ready"}
        processing = {"processed": [*old, candidate]}
        with patch("scripts.run_evidence_deep_article.build_payload", return_value=(payload, processing, {})), patch("scripts.run_evidence_deep_article.persist_miner_run"):
            result = execute(run_id="20260916T010000Z-new-evaluation", inventory_path=self.root / "inventory.json", apply=False,
                             output_root=self.root, miner_root=self.repo / "miner", repo=self.repo)
        self.assertEqual(result["deep_article"], "ready_not_published")
        self.assertEqual(result["candidate_id"], "new")
        self.assertEqual(result["epoch_rejections"], ["old-0", "old-1", "old-2"])

    def test_epoch_pool_does_not_resurrect_already_processed_candidate(self):
        candidate = self.candidate(); candidate.update(publishability="READY", problem="WordPress publishing")
        miner = self.repo / "miner"; miner.mkdir()
        (miner / "checkpoint.json").write_text(json.dumps({"processed_event_ids": [candidate["candidate_id"]]}))
        runner = Mock()
        with patch("scripts.run_evidence_deep_article.build_payload", return_value=({"candidates": [], "status": "no_publishable_topic"}, {"processed": [candidate]}, {})), patch("scripts.run_evidence_deep_article.persist_miner_run"):
            result = execute(run_id="20260916T010000Z-processed", inventory_path=self.root / "inventory.json", apply=True,
                             topic_runner=runner, output_root=self.root, miner_root=miner, repo=self.repo)
        self.assertEqual(result["deep_article"], "no_publishable_topic")
        runner.assert_not_called()

    def test_old_evidence_fingerprint_cannot_be_relabelled(self):
        candidate = self.candidate(); self.seal["denied"]["evidence_fingerprints"] = [evidence_fingerprint(candidate)]
        with self.assertRaises(EpochError): validate_candidate(candidate, self.seal, self.repo)

    def test_claimed_anchor_must_be_in_real_diff(self):
        candidate = self.candidate(); candidate["event_key"] = candidate["event_key"].replace("source.py", "fiction.py"); candidate["source_anchor"] = "fiction.py"
        with self.assertRaises(EpochError): validate_candidate(candidate, self.seal, self.repo)

    def test_commit_date_and_strict_ancestry_both_required(self):
        candidate = self.candidate()
        old = copy.deepcopy(candidate); old["event_key"] = "source.py@" + self.cutoff; old["evidence"]["commits"] = [self.cutoff]
        with self.assertRaises(EpochError): validate_candidate(old, self.seal, self.repo)
        self.source.write_text("value = 3\n")
        predates = self.commit("backdated source", "2026-08-31T00:00:00+00:00")
        candidate["event_key"] = "source.py@" + predates; candidate["evidence"]["commits"] = [predates]
        with self.assertRaises(EpochError): validate_candidate(candidate, self.seal, self.repo)

    def test_genuine_post_cutoff_work_before_seal_is_not_discarded(self):
        self.source.write_text("value = 3\n")
        commit = self.commit("new before seal", "2026-09-09T00:00:00+00:00")
        candidate = {"candidate_id": "new", "title_seed": "New issue", "source_anchor": "source.py",
                     "event_key": "source.py@" + commit, "evidence": {"commits": [commit]}}
        validate_candidate(candidate, self.seal, self.repo)

    def test_cherry_picked_legacy_patch_is_rejected_even_with_new_commit_date(self):
        # Undo and recreate the pre-cutoff root patch with a new parent and date.
        self.source.unlink(); removed = self.commit("remove", "2026-09-11T00:00:00+00:00")
        self.source.write_text("value = 1\n"); new = self.commit("replay old", "2026-09-12T00:00:00+00:00")
        candidate = {"candidate_id": "new", "title_seed": "Unrelated label", "source_anchor": "source.py",
                     "event_key": "source.py@" + new, "evidence": {"commits": [new]}}
        with self.assertRaises(EpochError): validate_candidate(candidate, self.seal, self.repo)

    def test_final_slug_and_title_are_checked_after_writing(self):
        for metadata in ({"title": "New", "slug": "OLD_wordpress-issue"}, {"title": "Old wordpress ISSUE", "slug": "new"}, {"title": "New"}):
            with self.subTest(metadata=metadata), self.assertRaises(EpochError): reject_retired_publication(metadata, self.root, self.repo)
        reject_retired_publication({"title": "New", "slug": "new"}, self.root, self.repo)
