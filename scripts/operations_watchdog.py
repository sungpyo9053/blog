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
from scripts.run_evidence_deep_article import audit_public, read_reconciliation, resume_public_audit
from scripts.send_kakao_report import send, briefing_status, deep_status, routine_status, quiet_mode
from scripts.weekly_editorial_updates import _NoRedirect

KST = ZoneInfo('Asia/Seoul')
DEEP = 'huntlab-evidence-deep-article.service'
WEEKLY = 'huntlab-weekly-editorial.service'
REPORT = 'huntlab-kakao-report.service'


def editorial_collection_status(root, now):
    """Observe the daily collector deadline, not a six-hour always-on schedule."""
    now = now.astimezone(KST)
    # Collection starts at 04:00; allow it 30 minutes. Between daily runs the
    # cache may legitimately exceed six hours without being a stuck collector.
    due = now.replace(hour=4, minute=30, second=0, microsecond=0)
    expected = (now if now >= due else now - timedelta(days=1)).replace(
        hour=3, minute=30, second=0, microsecond=0)
    path = Path(root)/'output/search-signals/editorial-sources.json'
    try:
        payload = read(path)
        stamp = datetime.fromisoformat(payload['checked_at'])
        if (stamp.tzinfo is None or stamp > now + timedelta(minutes=5)
                or payload.get('provider') != 'hunt_news_editorial_sources'
                or payload.get('contract_version') != 'editorial-source-cache.v1'
                or not isinstance(payload.get('rows'), list) or not payload['rows']):
            raise ValueError('invalid_collection')
        return {'status': 'stale' if stamp < expected else 'fresh',
                'checked_at': stamp.isoformat(), 'row_count': len(payload['rows'])}
    except FileNotFoundError:
        return {'status': 'missing'}
    except (OSError, ValueError, KeyError, TypeError):
        return {'status': 'invalid'}


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


def confirm_publication(run, record):
    receipt = read(run/'publication.json')
    if receipt.get('publication') != record.get('publication'):
        return False
    return bool(_verified({**record, 'public_audit': audit_public(
        record['publication'], receipt['candidate'])}))


def confirm_scheduled_report(root, day, slot):
    briefing = briefing_status(day)
    deep = deep_status(root, day, service_active(DEEP)) if slot == '11' else None
    return routine_status(briefing, deep)


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
    collection = editorial_collection_status(root, now)
    result['checks'] = {'editorial_collection': collection}
    if collection['status'] != 'fresh':
        issue('editorial_collection', 'news_collection_' + collection['status'])
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
            if now - stamp > timedelta(days=1):
                continue  # Never announce old posts as newly published during installation.
            post_id = record['publication']['post_id']
            notification_path = root/f'output/kakao-publications/post-{post_id}.json'
            notification = read(notification_path) if notification_path.exists() else {}
            if notification.get('status') in {'sent', 'suppressed_healthy'}:
                continue
            if notification and notification.get('status') != 'not_sent':
                issue(str(post_id), 'notification_unknown')
                continue
            if attempt('notify:'+str(post_id)):
                if not confirm_publication(run, record):
                    issue(run.name, 'public_audit_needs_repair')
                    continue
                notification = notify(record)
                if notification.get('status') not in {'sent', 'already_sent', 'suppressed_healthy'}:
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
            elif read(path).get('status') == 'queued_issue':
                key = hashlib.sha256(path.read_bytes()).hexdigest()
                resolved = state.setdefault('resolved_reports', {})
                if key not in resolved:
                    if confirm_scheduled_report(root, day, f'{hour:02d}'):
                        if apply:
                            resolved[key] = now.isoformat()
                        result['recovered'].append(f'report-{day}-{hour:02d}')
                    else:
                        issue(f'{day}-{hour}', 'scheduled_check_failed')
            elif read(path).get('status') not in {'sent', 'suppressed_healthy'}:
                issue(f'{day}-{hour}', 'report_delivery_unknown')
        except Exception:
            issue(f'{day}-{hour}', 'record_invalid')

    if apply:
        previous = state.get('observations', {})
        observations = {}
        actionable = []
        for item in result['issues']:
            key = json.dumps(item, sort_keys=True)
            old = previous.get(key, {})
            observation = {'count': old.get('count', 0)+1, 'opened_at': old.get('opened_at', now.isoformat())}
            observations[key] = observation
            if item['reason'] == 'notification_unknown' and quiet_mode(root):
                continue  # Individual post alerts are retired; preserve ambiguity without a new task.
            if observation['count'] >= 3 or item['reason'] == 'publication_unknown':
                actionable.append({**item, 'opened_at': observation['opened_at']})
        state['observations'] = observations
        result['action_required'] = actionable
        # Resolved transient incidents stay in records, without interrupting the user.
        if actionable:
            fingerprint = hashlib.sha256(json.dumps(actionable, sort_keys=True).encode()).hexdigest()
            alerts = state['alerts'].setdefault(day, {})
            prior = next((items[fingerprint] for items in state['alerts'].values() if fingerprint in items), None)
            if prior is None and len(alerts) < 2:
                alerts[fingerprint] = 'attempting'
                _save(state_path, state)
                labels = {
                    'public_site_unreachable': '사이트 접속 오류', 'publication_unknown': '발행 여부 확인 필요',
                    'public_audit_needs_repair': '공개 글 검증 실패', 'pipeline_needs_repair': '글 작성 오류',
                    'notification_unknown': '글 발행과 별개로 카톡 도착 확인 불가', 'notification_not_sent': '카톡 발송 시작 전 오류',
                    'record_invalid': '실행 기록 오류', 'run_incomplete': '작업 중단',
                    'deep_run_missing': '정기 글 작업 누락', 'weekly_run_missing': '주간 점검 누락',
                    'weekly_needs_repair': '주간 점검 오류', 'analytics_incomplete': '통계 연결 확인 필요',
                    'report_missing': '정기 보고 누락', 'report_delivery_unknown': '정기 보고의 카톡 도착 확인 불가',
                    'scheduled_check_failed': '정기 점검에서 오류 확인',
                    'news_collection_stale': '뉴스 수집 갱신 지연(오래된 자료 발행 차단)',
                    'news_collection_missing': '뉴스 수집 기록 없음(발행 전 확인 필요)',
                    'news_collection_invalid': '뉴스 수집 기록 검증 실패(발행 전 확인 필요)'}
                reasons = ', '.join(sorted({labels[x['reason']] for x in actionable}))[:75]
                message = f"[훈트랩 조치 필요]\n{reasons}\n자동 처리로 해결되지 않았습니다. 기록은 보존했습니다.\n로그를 복사하지 말고 ‘훈트랩 복구해줘’라고 요청하면 됩니다."[:200]
                try:
                    sender(message, os.environ.get('MCPORTER_BIN', 'mcporter'))
                    alerts[fingerprint] = 'sent'
                except Exception:
                    alerts[fingerprint] = 'delivery_unconfirmed'
                _save(state_path, state)
                result['alert'] = alerts[fingerprint]
            else:
                result['alert'] = prior or 'daily_alert_limit'
        _save(state_path, state)
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
