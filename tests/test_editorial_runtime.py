import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.editorial_runtime import (agent_environment, agent_runtime, build_json_command,
                                       codex_model_arguments, collect_json_output)
from scripts.run_daily_pipeline import build_codex_command


class RuntimeTests(unittest.TestCase):
    def test_unconfigured_keeps_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(codex_model_arguments(), [])

    def test_explicit_supported_runtime_does_not_change_prompt(self):
        with patch.dict(os.environ, {'HUNTLAB_CODEX_MODEL':'gpt-5.6-terra', 'HUNTLAB_CODEX_REASONING':'high'}, clear=True):
            command = build_codex_command('codex', 'unchanged prompt')
            self.assertEqual(command[1:5], ['--model','gpt-5.6-terra','-c','model_reasoning_effort="high"'])
            self.assertEqual(command[-1], 'unchanged prompt')

    def test_codex_default_stage_command_is_unchanged(self):
        with patch.dict(os.environ, {}, clear=True):
            command = build_codex_command('codex', 'p')
        self.assertEqual(command[:7], ['codex', '--ask-for-approval', 'never', '--sandbox', 'danger-full-access',
                                       '--search', 'exec'])
        self.assertEqual(command[-1], 'p')

    def test_codex_default_json_command_is_unchanged(self):
        with patch.dict(os.environ, {}, clear=True):
            command = build_json_command('codex', workdir='/w', output='/w/a.json', apply_model=False)
        self.assertEqual(command[0], 'codex')
        self.assertIn('read-only', command)
        self.assertEqual(command[-5:], ['--output-last-message', '/w/a.json', '--cd', '/w', '-'])
        self.assertIn('features.shell_tool=false', command)

    def test_claude_stage_command_bypasses_prompts_and_keeps_prompt_last(self):
        env = {'HUNTLAB_AGENT_RUNTIME': 'claude', 'HUNTLAB_CLAUDE_MODEL': 'claude-opus-5-5',
               'HUNTLAB_CLAUDE_EFFORT': 'high'}
        with patch.dict(os.environ, env, clear=True):
            command = build_codex_command('/bin/claude', 'unchanged prompt')
        self.assertEqual(command[:5], ['/bin/claude', '--model', 'claude-opus-5-5', '--effort', 'high'])
        self.assertIn('--print', command)
        self.assertEqual(command[command.index('--permission-mode') + 1], 'bypassPermissions')
        self.assertEqual(command[-1], 'unchanged prompt')

    def test_claude_json_command_disables_tools_and_enforces_schema(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {'HUNTLAB_AGENT_RUNTIME': 'claude'}, clear=True):
            schema = Path(directory) / 'schema.json'
            schema.write_text('{"type":"object"}')
            command = build_json_command('claude', workdir=directory, output=Path(directory) / 'a.json',
                                         schema=schema)
        self.assertEqual(command[command.index('--tools') + 1], '')
        self.assertEqual(command[command.index('--json-schema') + 1], '{"type":"object"}')
        self.assertEqual(command[command.index('--output-format') + 1], 'json')

    def test_claude_json_envelope_is_materialized(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {'HUNTLAB_AGENT_RUNTIME': 'claude'}, clear=True):
            output = Path(directory) / 'a.json'
            ok = SimpleNamespace(returncode=0, stdout=json.dumps({'structured_output': {'verdict': 'HOLD'}}))
            collect_json_output(ok, output)
            self.assertEqual(json.loads(output.read_text()), {'verdict': 'HOLD'})
            output.unlink()
            collect_json_output(SimpleNamespace(returncode=0, stdout=json.dumps({'is_error': True})), output)
            collect_json_output(SimpleNamespace(returncode=1, stdout=''), output)
            self.assertFalse(output.exists())

    def test_claude_environment_carries_only_claude_credentials(self):
        env = {'HUNTLAB_AGENT_RUNTIME': 'claude', 'HOME': '/h', 'CLAUDE_CODE_OAUTH_TOKEN': 't',
               'CODEX_HOME': '/c', 'WORDPRESS_APP_PASSWORD': 'x'}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(agent_environment(), {'HOME': '/h', 'CLAUDE_CODE_OAUTH_TOKEN': 't'})

    def test_invalid_runtime_fails_before_call(self):
        with patch.dict(os.environ, {'HUNTLAB_AGENT_RUNTIME': 'gpt'}, clear=True), self.assertRaises(ValueError):
            agent_runtime()

    def test_invalid_selection_fails_before_call(self):
        for values in ({'HUNTLAB_CODEX_MODEL':'x;echo bad'}, {'HUNTLAB_CODEX_REASONING':'high'},
                       {'HUNTLAB_CODEX_MODEL':'gpt-5.6-terra','HUNTLAB_CODEX_REASONING':'invented'}):
            with self.subTest(values=values), patch.dict(os.environ, values, clear=True), self.assertRaises(ValueError):
                codex_model_arguments()
