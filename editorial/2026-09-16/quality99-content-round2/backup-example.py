import json
import sys
from pathlib import Path

def check(rows):
    if not isinstance(rows, list) or not rows:
        return False
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            return False
        post_id = row.get('post_id')
        if type(post_id) is not int or post_id <= 0 or post_id in seen:
            return False
        seen.add(post_id)
        if any(not isinstance(row.get(k), str) or not row[k].strip()
               for k in ('title', 'original_content', 'updated_content')):
            return False
        targets = row.get('targets')
        if not isinstance(targets, list) or not targets:
            return False
        if any(type(t) is not int or t <= 0 or t == post_id for t in targets):
            return False
        if len(set(targets)) != len(targets):
            return False
        if row['original_content'] == row['updated_content']:
            return False
    return True

good = [{'post_id': 1, 'title': 'Sample', 'original_content': '<p>Before</p>',
         'updated_content': '<p>Before</p><p>Related</p>', 'targets': [2]}]
bad = [dict(good[0], original_content='')]
if len(sys.argv) == 1:
    for label, rows, expected in [('valid', good, True), ('missing_original', bad, False)]:
        result = check(rows)
        print(f'{label}: passed={str(result).lower()}')
        assert result is expected
else:
    try:
        with Path(sys.argv[1]).open('rb') as source:
            raw = source.read(10_000_001)
        if len(raw) > 10_000_000:
            raise ValueError('too large')
        passed = check(json.loads(raw))
    except (OSError, ValueError, RecursionError):
        passed = False
    print(json.dumps({'passed': passed}))
    sys.exit(0 if passed else 1)
