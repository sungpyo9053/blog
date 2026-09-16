import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from scripts.foundation_candidates import FoundationError, evaluate_foundation, load_foundation_candidates, validate_foundation_epoch, foundation_activation_ready, consumed_foundation_ids


class FoundationCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name); self.now = datetime(2026, 9, 16, 10, tzinfo=UTC)
        self.git('init', '-q'); self.git('config', 'user.name', 'Test Reviewer'); self.git('config', 'user.email', 'test@example.invalid')
        (self.repo / 'README.md').write_text('old repository')
        self.cutoff = self.commit('cutoff', '2026-09-14T00:00:00+00:00')
        evidence = self.repo / 'editorial/foundation-evidence'; evidence.mkdir(parents=True)
        self.example = evidence / 'example.md'; self.example.write_text('## 관측과 행동\n새로 만든 산술 예제: 관측 0, 목표 1, 이동량 0.2. 물리 로봇 아님.')
        self.verification = evidence / 'verification.md'; self.verification.write_text('검산: min(0.5 * (1 - 0), 0.2) = 0.2. 독립 검토 완료.')
        revision = self.commit('worked example', '2026-09-15T00:00:00+00:00')
        def reference(path):
            relative = path.relative_to(self.repo).as_posix()
            return {'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'public_url': f'https://github.com/example/repo/blob/{revision}/{relative}'}
        queue = self.repo / 'editorial/physical-ai-candidates'; queue.mkdir()
        self.path = queue / 'observation.json'
        self.manifest = {
            'schema_version': 1, 'candidate_id': 'foundation-observation', 'title': '로봇 관측과 행동의 차이',
            'slug': 'robot-observation-action', 'reader_question': '로봇의 관측과 행동은 어떻게 다른가',
            'target_reader': '처음 배우는 개발자', 'learning_outcome': '입력과 행동을 구분한다',
            'unique_takeaway': '행동이 변해도 정책 학습은 아닐 수 있다', 'author_id': 'author',
            'primary_sources': [{'url': 'https://gymnasium.farama.org/introduction/basic_usage/',
                                 'publisher': 'Farama', 'claim_scope': '관측-행동 루프', 'checked_at': self.now.isoformat()}],
            'worked_example': reference(self.example), 'verification': reference(self.verification),
        }
        self.review = {'schema_version': 1, 'manifest_sha256': '', 'reviewer_id': 'reviewer',
                       'reviewed_at': self.now.isoformat(), 'verdict': 'APPROVED', 'primary_sources_verified': True,
                       'worked_example_verified': True, 'public_evidence_verified': True, 'secret_safe': True}
        self.save()
        self.commit('reviewed foundation candidate', '2026-09-16T00:00:00+00:00')
        self.inventory = self.repo / 'inventory.json'
        self.inventory.write_text(json.dumps({'metadata': {'complete': True, 'full_content': True,
            'collected_at': self.now.isoformat(), 'statuses': {'publish': 0, 'draft': 0}}, 'posts': []}))
        self.seal = {'cutoff_commit': self.cutoff, 'denied': {'candidate_ids': [], 'titles': [], 'slugs': [], 'evidence_fingerprints': []}}

    def git(self, *args, env=None):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True, env=env).stdout.decode().strip()

    def commit(self, message, date):
        self.git('add', '.')
        self.git('commit', '-qm', message, env={**os.environ, 'GIT_AUTHOR_DATE': date, 'GIT_COMMITTER_DATE': date})
        return self.git('rev-parse', 'HEAD')

    def save(self):
        self.path.write_text(json.dumps(self.manifest, ensure_ascii=False))
        self.review['manifest_sha256'] = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.path.with_suffix('.review.json').write_text(json.dumps(self.review))

    def evaluate(self):
        return evaluate_foundation(self.path, repo=self.repo, inventory_path=self.inventory, seal=self.seal, now=self.now)

    def test_verified_foundation_is_ready_without_fake_incident(self):
        candidate = self.evaluate()
        self.assertEqual(candidate['publishability'], 'READY')
        self.assertEqual(candidate['candidate_origin'], 'foundation_concept')
        self.assertEqual(candidate['evidence']['commits'], [])
        self.assertNotIn('event_key', candidate)

    def test_missing_approval_and_uncommitted_changes_fail_closed(self):
        self.path.with_suffix('.review.json').unlink()
        ready, rejected = load_foundation_candidates(repo=self.repo, inventory_path=self.inventory, seal=self.seal, now=self.now)
        self.assertEqual(ready, []); self.assertEqual(len(rejected), 1)
        self.save(); self.manifest['title'] += ' 변경'; self.save()
        with self.assertRaisesRegex(FoundationError, 'not_committed'):
            self.evaluate()

    def test_self_review_insufficient_evidence_and_changed_hash_reject(self):
        for field, value in (('reviewer_id', ' AUTHOR '), ('worked_example_verified', False), ('public_evidence_verified', False)):
            original = self.review[field]; self.review[field] = value; self.save()
            with self.assertRaises(FoundationError): self.evaluate()
            self.review[field] = original
        self.save(); self.example.write_text('tampered')
        with self.assertRaisesRegex(FoundationError, 'hash_mismatch'): self.evaluate()

    def test_stale_or_incomplete_inventory_and_duplicate_title_reject(self):
        original = json.loads(self.inventory.read_text())
        for key, value in (('complete', False), ('full_content', False), ('collected_at', '2026-09-01T00:00:00Z')):
            payload = json.loads(json.dumps(original)); payload['metadata'][key] = value
            self.inventory.write_text(json.dumps(payload))
            with self.assertRaisesRegex(FoundationError, 'inventory'): self.evaluate()
        original['posts'] = [{'post_id': 1, 'status': 'draft', 'title': self.manifest['title'], 'slug': 'draft', 'content': 'another body'}]
        original['metadata']['statuses']['draft'] = 1; self.inventory.write_text(json.dumps(original))
        with self.assertRaisesRegex(FoundationError, 'search_intent'): self.evaluate()

    def test_retirement_id_and_title_still_block(self):
        self.seal['denied']['candidate_ids'] = [self.manifest['candidate_id']]
        with self.assertRaisesRegex(FoundationError, 'retired_candidate'): self.evaluate()
        self.seal['denied']['candidate_ids'] = []; self.seal['denied']['titles'] = [self.manifest['title']]
        with self.assertRaisesRegex(FoundationError, 'retired_title'): self.evaluate()

    def test_consumed_candidate_is_not_reselected(self):
        ready, rejected = load_foundation_candidates(repo=self.repo, inventory_path=self.inventory, seal=self.seal,
            consumed_ids=[self.manifest['candidate_id']], now=self.now)
        self.assertEqual((ready, rejected), ([], []))

    def test_postcutoff_requirement_applies_to_documentation(self):
        self.seal['cutoff_commit'] = self.git('rev-parse', 'HEAD')
        with self.assertRaises(FoundationError): self.evaluate()

    def test_activation_requires_real_draft_evidence_bound_to_hash(self):
        self.assertFalse(foundation_activation_ready(self.repo))
        directory = self.repo / 'output/foundation-workflow'; directory.mkdir(parents=True)
        raw = '<p>Checked draft body</p>'
        evidence = directory / 'draft-evidence.json'
        evidence.write_text(json.dumps({'draft': {'id': 1001, 'status': 'draft', 'content': {'raw': raw}},
            'render_validation': {'passed': True}, 'reread_body_sha256': hashlib.sha256(raw.encode()).hexdigest()}))
        approval = {'schema_version': 1, 'workflow': 'foundation_concept', 'status': 'DRAFT_WORKFLOW_VERIFIED',
            'draft_post_id': 1001, 'source_run_id': 'draft-run', 'checked_at': '2026-09-01T00:00:00Z',
            'reviewer_id': 'independent-reviewer', 'evidence': {'path': evidence.relative_to(self.repo).as_posix(),
            'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}}
        (directory / 'activation.json').write_text(json.dumps(approval))
        self.assertTrue(foundation_activation_ready(self.repo))
        evidence.write_text('{}')
        self.assertFalse(foundation_activation_ready(self.repo))

    def test_consumption_uses_confirmed_progress_even_if_receipt_write_failed(self):
        root = self.repo / 'runs'; run = root / 'confirmed'; run.mkdir(parents=True)
        (run / 'selected-candidate.json').write_text(json.dumps({'candidate_origin': 'foundation_concept', 'candidate_id': 'foundation-one'}))
        (run / 'progress.json').write_text('{"wordpress_write_count":"unknown"}')
        self.assertEqual(consumed_foundation_ids(root), set())
        (run / 'progress.json').write_text('{"wordpress_write_count":1}')
        self.assertEqual(consumed_foundation_ids(root), {'foundation-one'})
