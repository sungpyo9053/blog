import os
import unittest
from unittest.mock import patch

from scripts.editorial_runtime import codex_model_arguments
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

    def test_invalid_selection_fails_before_call(self):
        for values in ({'HUNTLAB_CODEX_MODEL':'x;echo bad'}, {'HUNTLAB_CODEX_REASONING':'high'},
                       {'HUNTLAB_CODEX_MODEL':'gpt-5.6-terra','HUNTLAB_CODEX_REASONING':'invented'}):
            with self.subTest(values=values), patch.dict(os.environ, values, clear=True), self.assertRaises(ValueError):
                codex_model_arguments()
