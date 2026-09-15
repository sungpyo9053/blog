#!/usr/bin/env python3
"""Apply independently approved existing-post body corrections, never create posts.

Dry-run by default. An ambiguous prior attempt is read back, never blindly retried.
WordPress has no compare-and-swap body write here: pause other editors for the run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient
from scripts.editorial_gate import inspect_article
from scripts.snapshot_topic_inventory import build_snapshot, plain


class CorrectionError(ValueError):
    pass


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def private_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('x', encoding='utf-8') as handle:
        os.chmod(path, 0o600)
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())


def protected(post):
    keys = ('id', 'status', 'slug', 'title', 'categories', 'tags', 'featured_media',
            'author', 'date', 'date_gmt', 'excerpt', 'meta', 'link')
    return {key: post[key] for key in keys}


def load_approved(manifest_path, approval_path):
    raw = manifest_path.read_text(encoding='utf-8')
    approval = approval_path.read_text(encoding='utf-8')
    digest = sha(raw)
    if not re.search(r'^status: APPROVED$', approval, re.M) or not re.search(
            '^manifest_sha256: ' + digest + '$', approval, re.M):
        raise CorrectionError('Approval does not match exact manifest')
    rows = json.loads(raw)['posts']
    if not isinstance(rows, list) or not rows:
        raise CorrectionError('Empty or invalid correction manifest')
    seen = set()
    prepared = []
    for row in rows:
        post_id = row.get('post_id')
        if type(post_id) is not int or post_id <= 0 or post_id in seen:
            raise CorrectionError('Invalid or repeated post ID')
        seen.add(post_id)
        values = dict(row)
        for kind in ('before', 'after'):
            path = (manifest_path.parent / row[kind + '_file']).resolve()
            if path.parent != manifest_path.parent.resolve():
                raise CorrectionError('Correction path escapes manifest directory')
            body = path.read_text(encoding='utf-8')
            if not body.strip() or sha(body) != row[kind + '_sha256']:
                raise CorrectionError('Body hash mismatch: ' + str(post_id))
            values[kind] = body
        if row['before_sha256'] == row['after_sha256']:
            raise CorrectionError('Correction changes nothing')
        prepared.append(values)
    return digest, prepared


def apply_corrections(client, manifest_path, approval_path, receipt_dir, *, apply=False, inventory=None):
    if client.max_retries != 0:
        raise CorrectionError('Writes require max_retries=0')
    digest, rows = load_approved(manifest_path, approval_path)
    inventory = inventory if inventory is not None else build_snapshot(client)
    # Check the final combined set, not five independent old snapshots.
    final_inventory = json.loads(json.dumps(inventory))
    by_id = {row['post_id']: row for row in rows}
    for post in final_inventory.get('posts', []):
        if post['post_id'] in by_id:
            post['content'] = by_id[post['post_id']]['after']
    for row in rows:
        check = inspect_article(row['after'], final_inventory, existing_post_id=row['post_id'])
        if not check['passed']:
            raise CorrectionError('Editorial gate failed: ' + str(row['post_id']) + ':' + ','.join(check['failures']))
        matches = [p for p in inventory['posts'] if p['post_id'] == row['post_id']]
        if len(matches) != 1:
            raise CorrectionError('Target absent from full inventory')
        for other in inventory['posts']:
            if other['post_id'] != row['post_id'] and (
                plain(other['title']).casefold() == plain(row['title']).casefold()
                or other['slug'].casefold() == row['slug'].casefold()
            ):
                raise CorrectionError('Another post has target title or slug')
    # All identities, bodies and existing receipts preflight before any write.
    state = []
    for row in rows:
        post_id = row['post_id']
        current = client.get_post(post_id)
        if current['id'] != post_id or current['status'] != 'publish' or current['slug'] != row['slug'] or plain(current['title']['raw']) != row['title']:
            raise CorrectionError('Target identity changed: ' + str(post_id))
        backup_path = receipt_dir / f'{post_id}.before.json'
        attempt_path = receipt_dir / f'{post_id}.attempt.json'
        done_path = receipt_dir / f'{post_id}.verified.json'
        attempted = attempt_path.exists()
        if done_path.exists() and not attempted:
            raise CorrectionError('Completion without durable attempt')
        if attempted:
            attempt = json.loads(attempt_path.read_text())
            if attempt.get('manifest_sha256') != digest or not backup_path.exists():
                raise CorrectionError('Prior attempt belongs to a different plan')
            backup = json.loads(backup_path.read_text())
            if current['content']['raw'] != row['after'] or protected(current) != protected(backup):
                raise CorrectionError('Unresolved prior attempt; inspect and recover manually')
        else:
            if current['content']['raw'] != row['before']:
                raise CorrectionError('Stale body or rendered/raw mismatch: ' + str(post_id))
            backup = current
            if backup_path.exists() and json.loads(backup_path.read_text()) != current:
                raise CorrectionError('Existing backup differs from current post')
        state.append((row, backup, attempted, backup_path, attempt_path, done_path))
    if not apply:
        return {'status': 'preflight_passed', 'wordpress_writes': 0, 'posts': len(rows)}
    for row, backup, attempted, backup_path, attempt_path, done_path in state:
        if not backup_path.exists():
            private_json(backup_path, backup)
    writes = 0
    for row, backup, attempted, backup_path, attempt_path, done_path in state:
        post_id = row['post_id']
        if not attempted:
            latest = client.get_post(post_id)
            if latest['content']['raw'] != row['before'] or protected(latest) != protected(backup):
                raise CorrectionError('Post changed since preflight: ' + str(post_id))
            private_json(attempt_path, {'manifest_sha256': digest, 'post_id': post_id,
                                       'attempted_at': datetime.now(UTC).isoformat()})
            writes += 1
            try:
                client.request('POST', f'posts/{post_id}', payload={'content': row['after']}, expected=(200,))
            except Exception:
                # Never emit response bodies or credentials. Read-back resolves success.
                pass
        try:
            actual = client.get_post(post_id)
        except Exception as error:
            raise CorrectionError('Read-back unavailable; do not retry write: ' + str(post_id)) from error
        if actual['content']['raw'] != row['after'] or protected(actual) != protected(backup):
            raise CorrectionError('Read-back mismatch; do not retry write: ' + str(post_id))
        if not done_path.exists():
            private_json(done_path, {'manifest_sha256': digest, 'post_id': post_id,
                                    'after_sha256': sha(actual['content']['raw']),
                                    'status': 'verified', 'verified_at': datetime.now(UTC).isoformat()})
    return {'status': 'verified', 'wordpress_writes': writes, 'posts': len(rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--approval', type=Path, required=True)
    parser.add_argument('--receipts', type=Path, required=True)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    config = WordPressConfig.from_environment(args.env_file)
    if config.base_url != 'https://huntlab.app':
        raise CorrectionError('Unexpected target site')
    print(json.dumps(apply_corrections(WordPressClient(config, max_retries=0), args.manifest,
                                     args.approval, args.receipts, apply=args.apply), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Error strings from HTTP/auth libraries can contain secrets.
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}), file=sys.stderr)
        raise SystemExit(1)
