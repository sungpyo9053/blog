#!/usr/bin/env python3
"""Four fixed existing posts, reviewed content-only copy edits. Dry-run by default.

No media uploads or new posts. Durable attempts are never automatically repeated.
The final GET/POST conflict check is not an atomic WordPress compare-and-swap.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

import markdown
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publisher.config import WordPressConfig
from publisher.frontmatter import load_document
from publisher.wordpress import WordPressClient
from scripts.editorial_gate import inspect_article, style_preservation
from scripts.evidence_topic_miner import contains_secret, normalized_identity
from scripts.physical_ai_quality_gate import enforce_quality
from scripts.run_daily_pipeline import PipelineLock
from scripts.run_evidence_deep_article import LOCK
from scripts.snapshot_topic_inventory import build_snapshot
from scripts.weekly_editorial_updates import _metadata, _source_state, _save_exclusive

ORIGINAL = 'physical-ai-launch-20260917'
BATCH = 'physical-ai-natural-20260917'
SLOTS = {'basics': 761, 'principles': 773, 'tools': 768, 'lab': 771}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def private_directory(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


class Elements(HTMLParser):
    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.images, self.image_tags = [], [], [], []
        self.feed(value)

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag == 'img':
            self.images.append(attrs)
            self.image_tags.append(self.get_starttag_text())

    handle_startendtag = handle_starttag


def owned(url, media=False):
    parsed = urlsplit(url)
    require(parsed.scheme == 'https' and parsed.netloc == 'huntlab.app'
            and not parsed.username and not parsed.query and not parsed.fragment,
            'unowned_url')
    if media:
        require(parsed.path.startswith('/wp-content/uploads/'), 'unowned_media_url')


def render(body):
    return markdown.markdown(body, extensions=['extra', 'sane_lists'], output_format='html5')


def render_reusing_images(original_body, revised_body, current_html):
    """Map the unchanged ordered original image tags to current REST tags.

    Require that the immutable original reproduces ALL stored HTML, not only
    filenames/ALT matches. Reuse exact stored tags and URLs in the new body.
    """
    old_render, new_render = render(original_body), render(revised_body)
    old, new, current = Elements(old_render), Elements(new_render), Elements(current_html)
    require(old.images == new.images, 'markdown_images_changed')
    require(len(old.images) == len(current.images), 'stored_image_count_mismatch')
    for source, stored in zip(old.images, current.images):
        require(source.get('alt') == stored.get('alt'), 'stored_image_alt_mismatch')
        owned(stored.get('src', ''), media=True)
    for original_tag, current_tag in zip(old.image_tags, current.image_tags):
        old_render = old_render.replace(original_tag, current_tag, 1)
        new_render = new_render.replace(original_tag, current_tag, 1)
    require(old_render.strip() == current_html.strip(), 'original_stored_body_mismatch')
    return new_render


def collect_snapshot(client, root=ROOT):
    directory = Path(root) / 'output' / BATCH / 'snapshot'
    private_directory(directory)
    require(not (directory / 'inventory.json').exists(), 'snapshot_already_exists')
    inventory = build_snapshot(client)
    for slot, post_id in SLOTS.items():
        post = client.get_post(post_id)
        require(post.get('id') == post_id and post.get('status') == 'publish', 'snapshot_target_not_published')
        raw = post.get('content', {}).get('raw')
        require(isinstance(raw, str) and not contains_secret(raw), 'snapshot_unsafe_body')
        _save_exclusive(directory / f'{slot}.json', post)
    _save_exclusive(directory / 'inventory.json', inventory)
    return {'status': 'snapshot_saved', 'posts': 4, 'wordpress_writes': 0}


def review_identity(path, *, slot, post, digest, before_sha):
    text = path.read_text()
    # Deliberately simple, unambiguous machine-readable approval fields.
    pairs = re.findall(r'^\s*(?:- )?([a-z_]+):\s*(.*?)\s*$', text, re.M)
    fields = {}
    for key, value in pairs:
        require(key not in fields, 'duplicate_review_field')
        fields[key] = value
    expected = {'verdict': 'APPROVED', 'publish_sha256': digest,
                'post_id': str(post['id']), 'title': post['title']['raw'],
                'slug': post['slug'], 'before_sha256': before_sha,
                'revision_batch': BATCH, 'topic_id': slot}
    require(all(fields.get(key) == value for key, value in expected.items()), 'review_identity_mismatch')


def public_verify(client, post, after, get=requests.get):
    url = post['link']
    owned(url)
    response = get(url, timeout=30, allow_redirects=False,
                   headers={'Cache-Control': 'no-cache'})
    require(response.status_code == 200, 'public_http_failed')
    page, expected = Elements(response.text), Elements(after)
    combined = ' '.join(''.join(page.parts).split())
    require(' '.join(post['title']['raw'].split()) in combined, 'public_title_missing')
    # Every text node, including code and short numeric table cells, must occur
    # in order. Whitespace only is normalized, not numbers or punctuation.
    cursor = 0
    for part in expected.parts:
        segment = ' '.join(part.split())
        if not segment:
            continue
        found = combined.find(segment, cursor)
        require(found >= 0, 'public_body_missing')
        cursor = found + len(segment)
    require(all(link in page.links for link in expected.links), 'public_links_missing')
    require(all(any(item.get('src') == expected_image.get('src')
                        and item.get('alt') == expected_image.get('alt')
                        for item in page.images)
                for expected_image in expected.images), 'public_body_media_missing')
    media_id = post.get('featured_media')
    require(type(media_id) is int and media_id > 0, 'featured_media_missing')
    media = client.request('GET', f'media/{media_id}?context=edit')
    require(media.get('id') == media_id and bool(media.get('alt_text')), 'featured_media_invalid')
    media_url = media.get('source_url', '')
    urls = [media_url] + [item.get('src', '') for item in expected.images]
    for value in dict.fromkeys(urls):
        owned(value, media=True)
        require(get(value, timeout=30, allow_redirects=False).status_code == 200,
                'public_media_http_failed')
    require(any(image.get('src') == media_url for image in page.images), 'public_featured_media_missing')
    return {'url': url, 'http_status': 200, 'body_verified': True,
            'links_verified': True, 'media_verified': True}


def revise(slot, *, apply=False, client=None, root=ROOT, snapshot_builder=build_snapshot,
           quality_checker=enforce_quality, public_checker=public_verify):
    require(slot in SLOTS and type(apply) is bool, 'invalid_slot_or_apply')
    root = Path(root)
    client = client or WordPressClient(WordPressConfig.from_environment(root / '.env'), max_retries=0)
    require(client.config.base_url == 'https://huntlab.app' and client.max_retries == 0,
            'unsafe_client_configuration')
    directory = root / 'output' / BATCH / slot
    private_directory(directory)
    receipt, attempt = directory / 'revision-result.json', directory / 'revision-attempt.json'
    if receipt.exists():
        prior = json.loads(receipt.read_text())
        require(prior.get('status') == 'updated', 'prior_result_requires_reconciliation')
        return {**prior, 'status': 'already_updated', 'wordpress_writes': 0}
    require(not attempt.exists(), 'prior_attempt_requires_reconciliation')
    path = directory / 'publish.md'
    original_path = root / 'output' / ORIGINAL / slot / 'publish.md'
    original, revised = load_document(original_path), load_document(path)
    require(original.metadata == revised.metadata, 'metadata_changed')
    quality = quality_checker(path, directory / 'physical-ai-quality-review.json')
    require(quality.get('schema_version') == 2 and isinstance(quality.get('naturalness'), dict),
            'naturalness_review_required')
    markdown_check = style_preservation(original_path.read_text(), path.read_text())
    require(markdown_check['passed'], 'markdown_protected_content_changed')
    post_id = SLOTS[slot]
    source = json.loads((root / 'output' / BATCH / 'snapshot' / f'{slot}.json').read_text())
    before = client.get_post(post_id)
    require(source.get('id') == post_id and before.get('id') == post_id
            and before.get('status') == 'publish', 'target_identity_mismatch')
    require(_source_state(source) == _source_state(before), 'snapshot_conflict')
    require(original.metadata['title'] == before['title']['raw']
            and original.metadata['slug'] == before['slug'], 'original_identity_mismatch')
    raw = before['content']['raw']
    digest = sha(path.read_text())
    review_identity(directory / 'review.md', slot=slot, post=before, digest=digest, before_sha=sha(raw))
    after = render_reusing_images(original.markdown, revised.markdown, raw)
    require(after != raw and not contains_secret(after), 'empty_or_unsafe_change')
    html_check = style_preservation(raw, after)
    require(html_check['passed'], 'html_protected_content_changed')
    inventory = snapshot_builder(client)
    require(inspect_article(after, inventory, existing_post_id=post_id)['passed'], 'editorial_inventory_failed')
    matches = [p for p in inventory['posts'] if p['post_id'] == post_id]
    require(len(matches) == 1 and matches[0]['content'] == raw
            and matches[0]['status'] == 'publish', 'inventory_target_conflict')
    require(not any(p['post_id'] != post_id and (
        normalized_identity(p.get('title', '')) == normalized_identity(before['title']['raw'])
        or normalized_identity(p.get('slug', '')) == normalized_identity(before['slug']))
        for p in inventory['posts']), 'duplicate_identity')
    result = {'status': 'validated', 'slot': slot, 'post_id': post_id, 'wordpress_writes': 0,
              'publish_sha256': digest, 'before_sha256': sha(raw), 'after_sha256': sha(after),
              'markdown_preservation': markdown_check, 'html_preservation': html_check}
    if not apply:
        return result
    backup = directory / 'revision-before.json'
    if backup.exists():
        require(json.loads(backup.read_text()) == before, 'backup_conflict')
    else:
        _save_exclusive(backup, before)
    require(_source_state(client.get_post(post_id)) == _source_state(before), 'prewrite_conflict')
    _save_exclusive(attempt, {**result, 'attempted_at': datetime.now(timezone.utc).isoformat()})
    try:
        # Any exception is uncertain; no automatic rollback or POST retry.
        client.request('POST', f'posts/{post_id}', payload={'content': after}, expected=(200,))
        actual = client.get_post(post_id)
        require(actual.get('content', {}).get('raw') == after, 'readback_body_mismatch')
        require(_metadata(actual) == _metadata(before), 'readback_metadata_mismatch')
        audit = public_checker(client, actual, after)
        result.update(status='updated', wordpress_writes=1, public_audit=audit,
                      completed_at=datetime.now(timezone.utc).isoformat())
    except Exception as error:
        result.update(status='update_unconfirmed', wordpress_writes='unknown',
                      error_type=type(error).__name__, reason='requires_read_only_reconciliation')
    _save_exclusive(receipt, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('slot', choices=(*SLOTS, 'snapshot'))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    require(not (args.slot == 'snapshot' and args.apply), 'snapshot_cannot_apply')
    lock = PipelineLock(LOCK)
    try:
        lock.acquire()
        client = WordPressClient(WordPressConfig.from_environment(ROOT / '.env'), max_retries=0)
        result = collect_snapshot(client) if args.slot == 'snapshot' else revise(args.slot, apply=args.apply, client=client)
        print(json.dumps(result, ensure_ascii=False))
        return int(result['status'] == 'update_unconfirmed')
    finally:
        lock.release()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}), file=sys.stderr)
        raise SystemExit(1)
