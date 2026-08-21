#!/usr/bin/env python3
"""Aggregate the fixed 14-day News Worthiness Shadow observation window."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = PROJECT_ROOT / "output" / "runs"
REPORT_DIR = PROJECT_ROOT / "output" / "news-worthiness" / "reports"
KST = ZoneInfo("Asia/Seoul")
DEFAULT_START = date(2026, 8, 22)
DEFAULT_END = date(2026, 9, 4)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _observed_date(payload: Mapping[str, Any]) -> date | None:
    raw = payload.get("selected_at") or payload.get("recorded_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw)).astimezone(KST).date()
    except ValueError:
        return None


def load_window(
    runs_dir: Path, start: date, end: date
) -> list[tuple[Path, dict[str, Any]]]:
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(runs_dir.glob("*/news-worthiness-shadow*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        observed = _observed_date(payload)
        if observed is not None and start <= observed <= end:
            rows.append((path, payload))
    return rows


def _base_rank(ranking: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    ordered = sorted(
        ranking,
        key=lambda item: (float(item.get("base_score", 0)), str(item.get("candidate_id", ""))),
        reverse=True,
    )
    return {str(item["candidate_id"]): index for index, item in enumerate(ordered, 1)}


def replay_result(run_dir: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    topics_path = run_dir / "topics.md"
    if not topics_path.is_file():
        return {"status": "missing_topics"}
    try:
        from scripts.news_worthiness import build_shadow_diff
        from scripts.run_daily_pipeline import parse_topic_plan_document

        document = parse_topic_plan_document(topics_path)
        legacy_titles = [str(item["title"]) for item in document["top2"]]
        replayed = build_shadow_diff(
            document["candidates"],
            legacy_titles,
            selected_at=str(payload["selected_at"]),
        )
    except Exception as exc:
        return {"status": "error", "error_type": type(exc).__name__}
    return {
        "status": "match" if canonical_bytes(replayed) == canonical_bytes(payload) else "mismatch",
        "source_snapshot_hash_match": replayed.get("source_snapshot_hash")
        == payload.get("source_snapshot_hash"),
    }


def aggregate(
    rows: Iterable[tuple[Path, Mapping[str, Any]]], start: date, end: date
) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    hard_filter_reasons: Counter[str] = Counter()
    evidence_strengths: Counter[str] = Counter()
    overlap_counts: Counter[str] = Counter()
    legacy_only: list[dict[str, Any]] = []
    shadow_only: list[dict[str, Any]] = []
    decay_reversals: list[dict[str, Any]] = []
    replay: list[dict[str, Any]] = []
    run_dates: set[str] = set()

    for path, payload in rows:
        observed = _observed_date(payload)
        if observed is not None:
            run_dates.add(observed.isoformat())
        if payload.get("status") == "failed":
            status_counts["error"] += 1
            continue
        shadow_titles = list(payload.get("shadow_top2", []))
        status_counts["empty" if not shadow_titles else "success"] += 1
        overlap_counts[str(payload.get("overlap_count", 0))] += 1
        candidates = list(payload.get("candidates", []))
        by_title = {str(item.get("title")): item for item in candidates}
        for rejection in payload.get("hard_filter_rejections", []):
            hard_filter_reasons.update(rejection.get("reasons", []))
        for candidate in candidates:
            evidence_strengths.update(
                item.get("strength", "none")
                for item in candidate.get("evidence", {}).values()
            )
        for title in payload.get("legacy_only", []):
            item = by_title.get(str(title), {})
            legacy_only.append(
                {
                    "run_id": path.parent.name,
                    "title": title,
                    "hard_filter_result": item.get("hard_filter_result"),
                    "hard_filter_reasons": item.get("hard_filter_reasons", []),
                    "base_score": item.get("base_score"),
                }
            )
        ranking = list(payload.get("ranking", []))
        ranking_by_title = {str(item.get("title")): item for item in ranking}
        for title in payload.get("shadow_only", []):
            item = ranking_by_title.get(str(title), {})
            shadow_only.append(
                {
                    "run_id": path.parent.name,
                    "title": title,
                    "rank": item.get("rank"),
                    "final_score": item.get("final_score"),
                    "score_breakdown": item.get("score_breakdown", {}),
                    "evidence": item.get("evidence", {}),
                }
            )
        base_ranks = _base_rank(ranking)
        for item in ranking:
            candidate_id = str(item.get("candidate_id", ""))
            if item.get("topic_decay_applied") and base_ranks.get(candidate_id) != item.get("rank"):
                decay_reversals.append(
                    {
                        "run_id": path.parent.name,
                        "title": item.get("title"),
                        "base_rank": base_ranks.get(candidate_id),
                        "final_rank": item.get("rank"),
                        "topic_decay": item.get("topic_decay"),
                    }
                )
        replay.append(
            {"run_id": path.parent.name, **replay_result(path.parent, payload)}
        )

    expected_days = (end - start).days + 1
    return {
        "window": {"start_kst": start.isoformat(), "end_kst": end.isoformat()},
        "expected_days": expected_days,
        "observed_dates": sorted(run_dates),
        "observed_day_count": len(run_dates),
        "window_complete": len(run_dates) == expected_days,
        "status_counts": dict(sorted(status_counts.items())),
        "hard_filter_reasons": dict(sorted(hard_filter_reasons.items())),
        "evidence_strengths": dict(sorted(evidence_strengths.items())),
        "overlap_counts": dict(sorted(overlap_counts.items())),
        "legacy_only": legacy_only,
        "shadow_only": shadow_only,
        "topic_decay_rank_reversals": decay_reversals,
        "replay": replay,
        "replay_all_match": bool(replay)
        and all(item.get("status") == "match" for item in replay),
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    window = report["window"]
    lines = [
        "# News Worthiness Shadow 14-day Report",
        "",
        f"- window_kst: {window['start_kst']} .. {window['end_kst']}",
        f"- observed_days: {report['observed_day_count']}/{report['expected_days']}",
        f"- window_complete: {str(report['window_complete']).lower()}",
        f"- status_counts: `{json.dumps(report['status_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- overlap_counts: `{json.dumps(report['overlap_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- replay_all_match: {str(report['replay_all_match']).lower()}",
        "",
        "## Hard Filter reasons",
        "",
        f"`{json.dumps(report['hard_filter_reasons'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Evidence strength",
        "",
        f"`{json.dumps(report['evidence_strengths'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Legacy only",
        "",
        f"```json\n{json.dumps(report['legacy_only'], ensure_ascii=False, indent=2)}\n```",
        "",
        "## Shadow only",
        "",
        f"```json\n{json.dumps(report['shadow_only'], ensure_ascii=False, indent=2)}\n```",
        "",
        "## Topic decay rank reversals",
        "",
        f"```json\n{json.dumps(report['topic_decay_rank_reversals'], ensure_ascii=False, indent=2)}\n```",
        "",
        "## Deterministic replay",
        "",
        f"```json\n{json.dumps(report['replay'], ensure_ascii=False, indent=2)}\n```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START)
    parser.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END)
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    report = aggregate(load_window(args.runs_dir, args.start, args.end), args.start, args.end)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.start.isoformat()}_{args.end.isoformat()}"
    json_path = args.output_dir / f"{stem}.json"
    markdown_path = args.output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        f"shadow_report window_complete={str(report['window_complete']).lower()} "
        f"observed_days={report['observed_day_count']}/{report['expected_days']} "
        f"replay_all_match={str(report['replay_all_match']).lower()} path={markdown_path}"
    )
    return 0 if report["window_complete"] and report["replay_all_match"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
