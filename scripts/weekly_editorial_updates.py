"""Bounded reviewed paragraph updates. No drafting, creation, or automatic retry."""
from __future__ import annotations

import fcntl
import hashlib
import html
import json
import os
import re
import unicodedata
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from scripts.editorial_gate import inspect_article, prose, style_preservation
from scripts.evidence_topic_miner import contains_secret, normalized_identity
from scripts.setup_physical_ai_categories import CATEGORIES


def sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def action_hash(action):
    return sha256(json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def require(condition, code):
    if not condition:
        raise ValueError(code)


def _save_exclusive(path, data):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _owned_url(url):
    parsed = urlsplit(url)
    require(parsed.scheme == 'https' and parsed.netloc == 'huntlab.app'
            and not parsed.username and not parsed.fragment, 'unsafe_public_url')


def _public_verify(url, paragraph):
    _owned_url(url)
    request = Request(url, headers={'User-Agent': 'HuntLab-Weekly-Editorial/1.0', 'Cache-Control': 'no-cache'})
    with build_opener(_NoRedirect()).open(request, timeout=30) as response:
        require(response.status == 200, 'public_http_failed')
        page = response.read(4_000_001)
        require(len(page) <= 4_000_000, 'public_body_too_large')
        require(prose(paragraph) in prose(page.decode('utf-8')), 'public_paragraph_missing')
    return {'http_status': 200, 'paragraph_present': True, 'url': url}


class _Context(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in {'img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'track', 'col'}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]


def _review(action, review, after, before):
    require(isinstance(review, dict), 'review_required')
    require(review.get('verdict') == 'APPROVED', 'review_not_approved')
    require(type(review.get('post_id')) is int and review['post_id'] == before['id']
            and review.get('title') == before.get('title', {}).get('raw')
            and review.get('slug') == before.get('slug'), 'review_target_mismatch')
    require(review.get('action_sha256') == action_hash(action)
            and review.get('after_sha256') == sha256(after), 'review_hash_mismatch')
    writer, reviewer = review.get('writer_id'), review.get('reviewer_id')
    require(isinstance(writer, str) and writer.strip() and isinstance(reviewer, str)
            and reviewer.strip() and writer.strip().casefold() != reviewer.strip().casefold(), 'independent_review_required')
    gates = review.get('gates')
    require(isinstance(gates, dict) and set(gates) == {f'gate{i}' for i in range(1, 9)}
            and all(value is True for value in gates.values()), 'mandatory_gates_failed')
    items = review.get('items')
    require(isinstance(items, list) and len(items) == 20, 'quality_items_required')
    require(all(isinstance(item, dict) and type(item.get('id')) is int
                and type(item.get('score')) is int and 0 <= item['score'] <= 5
                and all(isinstance(item.get(field), str) and item[field].strip()
                        for field in ('reason', 'body_location', 'evidence_ref'))
                for item in items), 'invalid_quality_item')
    require({item['id'] for item in items} == set(range(1, 21)), 'invalid_quality_ids')
    require(type(review.get('total')) is int and review['total'] == sum(item['score'] for item in items)
            and review['total'] >= 99, 'quality_below_threshold')
    from scripts.physical_ai_quality_gate import enforce_naturalness
    enforce_naturalness(review.get('naturalness'), items)


def _metadata(post):
    # Freeze stored settings, not generated excerpt/SEO markup or link nonces.
    # Confirmed against the private authenticated draft-761 REST readback.
    fields = ('id', 'status', 'type', 'slug', 'author', 'categories', 'tags',
              'featured_media', 'meta', 'aioseo_meta_data', 'date', 'date_gmt',
              'password', 'comment_status', 'ping_status', 'template', 'sticky',
              'format', 'link', 'jetpack_sharing_enabled')
    result = {key: post[key] for key in fields if key in post}
    for key in ('title', 'excerpt'):
        if key in post:
            result[key] = {'raw': post[key].get('raw')}
    return result


def _source_state(post):
    return (_metadata(post), post.get('content', {}).get('raw'),
            post.get('modified'), post.get('modified_gmt'))


def _has_control(value):
    if isinstance(value, str):
        return any(unicodedata.category(character) in {'Cc', 'Cf', 'Cs'} for character in value)
    if isinstance(value, dict):
        return any(_has_control(key) or _has_control(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_control(item) for item in value)
    return False


def apply_reviewed_update(client, *, action: dict, review: dict, run_dir: Path,
                          inventory: dict, apply: bool) -> dict:
    """Fail closed; exceptions never expose API response bodies or credentials.

    Persist and reuse run_dir on retries. An attempted write is never repeated,
    even when its response, readback, or final receipt was lost.
    """
    try:
        require(type(apply) is bool, 'invalid_apply_flag')
        require(isinstance(action, dict) and set(action) == {
            'post_id', 'before_sha256', 'old_paragraph', 'new_paragraph', 'reason', 'evidence_refs'}, 'invalid_action')
        require(len(json.dumps(action, ensure_ascii=False).encode('utf-8')) <= 65536, 'action_too_large')
        require(not _has_control(action), 'action_control_characters')
        post_id = action['post_id']
        require(type(post_id) is int and post_id > 0, 'invalid_post_id')
        require(all(isinstance(action[key], str) and action[key].strip()
                    for key in ('before_sha256', 'old_paragraph', 'new_paragraph', 'reason')), 'invalid_action_text')
        refs = action['evidence_refs']
        require(isinstance(refs, list) and refs and all(isinstance(ref, str) and ref.strip() for ref in refs), 'evidence_required')
        require(not contains_secret(json.dumps({'action': action, 'review': review}, ensure_ascii=False)), 'possible_secret')
        old, new = action['old_paragraph'], action['new_paragraph']
        # Plain paragraphs only: no nested code, links, markup, or entity-smuggled tags.
        require(all(re.fullmatch(r'<p>[^<>]+</p>', paragraph, re.S)
                    and '<' not in html.unescape(paragraph[3:-4])
                    and '>' not in html.unescape(paragraph[3:-4])
                    and len(prose(paragraph)) >= 20 for paragraph in (old, new)), 'plain_paragraph_required')
        require(old != new, 'no_change')
        directory = Path(run_dir)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        with os.fdopen(os.open(directory / 'update.lock', os.O_CREAT | os.O_RDWR, 0o600), 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            key = action_hash(action)
            receipt = directory / f'{key}.result.json'
            marker = directory / f'{key}.attempt.json'
            if receipt.exists():
                try:
                    saved_receipt = json.loads(receipt.read_text())
                    require(saved_receipt.get('action_sha256') == key
                            and saved_receipt.get('status') == 'updated', 'invalid_receipt')
                    return {**saved_receipt, 'status': 'already_updated',
                            'wp_write_count': 0, 'previous_wp_write_count': saved_receipt.get('wp_write_count', 1)}
                except Exception:
                    return {'status': 'update_unconfirmed', 'post_id': post_id,
                            'reason': 'invalid_receipt_requires_reconciliation'}
            if marker.exists():
                return {'status': 'update_unconfirmed', 'post_id': post_id, 'reason': 'prior_attempt_requires_reconciliation'}
            before = client.request('GET', f'posts/{post_id}?context=edit')
            require(before.get('id') == post_id and before.get('status') == 'publish', 'published_target_required')
            raw = before.get('content', {}).get('raw')
            require(isinstance(raw, str) and sha256(raw) == action['before_sha256'], 'source_hash_conflict')
            require(not contains_secret(raw), 'possible_source_secret')
            _owned_url(before.get('link', ''))
            approved = set()
            for slug, name in CATEGORIES.items():
                rows = client.request('GET', f'categories?slug={slug}&context=edit')
                require(isinstance(rows, list) and len(rows) <= 1, 'ambiguous_category')
                if rows:
                    require(rows[0].get('slug') == slug and rows[0].get('name') == name
                            and type(rows[0].get('id')) is int, 'category_identity_mismatch')
                    approved.add(rows[0]['id'])
            require(bool(approved.intersection(before.get('categories', []))), 'physical_category_required')
            require(raw.count(old) == 1, 'paragraph_not_unique')
            context = _Context()
            context.feed(raw[:raw.index(old)])
            require(not set(context.stack).intersection({'pre', 'code', 'table', 'blockquote', 'q', 'script', 'style', 'math'}), 'protected_paragraph_context')
            after = raw.replace(old, new, 1)
            require(re.findall(r'<[^>]+>', raw) == re.findall(r'<[^>]+>', after), 'markup_changed')
            require(style_preservation(raw, after)['passed'], 'protected_content_changed')
            require(inspect_article(after, inventory, existing_post_id=post_id)['passed'], 'inventory_or_duplicate_failed')
            target_rows = [row for row in inventory['posts'] if row['post_id'] == post_id]
            require(len(target_rows) == 1 and target_rows[0]['status'] == 'publish'
                    and target_rows[0]['content'] == raw, 'inventory_target_conflict')
            title = normalized_identity(prose(before.get('title', {}).get('raw', '')))
            slug = normalized_identity(before.get('slug', ''))
            require(bool(title and slug), 'target_identity_missing')
            require(not any(row['post_id'] != post_id and (
                normalized_identity(str(row.get('title', ''))) == title
                or normalized_identity(str(row.get('slug', ''))) == slug)
                for row in inventory['posts']), 'duplicate_target_identity')
            _review(action, review, after, before)
            result = {'status': 'dry_run', 'post_id': post_id, 'action_sha256': key,
                      'before_sha256': sha256(raw), 'after_sha256': sha256(after), 'wp_write_count': 0}
            if not apply:
                return result
            backup = directory / f'{key}.before.json'
            if backup.exists():
                require(_source_state(json.loads(backup.read_text())) == _source_state(before), 'backup_conflict')
            else:
                _save_exclusive(backup, before)
            fresh = client.request('GET', f'posts/{post_id}?context=edit')
            require(_source_state(fresh) == _source_state(before), 'concurrent_source_change')
            _save_exclusive(marker, {'status': 'attempting', 'post_id': post_id, 'action_sha256': key})
            try:
                retries = client.max_retries
                client.max_retries = 0
                try:
                    response = client.request('POST', f'posts/{post_id}', payload={'content': after}, expected=(200,))
                finally:
                    client.max_retries = retries
                require(isinstance(response, dict) and response.get('id') == post_id, 'post_response_mismatch')
                saved = client.request('GET', f'posts/{post_id}?context=edit')
                require(saved.get('content', {}).get('raw') == after, 'content_readback_mismatch')
                require(_metadata(saved) == _metadata(before), 'metadata_readback_mismatch')
                audit = _public_verify(saved.get('link', ''), new)
                result.update(status='updated', wp_write_count=1, public_audit=audit)
                _save_exclusive(receipt, result)
                return result
            except Exception:
                return {'status': 'update_unconfirmed', 'post_id': post_id,
                        'action_sha256': key, 'reason': 'inspect_wordpress_before_any_retry'}
    except ValueError as exc:
        # Only our static validation codes may be exposed.
        code = str(exc)
        return {'status': 'rejected', 'reason': code if re.fullmatch(r'[a-z_]+', code) else 'invalid_input', 'wp_write_count': 0}
    except Exception:
        return {'status': 'rejected', 'reason': 'preflight_failed', 'wp_write_count': 0}
