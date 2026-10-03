"""Explicit, process-scoped model selection; no automatic quality fallback."""
import json
import os
import re
import shutil
from pathlib import Path

RUNTIMES = ('codex', 'claude')
# Only the selected runtime's credential reaches tool-less JSON agents.
AUTH_KEYS = {'codex': ('CODEX_HOME',), 'claude': ('CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_API_KEY')}


def agent_runtime():
    runtime = os.environ.get('HUNTLAB_AGENT_RUNTIME', '').strip() or 'codex'
    if runtime not in RUNTIMES:
        raise ValueError('editorial_runtime_invalid')
    return runtime


def resolve_agent_executable():
    runtime = agent_runtime()
    executable = (os.environ.get('HUNTLAB_AGENT_BIN')
                  or (os.environ.get('CODEX_BIN') if runtime == 'codex' else None)
                  or shutil.which(runtime))
    if not executable:
        raise FileNotFoundError(f'{runtime}_cli_missing')
    return executable


def agent_environment(keys=('HOME', 'PATH', 'LANG', 'LC_ALL')):
    return {key: os.environ[key] for key in (*keys, *AUTH_KEYS[agent_runtime()]) if key in os.environ}


def _model_arguments(model_variable, effort_variable, efforts, effort_flag):
    model = os.environ.get(model_variable, '').strip()
    effort = os.environ.get(effort_variable, '').strip()
    if not model:
        if effort:
            raise ValueError('editorial_reasoning_requires_model')
        return []
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,79}', model):
        raise ValueError('editorial_model_invalid')
    if effort and effort not in efforts:
        raise ValueError('editorial_reasoning_invalid')
    return ['--model', model] + (effort_flag(effort) if effort else [])


def codex_model_arguments():
    return _model_arguments('HUNTLAB_CODEX_MODEL', 'HUNTLAB_CODEX_REASONING',
                            {'low', 'medium', 'high', 'xhigh', 'max', 'ultra'},
                            lambda effort: ['-c', f'model_reasoning_effort="{effort}"'])


# Mechanical stages (no editorial judgment) may run on a cheaper model to save quota.
LIGHT_STAGES = frozenset({'Image Maker Agent', 'Assembler Agent', 'Humanize Experiment Agent'})


def claude_model_arguments(light=False):
    prefix = 'HUNTLAB_CLAUDE_LIGHT' if light and os.environ.get('HUNTLAB_CLAUDE_LIGHT_MODEL', '').strip() else 'HUNTLAB_CLAUDE'
    return _model_arguments(prefix + '_MODEL', prefix + '_EFFORT',
                            {'low', 'medium', 'high', 'xhigh', 'max'},
                            lambda effort: ['--effort', effort])


def alert_quota_exhausted(output, root, sender=None):
    """Kakao once per day when the agent CLI reports a usage limit; never raises."""
    line = next((l for l in output.splitlines() if re.search(r'hit your .*limit', l, re.I)), None)
    if not line:
        return False
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        marker = Path(root) / 'output' / 'agent-quota' / (datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat() + '.sent')
        if marker.exists():
            return False
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(line)
        if sender is None:
            from scripts.send_kakao_report import send as sender
        sender(f'[HuntLab 경고] AI 사용량 한도 소진 — 글 준비·브리핑 중단\n{line.strip()[:120]}',
               os.environ.get('MCPORTER_BIN', 'mcporter'))
        return True
    except Exception:
        return False


def build_stage_command(executable, prompt, project_root, stage_name=''):
    """Full-access, web-enabled, non-interactive stage run; the prompt is the last argument."""
    if agent_runtime() == 'claude':
        return [executable, *claude_model_arguments(light=stage_name in LIGHT_STAGES), '--print', '--permission-mode', 'bypassPermissions',
                '--no-session-persistence', '--output-format', 'text', prompt]
    return [executable, *codex_model_arguments(), '--ask-for-approval', 'never', '--sandbox', 'danger-full-access',
            '--search', 'exec', '--ephemeral', '--color', 'never', '--cd', str(project_root), prompt]


def build_json_command(executable, *, workdir, output, schema=None, apply_model=True):
    """Tool-less JSON answer; the prompt goes to stdin.

    Codex writes the final message to ``output`` itself. Claude prints a JSON
    envelope on stdout, which ``collect_json_output`` turns into ``output``.
    """
    if agent_runtime() == 'claude':
        command = [executable, *(claude_model_arguments() if apply_model else []), '--print', '--tools', '',
                   '--strict-mcp-config', '--no-session-persistence', '--output-format', 'json']
        if schema is not None:
            command += ['--json-schema', Path(schema).read_text()]
        return command
    command = [executable, *(codex_model_arguments() if apply_model else []), '--ask-for-approval', 'never',
               '--sandbox', 'read-only', 'exec', '--ephemeral', '--ignore-user-config', '--ignore-rules',
               '--skip-git-repo-check']
    if schema is not None:
        command += ['--output-schema', str(schema)]
    command += ['--output-last-message', str(output), '--cd', str(workdir), '-']
    for setting in ('features.shell_tool=false', 'features.apps=false', 'features.hooks=false',
                    'features.multi_agent=false', 'features.memories=false', 'features.remote_plugin=false',
                    'web_search="disabled"', 'tools.view_image=false'):
        command[1:1] = ['-c', setting]
    return command


def collect_json_output(result, output):
    """Materialize a successful Claude JSON envelope into ``output``; Codex already wrote it."""
    if agent_runtime() != 'claude' or result.returncode:
        return
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError:
        return
    if not isinstance(envelope, dict) or envelope.get('is_error'):
        return
    answer = envelope.get('structured_output')
    if answer is not None:
        Path(output).write_text(json.dumps(answer, ensure_ascii=False))
        return
    # Without --json-schema Claude may wrap the JSON in a ```json fence; Codex never does.
    text = str(envelope.get('result', '')).strip()
    fenced = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n?```', text, flags=re.S)
    Path(output).write_text(fenced.group(1) if fenced else text)
