#!/usr/bin/env python3
"""Run Hunt News Lane B: at most one evidence-first deep article per slot."""

from __future__ import annotations

import argparse, json, logging, sys, threading, urllib.request
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient
from scripts.evidence_topic_miner import atomic_write_new, build_payload, persist_miner_run
from scripts.run_daily_pipeline import PipelineError, PipelineLock, configure_logger, make_run_id, make_topic_context, read_publish_result, resolve_codex, run_topic_pipeline
from scripts.snapshot_topic_inventory import build_snapshot

KST = timezone(timedelta(hours=9))
OUTPUT = ROOT / "output/evidence-deep-article-runs"
MINER_ROOT = ROOT / "output/topic-miner"
LOCK = ROOT / "logs/evidence-deep-article.lock"
DAILY_LIMIT = 2


def write_json_new(path: Path, payload: Mapping[str, Any]) -> None:
    atomic_write_new(path, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode())


def refresh_inventory() -> Path:
    destination = MINER_ROOT / "inventory-latest.json"
    snapshot = build_snapshot(WordPressClient(WordPressConfig.from_environment(ROOT / ".env")))
    data = (json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n").encode()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    archive = MINER_ROOT / "inventory" / f"{stamp}.json"
    atomic_write_new(archive, data)
    from scripts.evidence_topic_miner import atomic_replace
    atomic_replace(destination, data)
    return destination


def published_today(root: Path, day: str) -> int:
    count = 0
    for path in root.glob("*/result.json"):
        try: payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): continue
        if payload.get("kst_date") == day and payload.get("deep_article") == "published" and payload.get("failed") is False:
            count += 1
    return count


def candidate_plan(candidate: Mapping[str, Any]) -> dict[str, Any]:
    title = str(candidate["title_seed"])
    evidence = candidate["evidence"]
    return {
        "title": title,
        "category": "개발 트렌드",
        "content_type": "evidence_deep_article",
        "tags": ["개발 기록", "자동화", str(candidate["recommended_format"])],
        "reason": str(candidate["real_trigger"]),
        "research_focus": "evidence_candidate의 주장과 근거만 사용하고 공개 commit, test, log를 직접 대조한다.",
        "primary_keyword": Path(str(candidate["source_anchor"])).stem.replace("_", " "),
        "secondary_keywords": "",
        "target_reader": str(candidate["target_reader"]),
        "demand_signal_source": "evidence_first_then_optional_demand_check",
        "observed_problem_phrase": str(candidate["problem"]),
        "user_action": str(candidate["why_it_matters"]),
        "search_intent": "실제 구현·실험·운영 기록을 재현하고 같은 문제를 회피한다.",
        "original_value_plan": str(candidate["unique_takeaway"]),
        "evidence_plan": json.dumps(evidence, ensure_ascii=False),
        "duplicate_check": json.dumps(candidate["existing_post_overlap"], ensure_ascii=False),
        "internal_link_candidates": "",
        "topic_cluster": "Hunt News 운영기",
        "pillar_candidate": "false",
        "sources": json.dumps(evidence.get("public_urls", []), ensure_ascii=False),
        "problem_origin": str(candidate["real_trigger"]),
        "editorial_thesis": str(candidate["unique_takeaway"]),
        "chosen_focus": str(candidate["problem"]),
        "rejected_angle": "뉴스·공식 문서 재요약과 근거 없는 일반론",
        "structure_mode": str(candidate["recommended_format"]),
        "evidence_candidate": dict(candidate),
        "evidence_contract": dict(candidate["evidence_contract"]),
    }


