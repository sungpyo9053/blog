#!/usr/bin/env python3
"""Inspect a failed daily run and explicitly resume it after a human fix."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID_PATTERN = re.compile(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{10}")
LOCK_FILE = ROOT / "logs" / "daily-pipeline.lock"


def active_pid() -> int | None:
    if not LOCK_FILE.is_file():
        return None
    try:
        payload = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        pid = int(payload.get("pid", 0))
        import os

        os.kill(pid, 0)
        return pid
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose a failed run; resume only with explicit --execute."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not RUN_ID_PATTERN.fullmatch(args.run_id):
        raise SystemExit("invalid --run-id format")

    run_dir = ROOT / "output" / "runs" / args.run_id
    topics = run_dir / "topics.md"
    if not topics.is_file():
        raise SystemExit(f"missing resumable topics.md: {topics}")
    pid = active_pid()
    if pid is not None:
        raise SystemExit(f"pipeline already running (pid={pid})")

    log_path = ROOT / "logs" / f"{args.run_id[:8]}.log"
    print(f"run_id={args.run_id}")
    print(f"topics={topics}")
    print(f"log={log_path}")
    print("mode=manual-resume")
    if not args.execute:
        print("action=diagnostic-only; fix the cause, then rerun with --execute")
        return 0

    command = [
        str(ROOT / ".venv/bin/python"),
        str(ROOT / "scripts/run_daily_pipeline.py"),
        "--resume-run-id",
        args.run_id,
    ]
    print("action=resume")
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
