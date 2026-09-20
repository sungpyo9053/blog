#!/usr/bin/env python3
"""Schedule approved immutable queue entries in WordPress; never publish immediately."""
from __future__ import annotations

import json
import hashlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import editorial_queue as queue
from scripts import run_evidence_deep_article as deep
from scripts.run_daily_pipeline import configure_logger, publish_prepared_topic
from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient


def next_slot(posts, now):
    occupied = set()
    for post in posts:
        if post.get('status') not in {'publish', 'future'}:
            continue
        value = post.get('date_gmt')
        if not value:
            raise ValueError('schedule_inventory_date_missing')
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.tzinfo is None:
            from datetime import timezone
            date = date.replace(tzinfo=timezone.utc)
        occupied.add(date.astimezone(queue.KST).date())
    for offset in range(1, 8):
        slot = (now + timedelta(days=offset)).replace(hour=10, minute=0, second=0, microsecond=0)
        if slot.date() not in occupied and slot - now <= timedelta(days=7):
            return slot
    return None


def schedule_one():
    """Caller owns the same lane lock as preparation and legacy release."""
    now = queue.clock()
    client = WordPressClient(WordPressConfig.from_environment(ROOT / '.env'), max_retries=0)
    items = queue.rows(ROOT)
    if any(row['status'] == 'publishing' for row in items):
        raise ValueError('queue_publication_reconciliation_required')
    # Scheduled entries stay reserved; do not count already public entries as backlog.
    for row in items:
        if row['status'] == 'scheduled':
            post = client.get_post(row['publication']['post_id'])
            receipt = row['publication']
            raw = post.get('content', {}).get('raw')
            if (not isinstance(raw, str) or hashlib.sha256(raw.encode()).hexdigest() != receipt.get('expected_html_sha256')
                    or post.get('date_gmt') != receipt.get('date_gmt')):
                raise ValueError('scheduled_post_changed')
            if post.get('status') == 'publish':
                audit = queue.audit_queued_public(receipt, row['candidate'])
                run_id = deep.make_run_id()
                observed = deep.OUTPUT / run_id
                observed.mkdir(parents=True, exist_ok=False)
                actual_day = datetime.fromisoformat(post['date']).date().isoformat()
                result = {'run_id': run_id, 'kst_date': actual_day, 'failed': False,
                          'deep_article': 'published', 'wordpress_write_count': 1,
                          'publication': receipt, 'public_audit': audit,
                          'candidate': row['candidate'], 'queue_id': row['queue_id']}
                deep.write_json_new(observed / 'result.json', result)
                row.update(status='published', observed_published_at=now.isoformat())
                queue.save(queue.directory(ROOT) / f"{row['queue_id']}.json", row)
                deep.notify_publication(result)
            elif post.get('status') != 'future':
                raise ValueError('scheduled_post_state_changed')
    candidates = [row for row in items if row['status'] == 'queued']
    if not candidates:
        return {'status': 'no_approved_article', 'wordpress_write_count': 0}
    inventory = deep.refresh_inventory()
    snapshot = json.loads(inventory.read_text())
    if 'future' not in snapshot['metadata']['statuses']:
        raise ValueError('schedule_inventory_missing_future')
    slot = next_slot(snapshot['posts'], now)
    if slot is None:
        return {'status': 'schedule_week_full', 'wordpress_write_count': 0}
    row = sorted(candidates, key=lambda row: row['prepared_at'])[0]
    context = queue.preflight(row, repo=ROOT, inventory_path=inventory, now=now)
    review_dir = ROOT / 'output/schedule-reviews' / deep.make_run_id()
    review_dir.mkdir(parents=True, exist_ok=False)
    logger = configure_logger(now.date())
    queue.review_fresh_context(context, row['candidate'], inventory, review_dir, ROOT, logger)
    queue.preflight(row, repo=ROOT, inventory_path=inventory, now=queue.clock())
    # Reserve the item durably before the first possible WordPress mutation.
    row.update(status='publishing', scheduled_at=slot.isoformat())
    queue.save(queue.directory(ROOT) / f"{row['queue_id']}.json", row)
    result = publish_prepared_topic(context, configure_logger(now.date()),
                                    inventory_path=inventory, scheduled_at=slot)
    row['publication'] = result
    queue.save(queue.directory(ROOT) / f"{row['queue_id']}.json", row)
    if result.get('status') != 'scheduled' or result.get('content_verified') is not True:
        raise ValueError('scheduled_post_requires_reconciliation')
    from datetime import timezone
    if (result.get('date_gmt') != slot.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
            or result.get('date') != slot.strftime('%Y-%m-%dT%H:%M:%S')):
        raise ValueError('scheduled_post_date_mismatch')
    row.update(status='scheduled')
    queue.save(queue.directory(ROOT) / f"{row['queue_id']}.json", row)
    return {'status': 'scheduled', 'wordpress_write_count': 1,
            'post_id': result['post_id'], 'scheduled_at': slot.isoformat(), 'queue_id': row['queue_id']}


def main():
    lock = deep.PipelineLock(deep.LOCK)
    try:
        lock.acquire()
        result = schedule_one()
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__,
                          'reason': str(exc) if str(exc).replace('_', '').isalnum() else 'check_private_audit'}))
        return 1
    finally:
        lock.release()


if __name__ == '__main__':
    raise SystemExit(main())
