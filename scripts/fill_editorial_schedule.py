#!/usr/bin/env python3
"""Bounded refill: at most seven preparations, stop on failure or no new candidate."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import editorial_queue as queue


def main():
    for _ in range(7):
        scheduled = subprocess.run([sys.executable, str(ROOT/'scripts/schedule_editorial_queue.py')], cwd=ROOT)
        if scheduled.returncode:
            return scheduled.returncode
        if not queue.preparation_allowed(ROOT):
            print('schedule_target_reached')
            return 0
        before = len(queue.rows(ROOT))
        prepared = subprocess.run([sys.executable, str(ROOT/'scripts/run_evidence_deep_article.py'), '--apply', '--prepare-only'], cwd=ROOT)
        if prepared.returncode:
            return prepared.returncode
        if len(queue.rows(ROOT)) <= before:
            print('no_new_approved_article')
            return 0
    return subprocess.run([sys.executable, str(ROOT/'scripts/schedule_editorial_queue.py')], cwd=ROOT).returncode


if __name__ == '__main__':
    raise SystemExit(main())
