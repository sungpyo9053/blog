#!/usr/bin/env python3
"""Retry at 17:00 KST only when today's 04:00 briefing run did not succeed."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
RUNS_DIR = ROOT / "output" / "runs"
LOCK_FILE = LOG_DIR / "daily-pipeline.lock"
RUN_ID_PATTERN = re.compile(
    r"(?m)^[^\n ]+ INFO pipeline event=(?:start|resume) run_id="
    r"([0-9]{8}T[0-9]{6}Z-[a-f0-9]{10})"
)
SUCCESS_PATTERN = re.compile(
    r"(?m)^[^\n ]+ INFO pipeline event=end failed=false run_id="
)


def active_pipeline_pid() -> int | None:
    if not LOCK_FILE.is_file():
        return None
    try:
        pid = int(json.loads(LOCK_FILE.read_text(encoding="utf-8")).get("pid", 0))
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def choose_command(log_text: str) -> list[str] | None:
    if SUCCESS_PATTERN.search(log_text):
        return None
    # A manufactured Build Log is a planner classification error, not a
    # resumable stage failure. Re-plan at the 17:00 check after the strengthened gate.
    if "Build Log는 existing_work_record 근거만 허용합니다" in log_text:
        return [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / "scripts/run_daily_pipeline.py"),
            "--briefing-only",
        ]
    run_ids = RUN_ID_PATTERN.findall(log_text)
    python = str(ROOT / ".venv/bin/python")
    runner = str(ROOT / "scripts/run_daily_pipeline.py")
    if run_ids:
        run_id = run_ids[-1]
        if (RUNS_DIR / run_id / "topics.md").is_file():
            return [python, runner, "--briefing-only", "--resume-run-id", run_id]
    return [python, runner, "--briefing-only"]


def main() -> int:
    pid = active_pipeline_pid()
    if pid is not None:
        print(f"noon_retry status=skipped_pipeline_running pid={pid}")
        return 0
    log_path = LOG_DIR / f"{date.today().isoformat()}.log"
    log_text = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
    command = choose_command(log_text)
    if command is None:
        print("noon_retry status=skipped_daily_success")
        return 0
    mode = "resume" if "--resume-run-id" in command else "fresh"
    print(f"noon_retry status=starting mode={mode}")
    result = subprocess.run(command, cwd=ROOT, check=False)
    print(f"noon_retry status=finished mode={mode} exit_code={result.returncode}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
