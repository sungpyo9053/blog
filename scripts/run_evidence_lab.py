#!/usr/bin/env python3
"""Run the two approved HuntLab Evidence Lab fixtures without external writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evidence/lab-fixtures"


def _run(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, shell=False)
    return {"command": command, "exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_experiment(candidate_id: str) -> dict[str, Any]:
    tool = ROOT / "scripts/huntlab_wp_diagnostics.py"
    if candidate_id == "rest-html-200-response":
        before = _run([sys.executable, str(tool), "rest-response", "--status", "200", "--content-type", "text/html; charset=UTF-8", "--body", str(FIXTURES/"rest-html-200.html")])
        after = _run([sys.executable, str(tool), "rest-response", "--status", "201", "--content-type", "application/json; charset=UTF-8", "--body", str(FIXTURES/"rest-post-201.json"), "--expected-id", "742"])
        files = [FIXTURES/"rest-html-200.html", FIXTURES/"rest-post-201.json", tool]
        expected = {"before_exit": 1, "before_reason": "unexpected_content_type", "after_exit": 0, "after_reason": "validated_json_post_identity"}
    elif candidate_id == "noindex-sitemap-consistency":
        common = [sys.executable, str(tool), "indexability", "--pages", str(FIXTURES/"indexability-pages.json"), "--sitemap"]
        before = _run([*common, str(FIXTURES/"sitemap-before.xml")])
        after = _run([*common, str(FIXTURES/"sitemap-after.xml")])
        files = [FIXTURES/"indexability-pages.json", FIXTURES/"sitemap-before.xml", FIXTURES/"sitemap-after.xml", tool]
        expected = {"before_exit": 1, "before_reason": "indexability_conflict", "after_exit": 0, "after_reason": "consistent"}
    else:
        raise ValueError("candidate is not approved for this Evidence Lab")
    test = _run([sys.executable, "-m", "unittest", "tests.test_huntlab_wp_diagnostics", "-v"])
    before_payload = json.loads(before["stdout"])
    after_payload = json.loads(after["stdout"])
    ready = before["exit_code"] == expected["before_exit"] and before_payload["reason"] == expected["before_reason"] and after["exit_code"] == expected["after_exit"] and after_payload["reason"] == expected["after_reason"] and test["exit_code"] == 0
    return {
        "contract_version": "evidence-lab.v1",
        "candidate_id": candidate_id,
        "environment": {"python": sys.version.split()[0], "platform": sys.platform, "network_writes": 0, "wordpress_writes": 0},
        "expected_before_after": expected,
        "before": before,
        "after": after,
        "regression_test": test,
        "file_sha256": {path.relative_to(ROOT).as_posix(): _sha(path) for path in files},
        "completed_at": datetime.now(UTC).isoformat(),
        "status": "READY" if ready else "REJECT",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_id", choices=("rest-html-200-response", "noindex-sitemap-consistency"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_experiment(args.candidate_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {args.output}")
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_id": args.candidate_id, "status": payload["status"], "wordpress_writes": 0}, ensure_ascii=False))
    return 0 if payload["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
