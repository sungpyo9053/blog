import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import discover_physical_ai as d


class ArithmeticTests(unittest.TestCase):
    def test_allowed(self):
        self.assertEqual(d.arithmetic('(-2 + 5) * 8 / 4'), 6)

    def test_forbidden(self):
        for expression in ('True', '__import__("os")', 'a+1', '1**2', '(1).__class__', '[1]', '1//2', '1%2', '1/0', '1e309', '9e12', '1;'+'print(1)'):
            with self.subTest(expression=expression), self.assertRaises(d.DiscoveryError):
                d.arithmetic(expression)

    def test_limits(self):
        for expression in ('1+'*100+'1', '1'*501):
            with self.assertRaises(d.DiscoveryError): d.arithmetic(expression)

    def test_duplicate_json_and_nan(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}'):
            with self.assertRaises(d.DiscoveryError): d.parse_json(text)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'config').mkdir()
        self.now = datetime(2026, 9, 20, tzinfo=timezone.utc)
        self.config = {'producer_status': 'enabled', 'evidence_repository': 'https://github.com/sungpyo9053/blog',
                       'expected_git_origin': 'https://github.com/sungpyo9053/blog.git', 'allowed_primary_hosts': ['docs.example.org'],
                       'primary_sources': [{'id': 'control', 'url': 'https://docs.example.org/control', 'publisher': 'Official', 'claim_scope': 'control'}]}
        self.write_config()
        self.inventory = self.root/'inventory.json'
        self.inventory.write_text(json.dumps({'metadata': {'complete': True, 'full_content': True,
            'collected_at': self.now.isoformat(), 'statuses': {'publish': 0, 'draft': 0}}, 'posts': []}))
        self.candidate = {'title': '비례 제어 오차와 출력 계산', 'slug': 'proportional-error-command',
            'reader_question': '오차가 달라지면 출력은 어떻게 바뀌나?', 'target_reader': '로봇 제어 입문자',
            'learning_outcome': '계산하고 비교한다', 'unique_takeaway': '제어 이득과 오차의 곱을 비교한다',
            'source_ids': ['control'], 'example': {'description': '설명용 산술 예제, 단위 명시',
                'cases': [{'name': f'case{i}', 'expression': f'{i} * 2', 'expected': i*2} for i in (1,2,3)],
                'conclusion': '출력이 달라진다', 'limitations': '실물 로봇 검증 아님'}}
        self.approval = {'verdict': 'APPROVED', 'reason': '자료와 자체계산을 독립 검토했다',
                         'primary_sources_verified': True, 'worked_example_verified': True,
                         'public_evidence_verified': True, 'secret_safe': True}
        self.calls, self.publishes = [], []

    def write_config(self):
        (self.root/'config/physical-ai-discovery.json').write_text(json.dumps(self.config))

    def agent(self, repo, role, payload, directory):
        self.calls.append((role, payload))
        return {'status': 'candidate', 'reason': '새 질문', 'candidate': self.candidate} if role == 'researcher' else self.approval

    def fetch(self, url, hosts):
        if 'raw.githubusercontent.com' in url:
            relative = url.split('/' + 'a'*40 + '/', 1)[1]
            return (self.root/relative).read_bytes()
        return b'<html><body>Official proportional control example documentation.</body></html>'

    def publish(self, repo, paths, config, message):
        self.publishes.append(paths)
        return 'a'*40

    def run_it(self, **kwargs):
        return d.run_discovery(self.root, self.inventory, '20260920T010000Z-test', self.now,
                              agent=kwargs.pop('agent', self.agent), fetch=kwargs.pop('fetch', self.fetch),
                              git_publish=kwargs.pop('git_publish', self.publish), **kwargs)

    def test_no_candidate_no_git(self):
        result = self.run_it(agent=lambda *args: {'status': 'no_candidate', 'reason': '근거 부족', 'candidate': None})
        self.assertEqual(result['status'], 'no_candidate'); self.assertFalse(self.publishes)

    def test_ready_two_commits_host_bound(self):
        with patch.object(d, 'load_epoch', return_value=None), patch.object(d, 'evaluate_foundation', return_value={'candidate_id': 'foundation-example'}) as final:
            result = self.run_it()
        self.assertEqual(result['status'], 'ready'); self.assertEqual(len(self.publishes), 2)
        self.assertEqual([role for role, _ in self.calls], ['researcher', 'reviewer'])
        self.assertEqual(self.calls[1][1]['verification']['python'], d.sys.version.split()[0])
        self.assertEqual(self.calls[1][1]['verification']['exit_code'], 0)
        self.assertTrue(final.called)
        manifest = json.loads((self.root/'editorial/physical-ai-candidates/proportional-error-command.json').read_text())
        review = json.loads((self.root/'editorial/physical-ai-candidates/proportional-error-command.review.json').read_text())
        self.assertNotEqual(manifest['author_id'], review['reviewer_id'])
        self.assertEqual(review['manifest_sha256'], d.digest(d.encode(manifest)))
        self.assertEqual(len(self.publishes[0]), 3); self.assertEqual(len(self.publishes[1]), 2)

    def test_all_sources_fail_no_agent(self):
        def fail(*args): raise RuntimeError('private diagnostics')
        with self.assertRaisesRegex(d.DiscoveryError, '^all_primary_sources_failed$'): self.run_it(fetch=fail)
        self.assertFalse(self.calls); self.assertFalse(self.publishes)

    def test_hold_no_git(self):
        self.approval['verdict'] = 'HOLD'
        result = self.run_it()
        self.assertEqual(result['status'], 'no_candidate')
        self.assertEqual(result['reason'], 'independent_review_hold')
        self.assertFalse(self.publishes)

    def test_malicious_code_never_executes(self):
        self.candidate['example']['cases'][0]['expression'] = '__import__("os").system("echo bad")'
        with patch.object(d.subprocess, 'run') as execution:
            with self.assertRaises(d.DiscoveryError): self.run_it()
            execution.assert_not_called()
        self.assertFalse(self.publishes)

    def test_wrong_expected_no_reviewer(self):
        self.candidate['example']['cases'][0]['expected'] = 7
        with self.assertRaisesRegex(d.DiscoveryError, '^case_result_mismatch$'): self.run_it()
        self.assertEqual(len(self.calls), 1)

    def test_duplicate_no_git(self):
        with patch.object(d, 'existing_overlap', return_value={'result': 'duplicate'}):
            result = self.run_it()
        self.assertEqual(result['status'], 'no_candidate')
        self.assertEqual(result['reason'], 'candidate_duplicate')
        self.assertFalse(self.publishes)

    def test_public_bytes_wrong_stops_before_registration(self):
        def fetch(url, hosts): return b'wrong' if 'raw.githubusercontent' in url else self.fetch(url, hosts)
        with self.assertRaisesRegex(d.DiscoveryError, '^public_artifact_hash_mismatch$'): self.run_it(fetch=fetch)
        self.assertEqual(len(self.publishes), 1)
        self.assertFalse((self.root/'editorial/physical-ai-candidates/proportional-error-command.json').exists())

    def test_attempt_never_retried(self):
        agent = lambda *args: {'status': 'no_candidate', 'reason': 'not enough', 'candidate': None}
        self.run_it(agent=agent)
        with self.assertRaisesRegex(d.DiscoveryError, '^prior_discovery_requires_reconciliation$'): self.run_it()

    def test_run_path_rejected(self):
        with self.assertRaisesRegex(d.DiscoveryError, '^unsafe_run_id$'):
            d.run_discovery(self.root, self.inventory, '../outside', self.now)

    def test_source_ids_and_no_candidate_schema(self):
        self.candidate['source_ids'] = ['fabricated']
        with self.assertRaises(d.DiscoveryError): self.run_it()

    def test_model_failures_sanitized(self):
        def agent(*args): raise RuntimeError('secret-token-cannot-be-logged')
        with self.assertRaisesRegex(d.DiscoveryError, '^discovery_execution_failed$'): self.run_it(agent=agent)
        result = (self.root/'output/physical-discovery/20260920T010000Z-test/result.json').read_text()
        self.assertNotIn('secret-token', result)

    def test_ssrf_rejected_before_dns(self):
        with patch.object(d.socket, 'getaddrinfo') as dns:
            for url in ('http://docs.example.org/', 'https://evil.example/', 'https://user@docs.example.org/', 'https://docs.example.org:444/'):
                with self.assertRaises(d.DiscoveryError): d.fetch_https(url, ['docs.example.org'])
            dns.assert_not_called()

    def test_private_dns_rejected(self):
        with patch.object(d.socket, 'getaddrinfo', return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaisesRegex(d.DiscoveryError, '^nonpublic_source_address$'):
                d.fetch_https('https://docs.example.org/', ['docs.example.org'])

    def test_prompt_size_rejected_without_model(self):
        (self.root/'agents').mkdir()
        (self.root/'agents/physical-discovery-researcher.md').write_text('JSON only')
        with patch.object(d.subprocess, 'run') as process:
            with self.assertRaisesRegex(d.DiscoveryError, '^model_input_too_large$'):
                d.invoke_agent(self.root, 'researcher', {'data': '가'*120000}, self.root)
            process.assert_not_called()

    def test_git_has_only_explicit_paths_no_other_staged(self):
        commands = []
        paths = ['editorial/generated-foundations/new/example.py', 'editorial/generated-foundations/new/verification.json']
        def command(repo, *args):
            commands.append(args)
            if args == ('branch', '--show-current'): return 'main'
            if args[:2] == ('remote', 'get-url'): return self.config['expected_git_origin']
            if args[:2] == ('ls-remote', 'origin'): return ('b'*40 if len([x for x in commands if x[:2] == ('ls-remote','origin')]) == 1 else 'a'*40) + '\trefs/heads/main'
            if args == ('rev-parse', 'HEAD'): return 'a'*40 if any('commit' in row for row in commands) else 'b'*40
            if args[0] == 'diff-tree': return '\n'.join(paths)
            return ''
        with patch.object(d, 'git_command', side_effect=command):
            self.assertEqual(d.publish_files(self.root, paths, self.config, 'Test'), 'a'*40)
        self.assertIn(('add', '--', *paths), commands)
        self.assertIn(('-c', 'core.hooksPath=/dev/null', '-c', 'user.name=HuntLab Automation',
                       '-c', 'user.email=huntlab-automation@users.noreply.github.com',
                       'commit', '--only', '-m', 'Test', '--', *paths), commands)
        self.assertFalse(any('-a' in row or '--all' in row for row in commands))

    def test_git_wrong_branch_no_add(self):
        with patch.object(d, 'git_command', return_value='other') as command:
            with self.assertRaisesRegex(d.DiscoveryError, '^git_not_main$'):
                d.publish_files(self.root, ['editorial/new.py'], self.config, 'Test')
            self.assertEqual(command.call_count, 1)

    def test_fresh_inventory_required_before_agent(self):
        inventory = json.loads(self.inventory.read_text())
        inventory['metadata']['collected_at'] = '2020-01-01T00:00:00+00:00'
        self.inventory.write_text(json.dumps(inventory))
        with self.assertRaisesRegex(d.DiscoveryError, '^inventory_not_fresh_complete$'): self.run_it()
        self.assertFalse(self.calls)

    def test_final_authority_failure_not_ready(self):
        with patch.object(d, 'load_epoch', return_value=None), patch.object(d, 'evaluate_foundation', side_effect=ValueError('epoch unsafe')):
            with self.assertRaisesRegex(d.DiscoveryError, '^discovery_execution_failed$'): self.run_it()
        receipt = json.loads((self.root/'output/physical-discovery/20260920T010000Z-test/result.json').read_text())
        self.assertEqual(receipt['status'], 'failed')


if __name__ == '__main__': unittest.main()
