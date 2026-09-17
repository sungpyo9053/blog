#!/usr/bin/env python3
"""One-time user-authorized four-slot launch. Does not change daily scheduling."""
import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import markdown
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publisher.config import WordPressConfig
from publisher.frontmatter import load_document
from publisher.service import DraftPublisher
from publisher.wordpress import WordPressClient
from scripts.editorial_gate import enforce_prepublication
from scripts.publication_notification import _save, notify_publication
from scripts.run_daily_pipeline import PipelineLock, TopicContext, validate_publish_contract
from scripts.run_evidence_deep_article import LOCK
from scripts.snapshot_topic_inventory import build_snapshot

BATCH = 'physical-ai-launch-20260917'
CATEGORIES = {'basics': '피지컬 AI 기초', 'principles': '원리·알고리즘',
              'tools': '프레임워크·라이브러리', 'lab': '실습·실험'}


class Text(HTMLParser):
    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.feed(value)

    def handle_data(self, data):
        self.parts.append(data)


def validate_identity(slot, metadata):
    if slot not in CATEGORIES:
        raise ValueError('unknown_launch_slot')
    expected = {'run_id': BATCH, 'topic_id': slot, 'source_id': f'huntlab:{BATCH}:{slot}',
                'category': CATEGORIES[slot], 'publish_mode': 'publish',
                'content_type': 'foundation_concept'}
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError('launch_identity_mismatch')
    if metadata.get('existing_post_id') != (761 if slot == 'basics' else None):
        raise ValueError('unexpected_update_target')
    return expected


def run(slot, apply=False):
    directory = ROOT / 'output' / BATCH / slot
    path = directory / 'publish.md'
    document = load_document(path)
    identity = validate_identity(slot, document.metadata)
    context = TopicContext(title=document.metadata['title'], run_id=BATCH, topic_id=slot,
                           directory=directory, category=CATEGORIES[slot],
                           tags=tuple(document.metadata['tags']), content_type='foundation_concept')
    digest = validate_publish_contract(context)
    client = WordPressClient(WordPressConfig.from_environment(ROOT / '.env'), max_retries=0)
    receipt = directory / 'launch-result.json'
    marker = directory / 'launch-attempt.json'
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        if previous.get('failed') is False:
            return {'status': 'already_published', 'publication': previous['publication']}
        raise ValueError('prior_launch_requires_reconciliation')
    if marker.exists():
        raise ValueError('prior_launch_requires_reconciliation')
    inventory = build_snapshot(client)
    _save(directory / 'inventory-prepublish.json', inventory)
    enforce_prepublication(path, directory / 'inventory-prepublish.json',
                           existing_post_id=document.metadata.get('existing_post_id'))
    if not apply:
        return {'status': 'validated', 'slot': slot, 'sha256': digest, 'wordpress_writes': 0}
    # Each fixed slot can cross the write boundary only once, even after a crash.
    _save(marker, {'batch': BATCH, 'slot': slot, 'sha256': digest,
                   'started_at': datetime.now(timezone.utc).isoformat()})
    result = {'run_id': BATCH, 'slot': slot, 'failed': True,
              'wordpress_write_count': 'unknown'}
    try:
        published = DraftPublisher(client, audit_log=directory / 'publisher-audit.jsonl').publish_file(
            path, reviewer_approved=True, review_path=directory / 'review.md',
            expected_identity=identity)
        _save(directory / 'publisher-result.json', published.to_dict())
        if published.status != 'Success' or not published.published_url:
            raise ValueError('publisher_failed')
        result['publication'] = {'post_id': published.post_id, 'url': published.published_url,
                                 'title': document.metadata['title']}
        result['wordpress_write_count'] = 1
        post = client.get_post(published.post_id)
        raw = post['content'].get('raw', '')
        expected_html = markdown.markdown(document.markdown, extensions=['extra', 'sane_lists'], output_format='html5')
        if Text(raw).parts != Text(expected_html).parts:
            raise ValueError('stored_body_mismatch')
        if post['status'] != 'publish' or not post.get('featured_media'):
            raise ValueError('stored_state_mismatch')
        media = client.request('GET', f'media/{post["featured_media"]}?context=edit')
        if not media.get('alt_text'):
            raise ValueError('missing_media_alt')
        media_url = media.get('source_url', '')
        if not media_url.startswith('https://huntlab.app/wp-content/uploads/'):
            raise ValueError('unexpected_media_url')
        if requests.get(media_url, timeout=30).status_code != 200:
            raise ValueError('media_not_public')
        url = published.published_url
        if not url.startswith('https://huntlab.app/'):
            raise ValueError('unexpected_public_url')
        response = requests.get(url, timeout=30)
        public_text = ' '.join(''.join(Text(response.text).parts).split())
        segments = [' '.join(p.split()) for p in Text(expected_html).parts if len(p.strip()) > 25]
        if response.status_code != 200 or document.metadata['title'] not in public_text or not all(p in public_text for p in segments):
            raise ValueError('public_body_mismatch')
        links = re.findall(r'\]\((https://[^\s)]+)\)', document.markdown)
        if not links or not all(link in html.unescape(response.text) for link in links):
            raise ValueError('public_evidence_link_mismatch')
        result.update(failed=False, deep_article='published',
                      public_audit={'url': url, 'http_status': 200, 'title_present': True,
                                    'evidence_links_present': True, 'body_verified': True,
                                    'stored_body_sha256': hashlib.sha256(raw.encode()).hexdigest()})
    except Exception as exc:
        result.update(error_type=type(exc).__name__, reason='launch_requires_reconciliation')
    _save(receipt, result)
    if not result['failed']:
        result['notification'] = notify_publication(result)
        _save(receipt, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('slot', choices=CATEGORIES)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    lock = PipelineLock(LOCK)
    try:
        lock.acquire()
        result = run(args.slot, args.apply)
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(int(result.get('failed', False)))
    finally:
        lock.release()
