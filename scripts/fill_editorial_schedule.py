#!/usr/bin/env python3
"""Bounded refill: at most seven preparations.

A content rejection of one candidate (Reviewer ContentQualityRejection, or the
deterministic editorial gate) only drops that candidate and the refill moves on
to the next one; any other failure (model limit, budget, source, WordPress)
still stops immediately.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import editorial_queue as queue

RUNS = ROOT / 'output/evidence-deep-article-runs'


def run_ids():
    return {path.name for path in RUNS.glob('2*') if path.is_dir()} if RUNS.is_dir() else set()


def rejected_by_reviewer(new_runs):
    """True only when exactly one new run recorded a content rejection of its candidate."""
    if len(new_runs) != 1:
        return False
    try:
        result = json.loads((RUNS / next(iter(new_runs)) / 'result.json').read_text())
    except (OSError, ValueError):
        return False
    content_rejection = (result.get('error_type') == 'ContentQualityRejection'
                         or result.get('reason') == 'editorial_gate_rejected')
    return content_rejection and result.get('wordpress_write_count') == 0


def main():
    for _ in range(7):
        scheduled = subprocess.run([sys.executable, str(ROOT/'scripts/schedule_editorial_queue.py')], cwd=ROOT)
        if scheduled.returncode:
            return scheduled.returncode
        if not queue.preparation_allowed(ROOT):
            print('schedule_target_reached')
            return 0
        before = len(queue.rows(ROOT))
        runs_before = run_ids()
        prepared = subprocess.run([sys.executable, str(ROOT/'scripts/run_evidence_deep_article.py'), '--apply', '--prepare-only'], cwd=ROOT)
        if prepared.returncode:
            if rejected_by_reviewer(run_ids() - runs_before):
                print('reviewer_rejected_next_candidate')
                continue
            return prepared.returncode
        if len(queue.rows(ROOT)) <= before:
            print('no_new_approved_article')
            return 0
    return subprocess.run([sys.executable, str(ROOT/'scripts/schedule_editorial_queue.py')], cwd=ROOT).returncode


if __name__ == '__main__':
    raise SystemExit(main())
