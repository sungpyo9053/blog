#!/usr/bin/env python3
"""Send today's observed briefing (07h) and deep article (11h) status to self."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo('Asia/Seoul')


class KakaoNotSent(RuntimeError):
    """The MCP call was not started; safe to retry with a bounded budget."""


def quiet_mode(root):
    try:
        config = json.loads((Path(root)/'config/operations-notifications.json').read_text())
        return config == {'schema_version': 1, 'routine_reports': 'weekly'}
    except (OSError, ValueError):
        return False  # Invalid config must never silently disable alerts.


def routine_status(briefing, deep):
    if briefing[0] not in {'발행 완료', '진행 중'}:
        return False
    if deep is None:
        return True
    return bool(re.fullmatch(r'발행 \d+건\((?:발행 기록|공개 확인 완료)\)', deep[0])) or deep[0] in {
        '진행 중', '미발행: READY 0건(정상 종료)', '미발행: 새 주제 조사 후 READY 0건', '미발행: 일일 한도 도달'}


def run_day(run_id):
    try:
        return datetime.strptime(run_id.split('-')[0], '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc).astimezone(KST).date().isoformat()
    except ValueError:
        return ''


def active(unit):
    p = subprocess.run(['systemctl', 'show', unit, '-p', 'ActiveState', '--value'], capture_output=True, text=True, timeout=10)
    return p.stdout.strip() in {'active', 'activating'}


def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent':'HuntNews-Report/1.0'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def briefing_status(day):
    try:
        rows = fetch_json(f'https://huntlab.app/wp-json/wp/v2/hunt_briefing?slug={day}&_fields=id,status,link')
        if not isinstance(rows, list):
            return '조회 오류', ''
        for row in rows:
            if row.get('status') == 'publish':
                return '발행 완료', str(row.get('link', ''))
        return ('진행 중' if active('huntlab-daily-pipeline.service') else '미발행'), ''
    except Exception:
        return '조회 실패(발행 여부 미확인)', ''


def deep_status(root, day, is_active=False):
    rows = []
    for directory in sorted((root/'output/evidence-deep-article-runs').glob('*')):
        if not directory.is_dir() or run_day(directory.name) != day:
            continue
        path = directory/'result.json'
        if not path.exists():
            continue
        try:
            row = json.loads(path.read_text())
            recovery_path = directory/'public-audit-recovery.json'
            if recovery_path.is_file():
                recovery = json.loads(recovery_path.read_text())
                receipt = json.loads((directory/'publication.json').read_text())
                audit = recovery.get('public_audit') or {}
                publication = receipt.get('publication') or {}
                if (recovery.get('run_id') == receipt.get('run_id') == directory.name
                        and recovery.get('kst_date') == receipt.get('kst_date') == day
                        and recovery.get('publication') == publication
                        and receipt.get('wordpress_write_count') == 1
                        and recovery.get('wordpress_write_count') == 1
                        and recovery.get('failed') is False
                        and recovery.get('deep_article') == 'published'
                        and audit.get('url') == publication.get('url')
                        and audit.get('http_status') == 200
                        and audit.get('title_present') is True
                        and audit.get('evidence_links_present') is True):
                    row = recovery
            # dry-run does not prove the scheduled execution happened.
            if row.get('deep_article') != 'ready_not_published':
                rows.append(row)
        except (ValueError, OSError):
            return '결과 기록 오류', ''
    published = {}
    for path in (root/'output/runs').glob('*/*/publisher-audit.jsonl'):
        try:
            context = json.loads((path.parent/'planner-context.json').read_text())
            if context.get('content_type') not in {'evidence_deep_article', 'foundation_concept'}:
                continue
            for line in path.read_text().splitlines():
                event = json.loads(line)
                if event.get('event') != 'post_published' or event.get('status') != 'Success':
                    continue
                when = datetime.fromisoformat(event['timestamp']).astimezone(KST).date().isoformat()
                if when == day:
                    published[event['post_id']] = event.get('published_url', '')
        except (ValueError, OSError, KeyError):
            continue
    if published:
        suffix = ' / 후속 처리 실패' if rows and rows[-1].get('failed') else ''
        return f'발행 {len(published)}건(발행 기록){suffix}', next(iter(published.values()))
    if is_active:
        return '진행 중', ''
    if not rows:
        return '실행 결과 없음(누락/중단 확인 필요)', ''
    latest = rows[-1]
    if latest.get('failed'):
        if latest.get('wordpress_write_count') == 'unknown':
            return '실패: 글 저장 결과 미확인(중복 방지를 위해 재발행 중지)', ''
        if latest.get('failure_stage') == 'candidate_supply':
            return '실패: 새 주제 조사·후보 공급 단계', ''
        if latest.get('wordpress_write_count') == 1:
            return '실패: 글 저장 후 공개 내용 확인 단계', ''
        return '실패: 글 작성·검수 단계(원인 확인 필요)', ''
    state = latest.get('deep_article')
    if state == 'published':
        audit = latest.get('public_audit') or {}
        publication = latest.get('publication') or {}
        url = publication.get('url', '')
        if (latest.get('wordpress_write_count') == 1 and audit.get('http_status') == 200
                and audit.get('url') == url and audit.get('title_present') is True
                and audit.get('evidence_links_present') is True
                and url.startswith('https://huntlab.app/')):
            return '발행 1건(공개 확인 완료)', url
    if state == 'no_publishable_topic':
        if latest.get('reconciliation_required'):
            return '미발행: READY 0건 / 과거 발행 결과 대조 필요', ''
        if (latest.get('discovery') or {}).get('status') == 'no_candidate':
            return '미발행: 새 주제 조사 후 READY 0건', ''
        return '미발행: READY 0건(정상 종료)', ''
    if state == 'daily_limit_reached':
        return '미발행: 일일 한도 도달', ''
    return '발행 결과 확인 필요', ''


def message_for(day, slot, briefing, deep=None):
    status, url = briefing
    lines = [f'[Hunt News {day} {slot}시]', f'브리핑: {status}']
    if slot == '11' and deep:
        lines.append('심층글: '+deep[0])
    # Keep status intact; omit links rather than truncate URLs at the 200-char limit.
    for link in (url, deep[1] if deep else ''):
        if link and link.startswith('https://huntlab.app/') and len('\n'.join(lines+[link])) <= 200:
            lines.append(link)
    return '\n'.join(lines)


def send(message, executable):
    env = os.environ.copy()
    if Path(executable).is_absolute():
        env['PATH'] = str(Path(executable).parent) + os.pathsep + env.get('PATH', '')
    try:
        runtime = subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=15, env=env)
    except (OSError, subprocess.TimeoutExpired):
        raise KakaoNotSent('Kakao runtime unavailable before send') from None
    if runtime.returncode:
        raise KakaoNotSent('Kakao runtime failed before send')
    p = subprocess.run([executable, 'call', 'mcp-gateway.KakaotalkChat-MemoChat', '--args', json.dumps({'message':message},ensure_ascii=False), '--timeout','45000','--output','json'], capture_output=True, text=True, timeout=60, env=env)
    # Do not emit raw client output: OAuth diagnostics can contain credentials.
    if p.returncode or '메시지를 성공적으로 보냈습니다' not in p.stdout:
        raise RuntimeError('Kakao delivery unconfirmed; inspect authentication privately')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slot', choices=['07','11'])
    parser.add_argument('--send', action='store_true')
    args=parser.parse_args()
    now=datetime.now(KST)
    slot=args.slot or ('07' if now.hour < 11 else '11')
    day=now.date().isoformat()
    state=ROOT/'output/kakao-reports'
    state.mkdir(parents=True,exist_ok=True)
    with (state/'report.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        receipt=state/f'{day}-{slot}.json'
        if args.send and receipt.exists():
            print('already_attempted; no duplicate send')
            return 0
        briefing=briefing_status(day)
        deep=deep_status(ROOT,day,active('huntlab-evidence-deep-article.service')) if slot=='11' else None
        message=message_for(day,slot,briefing,deep)
        if len(message)>200:
            raise RuntimeError('Report exceeds Kakao 200 character limit')
        if not args.send:
            print(message)
            return 0
        payload={'day':day,'slot':slot,'message':message,'status':'attempting','timestamp':now.isoformat()}
        if quiet_mode(ROOT):
            payload['status'] = 'suppressed_healthy' if routine_status(briefing, deep) else 'queued_issue'
            receipt.write_text(json.dumps(payload, ensure_ascii=False)+'\n')
            print(payload['status']+'; retained for weekly reporting and watchdog')
            return 0
        receipt.write_text(json.dumps(payload,ensure_ascii=False)+'\n')
        try:
            send(message,os.environ.get('MCPORTER_BIN','mcporter'))
        except Exception as exc:
            payload['status']='not_sent' if isinstance(exc, KakaoNotSent) else 'delivery_unconfirmed'
            receipt.write_text(json.dumps(payload,ensure_ascii=False)+'\n')
            print(payload['status']+'; no automatic duplicate send')
            return 1
        payload['status']='sent'
        receipt.write_text(json.dumps(payload,ensure_ascii=False)+'\n')
        print('sent '+day+' '+slot)
        return 0


if __name__=='__main__':
    raise SystemExit(main())
