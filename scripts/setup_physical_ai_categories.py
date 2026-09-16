#!/usr/bin/env python3
"""Explicit site-operator taxonomy setup, never called by Publisher."""
import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient

CATEGORIES = {
    'physical-ai-basics': '피지컬 AI 기초',
    'physical-ai-principles': '원리·알고리즘',
    'physical-ai-frameworks': '프레임워크·라이브러리',
    'physical-ai-experiments': '실습·실험',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    client = WordPressClient(WordPressConfig.from_environment(ROOT / '.env'))
    state = ROOT / 'output/physical-ai-transition/categories'
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    result = []
    for slug, name in CATEGORIES.items():
        rows = client.request('GET', f'categories?slug={slug}&context=edit')
        if len(rows) > 1 or rows and rows[0]['name'] != name:
            raise ValueError('Existing category conflicts with approved taxonomy')
        if not rows and args.apply:
            created = client.request('POST', 'categories', payload={'slug': slug, 'name': name}, expected=(201,))
            rows = client.request('GET', f'categories?slug={slug}&context=edit')
            if len(rows) != 1 or rows[0]['id'] != created['id'] or rows[0]['name'] != name:
                raise ValueError('Category readback failed; inspect before retrying')
        receipt = {'slug': slug, 'name': name, 'id': rows[0]['id'] if rows else None,
                   'status': 'verified' if rows else 'would_create', 'checked_at': datetime.now(UTC).isoformat()}
        if args.apply:
            path = state / f'{slug}.json'
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
                json.dump(receipt, stream, ensure_ascii=False, indent=2)
        result.append(receipt)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
