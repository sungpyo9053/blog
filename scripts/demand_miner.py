#!/usr/bin/env python3
"""Turn observed WordPress problems into HOLD candidates for Evidence Lab."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evidence_topic_miner import atomic_write_new, canonical_json, normalized_tokens

CONTRACT_VERSION = "demand-miner.v1"
ALLOWED_INTENTS = {"troubleshooting", "implementation", "comparison", "cost", "migration", "monitoring", "security", "purchase_decision", "informational_only"}
TOPIC_TERMS = {"wordpress", "rest", "api", "pagination", "cron", "systemd", "sitemap", "noindex", "plugin", "플러그인", "publisher", "발행", "lightsail", "backup", "rollback", "media", "canonical"}


def _overlap(candidate: dict[str, Any], inventory: list[dict[str, Any]]) -> dict[str, Any]:
    known_id = candidate.get("existing_post_id")
    if known_id is not None:
        match = next((post for post in inventory if int(post.get("post_id", 0)) == int(known_id)), None)
        if match:
            return {"result": "exact", "post_id": match.get("post_id"), "url": match.get("url"), "reason": "declared_existing_search_intent"}
    known_url = str(candidate.get("existing_post_url", "")).rstrip("/")
    if known_url:
        match = next((post for post in inventory if str(post.get("url", "")).rstrip("/") == known_url), None)
        if match:
            return {"result": "exact", "post_id": match.get("post_id"), "url": match.get("url"), "reason": "declared_existing_search_intent"}
    tokens = normalized_tokens(f"{candidate['exact_problem']} {candidate.get('title_seed','')}")
    best: tuple[float, dict[str, Any] | None] = (0.0, None)
    for post in inventory:
        other = normalized_tokens(f"{post.get('title','')} {post.get('slug','')} {post.get('excerpt','')}")
        score = len(tokens & other) / len(tokens | other) if tokens and other else 0.0
        if score > best[0]:
            best = (score, post)
    if best[0] >= 0.34 and best[1]:
        return {"result": "probable", "post_id": best[1].get("post_id"), "url": best[1].get("url"), "similarity": round(best[0], 4)}
    return {"result": "none"}


def evaluate(source: dict[str, Any], inventory: list[dict[str, Any]]) -> dict[str, Any]:
    intent = str(source.get("commercial_intent", ""))
    if intent not in ALLOWED_INTENTS:
        raise ValueError(f"invalid commercial_intent: {intent}")
    text = f"{source.get('exact_problem','')} {source.get('scope_terms','')}".casefold()
    in_scope = any(term in text for term in TOPIC_TERMS)
    overlap = _overlap(source, inventory)
    demand_ok = bool(source.get("demand_source") and (source.get("demand_url") or source.get("search_console_query")))
    asset_ok = bool(source.get("possible_asset"))
    status = "HOLD"
    rejection_reason = None
    if not in_scope or not demand_ok:
        status, rejection_reason = "REJECT", "outside_scope_or_missing_demand"
    elif overlap["result"] != "none":
        status, rejection_reason = "REJECT", "existing_post_overlap"
    score = int(source.get("demand_strength", 0)) * 4 + int(source.get("commercial_fit", 0)) * 3 + (2 if asset_ok else 0) - int(source.get("experiment_cost", 5))
    public = {key: source.get(key) for key in ("candidate_id", "title_seed", "target_reader", "exact_problem", "demand_source", "demand_url", "search_console_query", "commercial_intent", "proposed_experiment", "required_evidence", "possible_asset", "monetization_path")}
    public.update({"existing_post_overlap": overlap, "status": status, "rejection_reason": rejection_reason, "selection_score": score})
    return public


def build(source_path: Path, inventory_path: Path) -> dict[str, Any]:
    sources = json.loads(source_path.read_text(encoding="utf-8"))
    inventory_payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory = inventory_payload["posts"] if isinstance(inventory_payload, dict) else inventory_payload
    candidates = [evaluate(dict(item), inventory) for item in sources]
    if len(candidates) > 20:
        raise ValueError("Demand Miner accepts at most 20 candidates per run")
    eligible = sorted((row for row in candidates if row["status"] == "HOLD"), key=lambda row: (-row["selection_score"], row["candidate_id"]))
    return {"contract_version": CONTRACT_VERSION, "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(), "inventory_sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(), "candidate_count": len(candidates), "candidates": candidates, "top_candidates": eligible[:5], "evidence_lab_selection": eligible[0] if eligible else None}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# HuntLab Demand Miner", "", f"- candidates: {payload['candidate_count']}", f"- top candidates: {len(payload['top_candidates'])}", ""]
    for index, row in enumerate(payload["top_candidates"], 1):
        lines.extend([f"## {index}. {row['title_seed']}", "", f"- reader: {row['target_reader']}", f"- demand: {row.get('demand_url') or row.get('search_console_query')}", f"- intent: `{row['commercial_intent']}`", f"- experiment: {row['proposed_experiment']}", f"- asset: {row['possible_asset']}", f"- monetization: {row['monetization_path']}", f"- status: `{row['status']}`", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.sources, args.inventory)
    atomic_write_new(args.output_dir / "candidates.json", (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode())
    atomic_write_new(args.output_dir / "candidates.md", render_markdown(payload).encode())
    print(canonical_json({"candidate_count": payload["candidate_count"], "top_count": len(payload["top_candidates"]), "selected": (payload["evidence_lab_selection"] or {}).get("candidate_id")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
