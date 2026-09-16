#!/usr/bin/env python3
"""Notify the approved Kakao self-chat after verified publication, never publish.

Uncertain delivery cannot be retried automatically: MCP has no idempotency key.
The CLI retries only this notification and never invokes the publishing pipeline.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

try:
    from scripts.send_kakao_report import send
except ModuleNotFoundError:  # Direct script execution.
    from send_kakao_report import send

ROOT = Path(__file__).resolve().parents[1]


def _verified(result):
    publication = result.get('publication') or {}
    audit = result.get('public_audit') or {}
    post_id = publication.get('post_id')
    url = publication.get('url', '')
    parsed = urlsplit(url)
    if not (
        result.get('failed') is False
        and result.get('deep_article') == 'published'
        and result.get('wordpress_write_count') == 1
        and type(post_id) is int and post_id > 0
        and parsed.scheme == 'https' and parsed.netloc == 'huntlab.app'
        and parsed.path not in ('', '/') and not parsed.query and not parsed.fragment
        and not any(character.isspace() for character in url)
        and audit.get('url') == url and audit.get('http_status') == 200
        and audit.get('title_present') is True
        and audit.get('evidence_links_present') is True
    ):
        return None
    return publication


def _save(path, payload):
    """Persist state before crossing the external side-effect boundary."""
    descriptor, temporary = tempfile.mkstemp(prefix='.receipt-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(payload, stream, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _notify(result, root, sender, retry_unconfirmed):
    publication = _verified(result)
    if publication is None:
        return {'status': 'not_eligible'}
    post_id = publication['post_id']
    url = publication['url']
    # Preserve a complete article link, including when an encoded slug is long.
    link = url if len(url) <= 150 else f'https://huntlab.app/?p={post_id}'
    title = ' '.join(str(publication.get('title', '')).split())
    lines = ['[HuntLab 새 글 발행]', '공개 본문·근거 확인 완료']
    available = 200 - len('\n'.join(lines + [link])) - 1
    if title and available > 0:
        lines.append(title[:available])
    message = '\n'.join(lines + [link])
    state = root / 'output/kakao-publications'
    state.mkdir(parents=True, exist_ok=True)
    path = state / f'post-{post_id}.json'
    with (state / 'notification.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = json.loads(path.read_text()) if path.exists() else {}
        if previous.get('status') == 'sent':
            return {'status': 'already_sent', 'post_id': post_id}
        if previous and previous.get('status') != 'not_sent' and not retry_unconfirmed:
            return {'status': 'delivery_unconfirmed', 'post_id': post_id}
        receipt = {
            'post_id': post_id, 'url': url, 'run_id': result.get('run_id'),
            'message': message, 'status': 'attempting',
            'attempt': previous.get('attempt', 0) + 1,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        _save(path, receipt)
        try:
            sender(message, os.environ.get('MCPORTER_BIN', 'mcporter'))
        except FileNotFoundError:
            # The process was never started, so notification-only retry is safe.
            receipt['status'] = 'not_sent'
        except Exception:
            # Never persist exception strings or raw MCP/OAuth output.
            receipt['status'] = 'delivery_unconfirmed'
        else:
            receipt['status'] = 'sent'
        _save(path, receipt)
        return {'status': receipt['status'], 'post_id': post_id}


def notify_publication(result, *, root=ROOT, sender=None, retry_unconfirmed=False):
    """Best-effort notification. Failures cannot turn a published post into failure."""
    try:
        return _notify(result, Path(root), sender or send, retry_unconfirmed)
    except Exception:
        return {'status': 'notification_error'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result', required=True, type=Path,
                        help='Verified result.json or public-audit-recovery.json')
    parser.add_argument('--send', action='store_true')
    parser.add_argument('--retry-unconfirmed', action='store_true',
                        help='Only after checking self-chat: delivery may duplicate')
    args = parser.parse_args()
    if args.retry_unconfirmed and not args.send:
        parser.error('--retry-unconfirmed requires --send')
    try:
        result = json.loads(args.result.read_text())
        status = (notify_publication(result, retry_unconfirmed=args.retry_unconfirmed)
                  if args.send else {'status': 'eligible' if _verified(result) else 'not_eligible'})
    except Exception:
        status = {'status': 'notification_error'}
    print(json.dumps(status))
    return 0 if status['status'] in {'sent', 'already_sent', 'eligible'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