def run_selected_candidate(candidate: Mapping[str, Any], run_id: str, logger: logging.Logger) -> dict[str, Any]:
    plan = candidate_plan(candidate)
    context = make_topic_context(run_id, plan["title"], category=plan["category"], tags=tuple(plan["tags"]), reason=plan["reason"], research_focus=plan["research_focus"], content_type=plan["content_type"])
    result = run_topic_pipeline(resolve_codex(), context, plan, logger, timeout_seconds=3600, resume=False, publish_lock=threading.Lock(), humanize_lock=threading.Lock())
    if result.get("post_id") is None: raise PipelineError("Publisher did not return post_id")
    return result


def audit_public(result: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    url = str(result.get("url", ""))
    if not url.startswith("https://"): raise PipelineError("published URL is not HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent":"HuntNews-EvidenceAudit/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
        status = response.status
    title_ok = str(candidate["title_seed"]) in body
    evidence_ok = all(str(link).split("#",1)[0] in body for link in candidate["evidence"].get("public_urls", []))
    if status != 200 or not title_ok or not evidence_ok: raise PipelineError("public HTML evidence audit failed")
    return {"url":url,"http_status":status,"title_present":title_ok,"evidence_links_present":evidence_ok,"checked_at":datetime.now(UTC).isoformat()}


def execute(*, run_id: str, inventory_path: Path, apply: bool, topic_runner: Callable[[Mapping[str, Any], str, logging.Logger], dict[str, Any]] = run_selected_candidate, public_auditor: Callable[[Mapping[str, Any], Mapping[str, Any]], dict[str, Any]] = audit_public, output_root: Path = OUTPUT, miner_root: Path = MINER_ROOT, repo: Path = ROOT) -> dict[str, Any]:
    now = datetime.now(KST); day = now.date().isoformat(); run_dir = output_root / run_id
    checkpoint_path = miner_root / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.is_file() else None
    payload, processing, next_checkpoint = build_payload(repo=repo, inventory_path=inventory_path, run_date=now.date(), checkpoint=checkpoint)
    miner_dir = miner_root / day / run_id
    persist_miner_run(miner_dir, checkpoint_path, payload, processing, next_checkpoint)
    base = {"run_id":run_id,"kst_date":day,"publication_mode":"briefing_only","failed":False,"wordpress_write_count":0,"candidate_count":len(payload["candidates"])}
    if published_today(output_root, day) >= DAILY_LIMIT:
        return {**base,"deep_article":"daily_limit_reached"}
    if not payload["candidates"]:
        return {**base,"deep_article":"no_publishable_topic"}
    candidate = payload["candidates"][0]
    if not apply:
        return {**base,"deep_article":"ready_not_published","candidate_id":candidate["candidate_id"]}
    published = topic_runner(candidate, run_id, configure_logger(now.date()))
    return {**base,"publication_mode":"dual_lane","deep_article":"published","wordpress_write_count":1,"candidate_id":candidate["candidate_id"],"publication":published,"public_audit":public_auditor(published,candidate)}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--apply",action="store_true"); parser.add_argument("--dry-run",action="store_true"); parser.add_argument("--run-id",default=""); parser.add_argument("--inventory",type=Path); args=parser.parse_args()
    if args.apply and args.dry_run: parser.error("choose --apply or --dry-run")
    run_id=args.run_id or make_run_id(); lock=PipelineLock(LOCK)
    try:
        lock.acquire()
        inventory=args.inventory or (refresh_inventory() if args.apply else MINER_ROOT/"inventory-latest.json")
        result=execute(run_id=run_id,inventory_path=inventory,apply=args.apply)
        write_json_new(OUTPUT/run_id/"result.json",result)
        print(json.dumps(result,ensure_ascii=False)); return 0
    except Exception as exc:
        failure={"run_id":run_id,"failed":True,"deep_article":"failed","error_type":type(exc).__name__,"wordpress_write_count":"unknown" if args.apply else 0}
        try: write_json_new(OUTPUT/run_id/"result.json",failure)
        except Exception: pass
        print(json.dumps(failure,ensure_ascii=False)); return 1
    finally: lock.release()

if __name__ == "__main__": raise SystemExit(main())
