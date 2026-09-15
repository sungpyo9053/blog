"""Read-only validation of proposed HTML and embedded reader commands."""
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.editorial_gate import inspect_article

def sha(data):
    return hashlib.sha256(data).hexdigest()

manifest = json.loads((HERE / 'content-corrections.json').read_text())
inventory_path = ROOT / 'output/quality99-editorial-inventory.json'
inventory = json.loads(inventory_path.read_text())
by_id = {p['post_id']: p for p in inventory['posts']}
for row in manifest['posts']:
    for kind in ('before', 'after'):
        data = (HERE / row[kind + '_file']).read_bytes()
        assert sha(data) == row[kind + '_sha256']
    assert by_id[row['post_id']]['content'] == (HERE / row['before_file']).read_text()
    assert by_id[row['post_id']]['slug'] == row['slug']
    by_id[row['post_id']]['content'] = (HERE / row['after_file']).read_text()

results = []
for row in manifest['posts']:
    body = (HERE / row['after_file']).read_text()
    result = inspect_article(body, inventory, existing_post_id=row['post_id'])
    assert result['passed'], result
    result['post_id'] = row['post_id']
    if row['post_id'] in (132, 301):
        name = 'pagination' if row['post_id'] == 132 else 'summary'
        source = (HERE / (name + '-example.py')).read_text()
        blocks = [html.unescape(x) for x in re.findall(r'<pre><code class="language-bash">(.*?)</code></pre>', body, re.S)]
        exact = "python3 - <<'PY'\n" + source + 'PY\n'
        assert blocks.count(exact) == 1
        with tempfile.TemporaryDirectory(prefix='huntlab-reader-check-') as workdir:
            env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'])
            run = subprocess.run(['bash'], input=exact, text=True, cwd=workdir, env=env, capture_output=True, timeout=120)
            assert not list(Path(workdir).iterdir()), 'reader example wrote files'
        assert run.returncode == 0, run.stderr
        result.update(block_sha256=sha(exact.encode()), exit_code=run.returncode, stdout=run.stdout, stderr=run.stderr, reader_files_written=0)
    else:
        before = (HERE / row['before_file']).read_text()
        for pattern in (r'<pre><code class="language-bash">.*?</code></pre>', r'(?:href|src)="[^"]*"'):
            assert re.findall(pattern, before, re.S) == re.findall(pattern, body, re.S)
        result['commands_links_media_preserved'] = True
    results.append(result)
report = {'checked_at': datetime.now(UTC).isoformat(), 'python': sys.version.split()[0],
          'manifest_sha256': sha((HERE / 'content-corrections.json').read_bytes()),
          'inventory_sha256': sha(inventory_path.read_bytes()),
          'statuses': inventory['metadata']['statuses'], 'wordpress_writes': 0,
          'final_publication_approval': False, 'results': results}
(HERE / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
