#!/usr/bin/env python3
"""Bounded read-only publication recovery and operations alerts; never publish."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.request import Request, build_opener
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.publication_notification import _save, _verified, notify_publication
from scripts.run_daily_pipeline import PipelineError, PipelineLock
from scripts.run_evidence_deep_article import read_reconciliation, resume_public_audit
from scripts.send_kakao_report import send
from scripts.weekly_editorial_updates import _NoRedirect

KST = ZoneInfo('Asia/Seoul')
DEEP = 'huntlab-evidence-deep-article.service'
WEEKLY = 'huntlab-weekly-editorial.service'
REPORT = 'huntlab-kakao-report.service'


def read(path):
    if path.is_symlink() or path.stat().st_size > 2_000_000:
        raise ValueError('invalid_record')
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError('invalid_record')
    return value


def service_active(unit):
    result = subprocess.run(['systemctl', 'show', unit, '-p', 'ActiveState', '--value'],
                            capture_output=True, text=True, timeout=10, check=True)
    return result.stdout.strip() in {'active', 'activating'}


def site_healthy():
    with build_opener(_NoRedirect()).open(Request('https://huntlab.app/',
            headers={'User-Agent': 'HuntLab-Operations/1.0'}), timeout=15) as response:
        return response.status == 200


def publication_identity(record, run_id, day):
    publication = record.get('publication') or {}
    url = urlsplit(publication.get('url', ''))
    return (record.get('run_id') == run_id and record.get('kst_date') == day
            and record.get('wordpress_write_count') == 1
            and type(publication.get('post_id')) is int and publication['post_id'] > 0
            and url.scheme == 'https' and url.netloc == 'huntlab.app'
            and url.path not in ('', '/') and not url.query and not url.fragment)


def run_watchdog(root, now, *, apply=False, recover=resume_public_audit,
                 notify=notify_publication, sender=send, health=site_healthy, active=service_active):
    """Caller owns both watchdog and deep-publication locks for an apply run."""
    if now.tzinfo is None:
        raise ValueError('timezone_required')
    root, now = Path(root), now.astimezone(KST)
    day = now.date().isoformat()
    directory = root/'output/operations-watchdog'
    state_path = directory/'state.json'
    state = read(state_path) if state_path.exists() else {'attempts': {}, 'alerts': {}}
    result = {'checked_at': now.isoformat(), 'dry_run': not apply,
              'wordpress_write_count': 0, 'issues': [], 'recovered': []}
    if apply:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def issue(key, reason):
        result['issues'].append({'key': key, 'reason': reason})

    def attempt(key):
        count = state['attempts'].get(key, 0)
        if not apply or count >= 3:
            return False
        # Persist before even read-only recovery: crashes consume the budget.
        state['attempts'][key] = count + 1
        _save(state_path, state)
        return True

    try:
        if not health():
            issue('site', 'public_site_unreachable')
    except Exception:
        issue('site', 'public_site_unreachable')
    busy = active(DEEP)
    today_runs = []
    for run in sorted((root/'output/evidence-deep-article-runs').glob('*')):
        if not run.is_dir() or run.is_symlink() or not re.fullmatch(r'\d{8}T\d{6}Z-[a-zA-Z0-9_-]+', run.name):
            continue
        stamp = datetime.strptime(run.name.split('-')[0], '%Y%m%dT%H%M%SZ').replace(tzinfo=UTC).astimezone(KST)
        # ponytail: seven-day scan; add indexed incident storage if retention grows.
        if not timedelta(0) <= now - stamp <= timedelta(days=7):
            continue
        if busy:
            continue
        try:
            if not (run/'result.json').exists():
                if now - stamp > timedelta(hours=2):
                    issue(run.name, 'run_incomplete')
                continue
            record = read(run/'result.json')
            if stamp.date() == now.date() and record.get('deep_article') != 'ready_not_published':
                today_runs.append(run.name)
            receipt_path = run/'publication.json'
            recovery_path = run/'public-audit-recovery.json'
            receipt = read(receipt_path) if receipt_path.exists() else None
            if recovery_path.exists():
                restored = read(recovery_path)
                if (not receipt or not publication_identity(receipt, run.name, stamp.date().isoformat())
                        or restored.get('publication') != receipt.get('publication')
                        or not publication_identity(restored, run.name, stamp.date().isoformat())
                        or not _verified(restored)):
                    raise ValueError('invalid_recovery')
                record = restored
            if record.get('failed') and receipt:
                if not publication_identity(receipt, run.name, stamp.date().isoformat()):
                    raise ValueError('invalid_publication')
                if attempt('audit:'+run.name):
                    try:
                        restored = recover(run.name)
                        if (not publication_identity(restored, run.name, stamp.date().isoformat())
                                or restored.get('publication') != receipt.get('publication')
                                or not _verified(restored)):
                            raise ValueError('invalid_recovery')
                        record = restored
                        result['recovered'].append(run.name)
                    except Exception:
                        issue(run.name, 'public_audit_needs_repair')
                        continue
                else:
                    issue(run.name, 'public_audit_needs_repair')
                    continue
            if record.get('failed'):
                reconciliation = read_reconciliation(run)
                if reconciliation and reconciliation.get('wordpress_write_count') == 0:
                    continue
                issue(run.name, 'publication_unknown' if record.get('wordpress_write_count') == 'unknown'
                      else 'pipeline_needs_repair')
                continue
            if record.get('deep_article') != 'published':
                continue  # No topic / limit / quality HOLD is never retried as a failure.
            if not publication_identity(record, run.name, stamp.date().isoformat()) or not _verified(record):
                raise ValueError('invalid_publication')
            post_id = record['publication']['post_id']
            notification_path = root/f'output/kakao-publications/post-{post_id}.json'
            notification = read(notification_path) if notification_path.exists() else {}
            if notification.get('status') == 'sent':
                continue
            if notification and notification.get('status') != 'not_sent':
                issue(str(post_id), 'notification_unknown')
                continue
            if attempt('notify:'+str(post_id)):
                notification = notify(record)
                if notification.get('status') not in {'sent', 'already_sent'}:
                    issue(str(post_id), 'notification_not_sent' if notification.get('status') == 'not_sent'
                          else 'notification_unknown')
            else:
                issue(str(post_id), 'notification_not_sent')
        except Exception:
            issue(run.name, 'record_invalid')

    if now.hour >= 12 and not today_runs and not busy:
        issue(day, 'deep_run_missing')
    sunday = now.date() - timedelta(days=(now.weekday()+1) % 7)
    due = datetime.combine(sunday, datetime.min.time(), KST).replace(hour=21)
    if sunday.isoformat() >= '2026-09-20' and now >= due and not active(WEEKLY):
        weekly = root/f'output/weekly-editorial/{sunday.isoformat()}/result.json'
        try:
            if not weekly.exists():
                issue(sunday.isoformat(), 'weekly_run_missing')
            else:
                report = read(weekly)
                if report.get('failed'):
                    issue(sunday.isoformat(), 'weekly_needs_repair')
                if report.get('metrics_status') == 'INCOMPLETE':
                    issue(sunday.isoformat(), 'analytics_incomplete')
        except Exception:
            issue(sunday.isoformat(), 'record_invalid')
    for hour in (7, 11):
        if now < now.replace(hour=hour, minute=15, second=0, microsecond=0) or active(REPORT):
            continue
        path = root/f'output/kakao-reports/{day}-{hour:02d}.json'
        try:
            if not path.exists():
                issue(f'{day}-{hour}', 'report_missing')
            elif read(path).get('status') != 'sent':
                issue(f'{day}-{hour}', 'report_delivery_unknown')
        except Exception:
            issue(f'{day}-{hour}', 'record_invalid')

    if apply:
        if result['issues'] or result['recovered']:
            fingerprint = hashlib.sha256(json.dumps([result['issues'], result['recovered']], sort_keys=True).encode()).hexdigest()
            alerts = state['alerts'].setdefault(day, {})
            if fingerprint not in alerts and len(alerts) < 2:
                alerts[fingerprint] = 'attempting'
                _save(state_path, state)
                reasons = ', '.join(sorted({x['reason'] for x in result['issues']}))
                message = f"[훈트랩 운영 감시] 복구 {len(result['recovered'])}건 / 확인 필요 {len(result['issues'])}건\n{reasons}\n자동 재발행 없음. 상세: output/operations-watchdog/latest.json"[:200]
                try:
                    sender(message, os.environ.get('MCPORTER_BIN', 'mcporter'))
                    alerts[fingerprint] = 'sent'
                except Exception:
                    alerts[fingerprint] = 'delivery_unconfirmed'
                _save(state_path, state)
                result['alert'] = alerts[fingerprint]
            else:
                result['alert'] = alerts.get(fingerprint, 'daily_alert_limit')
        _save(directory/'latest.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    locks = [PipelineLock(ROOT/'logs/operations-watchdog.lock'),
             PipelineLock(ROOT/'logs/evidence-deep-article.lock')]
    try:
        for lock in locks:
            lock.acquire()
        result = run_watchdog(ROOT, datetime.now(KST), apply=args.apply)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except PipelineError:
        print(json.dumps({'status': 'deferred', 'reason': 'pipeline_busy'}))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__}))
        return 1
    finally:
        for lock in reversed(locks):
            lock.release()


if __name__ == '__main__':
    raise SystemExit(main())
