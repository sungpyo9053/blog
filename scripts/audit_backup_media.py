#!/usr/bin/env python3
"""Verify restored WordPress attachment files against a pre-restore SHA manifest.

This checks original attachment files only, not a complete WordPress recovery.
No WordPress API calls, SQL execution, writes to uploads, or network access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


def attachment_path(root: Path, relative: str) -> Path:
    if root.is_symlink():
        raise ValueError('symlink_uploads_root')
    if not isinstance(relative, str) or not relative or '\\' in relative or '\x00' in relative:
        raise ValueError('invalid_attachment_path')
    part = PurePosixPath(relative)
    if part.is_absolute() or '..' in part.parts or str(part) != relative:
        raise ValueError('invalid_attachment_path')
    path = root / relative
    # Do not follow symlinks, even when they currently point within the root.
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            raise ValueError('symlink_attachment')
        cursor = cursor.parent
    if root.resolve() not in path.resolve().parents:
        raise ValueError('attachment_outside_uploads')
    return path


def file_hash(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def make_manifest(root: Path, references: list[str]) -> dict:
    if not isinstance(references, list) or not references:
        raise ValueError('attachment_references_required')
    if any(not isinstance(relative, str) for relative in references):
        raise ValueError('invalid_attachment_reference')
    files = []
    for relative in sorted(set(references)):
        path = attachment_path(root, relative)
        if not path.is_file():
            raise ValueError('source_attachment_missing')
        files.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': file_hash(path)})
    return {'schema_version': 1, 'scope': 'original_attachment_files',
            'reference_count': len(references), 'files': files}


def audit_manifest(root: Path, manifest: dict) -> dict:
    if (not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int
            or manifest['schema_version'] != 1 or manifest.get('scope') != 'original_attachment_files'
            or not isinstance(manifest.get('files'), list) or not manifest['files']):
        raise ValueError('invalid_manifest')
    files = manifest['files']
    if type(manifest.get('reference_count')) is not int or manifest['reference_count'] < len(files):
        raise ValueError('invalid_reference_count')
    failures, seen = [], set()
    for row in files:
        if not isinstance(row, dict):
            raise ValueError('invalid_file_record')
        relative = row.get('path')
        path = attachment_path(root, relative)
        if relative in seen or not re.fullmatch(r'[a-f0-9]{64}', str(row.get('sha256', ''))):
            raise ValueError('invalid_or_duplicate_file_record')
        if type(row.get('bytes')) is not int or row['bytes'] < 0:
            raise ValueError('invalid_file_size')
        seen.add(relative)
        if not path.is_file():
            failures.append({'path': relative, 'reason': 'missing_file'})
        elif path.stat().st_size != row['bytes'] or file_hash(path) != row['sha256']:
            failures.append({'path': relative, 'reason': 'content_mismatch'})
    return {'passed': not failures, 'checked_files': len(files), 'failures': failures,
            'scope': manifest['scope'], 'whole_site_restore_verified': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('snapshot', 'audit'))
    parser.add_argument('--uploads', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True,
                        help='snapshot: JSON array of attachment paths; audit: manifest JSON')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text())
    result = make_manifest(args.uploads, payload) if args.operation == 'snapshot' else audit_manifest(args.uploads, payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'operation': args.operation, 'passed': result.get('passed', True),
                      'files': len(result.get('files', [])) if args.operation == 'snapshot' else result['checked_files'],
                      'whole_site_restore_verified': False}))
    return int(result.get('passed') is False)


if __name__ == '__main__':
    raise SystemExit(main())
