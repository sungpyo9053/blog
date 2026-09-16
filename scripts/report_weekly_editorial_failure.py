#!/usr/bin/env python3
"""Systemd failure alert only; never retries editorial work or WordPress writes."""
import fcntl
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.publication_notification import _save
from scripts.send_kakao_report import send


def main():
    result = subprocess.run(['systemctl', 'show', 'huntlab-weekly-editorial.service',
                             '--property=InvocationID', '--value'], capture_output=True,
                            text=True, timeout=10, check=True).stdout.strip()
    if len(result) != 32 or any(c not in '0123456789abcdef' for c in result):
        raise ValueError('Missing service invocation identity')
    directory = ROOT / 'output/weekly-editorial/failure-alerts'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f'{result}.json'
    with (directory / 'alert.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            print('already_attempted; no duplicate alert')
            return 0
        payload = {'status':'attempting', 'invocation_id':result,
                   'checked_at':datetime.now(UTC).isoformat()}
        _save(path, payload)
        message = '[훈트랩 주간 개선 경고]\n서비스가 정상 종료되지 않았습니다. 자동 재실행은 하지 않습니다. 수정 완료 여부는 실행 기록·WordPress 확인이 필요합니다. 상세: output/weekly-editorial/'
        try:
            send(message, os.environ.get('MCPORTER_BIN', 'mcporter'))
        except Exception:
            payload['status'] = 'delivery_unconfirmed'
        else:
            payload['status'] = 'sent'
        _save(path, payload)
        print(json.dumps({'status':payload['status']}))
        return 0 if payload['status'] == 'sent' else 1


if __name__ == '__main__':
    raise SystemExit(main())
