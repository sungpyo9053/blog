"""Execute exact proposed reader blocks; store sanitized verification only."""
from datetime import UTC, datetime
import hashlib
import ast
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.editorial_gate import inspect_article
from scripts.snapshot_topic_inventory import redact_text
REV = '170c6ba70c419501171ae741b318a2fb6f4ac38d'
def sha(data):
    return hashlib.sha256(data).hexdigest()
def blocks(post_id):
    body = (HERE / f'post-{post_id}.after.html').read_text()
    return [html.unescape(b) for b in re.findall(r'<pre><code[^>]*>(.*?)</code></pre>', body, re.S)]
def run(command, cwd):
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'])
    p = subprocess.run(['bash', '-e'], input=command, text=True, cwd=cwd, env=env,
                       capture_output=True, timeout=300)
    output = (p.stdout + p.stderr).replace(str(cwd), '[reader-directory]')
    # Public evidence keeps only decisive output, not dependency download chatter.
    lines = [l for l in output.splitlines() if l.startswith(('Python ', 'test_', 'Ran ', 'OK', 'valid:', 'missing_', 'created_', 'bounded_', '{'))]
    return {'block_sha256': sha(command.encode()), 'exit': p.returncode, 'output': '\n'.join(lines)}

manifest = json.loads((HERE / 'content-corrections.json').read_text())
inventory_path = ROOT / 'output/quality99-round2-inventory.json'
inventory = json.loads(inventory_path.read_text())
by_id = {r['post_id']: r for r in inventory['posts']}
for r in manifest['posts']:
    for kind in ('before', 'after'):
        assert sha((HERE / r[kind + '_file']).read_bytes()) == r[kind + '_sha256']
    assert by_id[r['post_id']]['content'] == redact_text((HERE / r['before_file']).read_text())
    by_id[r['post_id']]['content'] = (HERE / r['after_file']).read_text()
# Include independently proposed round-one content in the final combined set.
other = HERE.parent / 'quality99-content/content-corrections.json'
for r in json.loads(other.read_text())['posts']:
    by_id[r['post_id']]['content'] = (other.parent / r['after_file']).read_text()
gates = []
for r in manifest['posts']:
    g = inspect_article(by_id[r['post_id']]['content'], inventory, existing_post_id=r['post_id'])
    assert g['passed'], g
    gates.append(dict(post_id=r['post_id'], **g))

setup = blocks(50)[0]
assert setup == blocks(290)[0] == blocks(373)[0] and REV in setup
execution = []
with tempfile.TemporaryDirectory(prefix='huntlab-exact-round2-') as temp:
    execution.append(dict(name='shared_exact_setup_50_290_373', **run(setup, Path(temp))))
    assert execution[-1]['exit'] == 0
    checkout = Path(temp) / 'blog'
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip()
    assert actual == REV
    for post_id in (50, 290):
        command = blocks(post_id)[-1]
        execution.append(dict(name=f'post_{post_id}_exact_tests', **run(command, checkout)))
        assert execution[-1]['exit'] == 0
    command = next(b for b in blocks(373) if b.startswith(".venv/bin/python - <<'PY'"))
    execution.append(dict(name='post_373_unchanged_example', **run(command, checkout)))
    assert execution[-1]['exit'] == 0
    execution.append(dict(name='post_698_current_five_tests', **run('.venv/bin/python -m unittest tests.test_huntlab_wp_diagnostics -v', checkout)))
    assert execution[-1]['exit'] == 0
    source_hashes = {}
    for name in ('publisher/wordpress.py', 'publisher/service.py', 'tests/test_wordpress_retry.py', 'tests/test_publisher.py', 'requirements-publisher.txt'):
        if (checkout / name).is_file():
            assert (checkout / name).read_bytes() == (ROOT / name).read_bytes(), name
            source_hashes[name] = sha((checkout / name).read_bytes())
    def selected_definitions(source):
        tree = ast.parse(source)
        return '\n'.join(ast.dump(n, include_attributes=False) for n in tree.body
                         if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                         and n.name in {'PipelineError', 'Stage', 'planner_retry_stage'})
    current = selected_definitions((ROOT / 'scripts/run_daily_pipeline.py').read_text())
    pinned = selected_definitions((checkout / 'scripts/run_daily_pipeline.py').read_text())
    assert current == pinned
    source_hashes['selected_planner_definitions_ast'] = sha(pinned.encode())

