#!/usr/bin/env python3
"""Safely switch the HuntLab humanization pass ON or OFF."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_daily_pipeline import HUMANIZE_EXPERIMENT_STATE


def update_state(path: Path, mode: str, *, until: date | None = None) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    enabled = mode == "on"
    payload.update({"enabled": enabled, "mode": mode, "remaining": 0})
    if enabled:
        if until is None:
            raise ValueError("ON 모드에는 --until 날짜가 필요합니다.")
        payload["enabled_until"] = f"{until.isoformat()}T23:59:59+09:00"
        payload["note"] = (
            f"Scheduled pipeline humanization is ON through {until.isoformat()} "
            "23:59:59 KST and becomes ineffective after that cutoff."
        )
    else:
        payload.pop("enabled_until", None)
        payload["note"] = "Scheduled pipeline humanization is OFF."

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("on", "off"))
    parser.add_argument("--until", type=date.fromisoformat)
    args = parser.parse_args()
    if args.mode == "on" and args.until is None:
        parser.error("on에는 --until YYYY-MM-DD가 필요합니다.")
    payload = update_state(HUMANIZE_EXPERIMENT_STATE, args.mode, until=args.until)
    print(
        json.dumps(
            {
                "enabled": payload["enabled"],
                "mode": payload["mode"],
                "enabled_until": payload.get("enabled_until"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
