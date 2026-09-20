"""Explicit, process-scoped model selection; no automatic quality fallback."""
import os
import re


def codex_model_arguments():
    model = os.environ.get('HUNTLAB_CODEX_MODEL', '').strip()
    effort = os.environ.get('HUNTLAB_CODEX_REASONING', '').strip()
    if not model:
        if effort:
            raise ValueError('editorial_reasoning_requires_model')
        return []
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,79}', model):
        raise ValueError('editorial_model_invalid')
    if effort and effort not in {'low', 'medium', 'high', 'xhigh', 'max', 'ultra'}:
        raise ValueError('editorial_reasoning_invalid')
    return ['--model', model] + (['-c', f'model_reasoning_effort="{effort}"'] if effort else [])