assert blocks(698)[0] == blocks(699)[0] and REV in blocks(698)[0]
with tempfile.TemporaryDirectory(prefix='huntlab-stdlib-round2-') as temp:
    execution.append(dict(name='shared_exact_setup_698_699', **run(blocks(698)[0], Path(temp))))
    assert execution[-1]['exit'] == 0
    checkout = Path(temp) / 'blog'
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip() == REV
    execution.append(dict(name='stdlib_no_pip', **run(".venv/bin/python -c 'import importlib.util; assert importlib.util.find_spec(\"pip\") is None'", checkout)))
    assert execution[-1]['exit'] == 0
    for post_id in (698, 699):
        commands = [b for b in blocks(post_id) if b.startswith('.venv/bin/python scripts/huntlab_wp_diagnostics.py')]
        assert len(commands) == 2
        for index, command in enumerate(commands):
            result = run(command, checkout)
            assert result['exit'] == (1 if index == 0 else 0)
            execution.append(dict(name=f'post_{post_id}_diagnostic_{index}', **result))
        execution.append(dict(name=f'post_{post_id}_exact_lab', **run(blocks(post_id)[-1], checkout)))
        assert execution[-1]['exit'] == 0
    for name in ('scripts/huntlab_wp_diagnostics.py', 'scripts/run_evidence_lab.py', 'tests/test_huntlab_wp_diagnostics.py'):
        assert (checkout / name).read_bytes() == (ROOT / name).read_bytes()
        source_hashes[name] = sha((checkout / name).read_bytes())

code = "python3 - <<'PY'\n" + (HERE / 'backup-example.py').read_text() + 'PY\n'
assert blocks(96).count(code) == 1
with tempfile.TemporaryDirectory(prefix='huntlab-json-reader-') as temp:
    cwd = Path(temp)
    execution.append(dict(name='post_96_exact_demo', **run(code, cwd)))
    assert execution[-1]['exit'] == 0 and not list(cwd.iterdir())
    good = [{'post_id': 1, 'title': 'Sample', 'original_content': '<p>Before</p>', 'updated_content': '<p>After</p>', 'targets': [2]}]
    cases = [('valid', good, 0), ('empty_original', [dict(good[0], original_content='')], 1),
             ('duplicate_ids', good + good, 1), ('bool_id', [dict(good[0], post_id=True)], 1),
             ('duplicate_target', [dict(good[0], targets=[2, 2])], 1),
             ('self_target', [dict(good[0], targets=[1])], 1),
             ('unchanged', [dict(good[0], updated_content='<p>Before</p>')], 1),
             ('empty_list', [], 1), ('missing_targets', [dict(good[0], targets=None)], 1)]
    for label, value, expected in cases:
        fixture = cwd / 'backup.json'
        fixture.write_text(json.dumps(value))
        before = fixture.read_bytes()
        actual = run(code.replace("python3 - <<'PY'", "python3 - \"backup.json\" <<'PY'", 1), cwd)
        assert actual['exit'] == expected, label
        assert fixture.read_bytes() == before and len(list(cwd.iterdir())) == 1
        execution.append(dict(name='post_96_file_' + label, fixture_sha256=sha(before), **actual))
    fixture.write_text('{invalid')
    actual = run(code.replace("python3 - <<'PY'", "python3 - \"backup.json\" <<'PY'", 1), cwd)
    assert actual['exit'] == 1
    execution.append(dict(name='post_96_malformed_json', fixture_sha256=sha(fixture.read_bytes()), **actual))
report = {'status': 'PROPOSED', 'checked_at': datetime.now(UTC).isoformat(), 'python': sys.version.split()[0],
          'revision': REV, 'manifest_sha256': sha((HERE / 'content-corrections.json').read_bytes()),
          'inventory_sha256': sha(inventory_path.read_bytes()), 'statuses': inventory['metadata']['statuses'],
          'gates': gates, 'execution': execution, 'source_hashes': source_hashes,
          'wordpress_writes': 0, 'approval': False}
(HERE / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
