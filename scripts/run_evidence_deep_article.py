#!/usr/bin/env python3
"""Run Hunt News Lane B: at most one evidence-first deep article per KST day."""

from __future__ import annotations

import argparse, hashlib, json, logging, re, sys, threading, urllib.request
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publisher.config import WordPressConfig
from publisher.wordpress import WordPressClient
from scripts.evidence_topic_miner import atomic_replace, atomic_write_new, build_payload, choose_candidates, persist_miner_run
from scripts.run_daily_pipeline import PipelineError, PipelineLock, configure_logger, make_run_id, make_topic_context, read_publish_result, resolve_codex, run_topic_pipeline
from scripts.snapshot_topic_inventory import build_snapshot
from scripts.editorial_epoch import EpochError, load_epoch, reject_legacy_run, validate_candidate

KST = timezone(timedelta(hours=9))
OUTPUT = ROOT / "output/evidence-deep-article-runs"
MINER_ROOT = ROOT / "output/topic-miner"
LOCK = ROOT / "logs/evidence-deep-article.lock"
DAILY_LIMIT = 1


def write_json_new(path: Path, payload: Mapping[str, Any]) -> None:
    atomic_write_new(path, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode())

def write_progress(path: Path, *, stage: str, wordpress_write_count: int | str) -> None:
    atomic_replace(path, (json.dumps({"stage":stage,"wordpress_write_count":wordpress_write_count,"kst_date":datetime.now(KST).date().isoformat()}, ensure_ascii=False, indent=2) + "\n").encode())


def refresh_inventory() -> Path:
    destination = MINER_ROOT / "inventory-latest.json"
    snapshot = build_snapshot(WordPressClient(WordPressConfig.from_environment(ROOT / ".env")))
    data = (json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n").encode()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    archive = MINER_ROOT / "inventory" / f"{stamp}.json"
    atomic_write_new(archive, data)
    atomic_replace(destination, data)
    return destination


def read_reconciliation(directory: Path) -> dict[str, Any] | None:
    """Accept a separately reviewed decision tied to immutable local evidence."""
    path = directory / "reconciliation.json"
    if not path.exists():
        return None
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        actual = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                  for name in ("result.json", "progress.json") if (directory / name).is_file()}
        if (type(receipt.get("schema_version")) is not int or receipt["schema_version"] != 1 or receipt.get("run_id") != directory.name
                or type(receipt.get("wordpress_write_count")) is not int
                or receipt["wordpress_write_count"] not in (0, 1)
                or receipt.get("original_state_sha256") != actual or not actual
                or not isinstance(receipt.get("reviewed_by"), str) or not receipt["reviewed_by"].strip()
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(receipt.get("kst_date", "")))):
            raise ValueError("invalid reconciliation contract")
        if datetime.fromisoformat(receipt["checked_at"]).tzinfo is None:
            raise ValueError("missing timezone")
        datetime.fromisoformat(receipt["kst_date"])
        evidence = receipt["evidence"]
        if not isinstance(evidence, list) or len(evidence) != 2 or {item["kind"] for item in evidence} != {"pipeline_trace", "wordpress_inventory"}:
            raise ValueError("both execution and WordPress evidence required")
        for item in evidence:
            relative = Path(item["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("evidence must be inside run directory")
            target = directory / relative
            if directory.resolve() not in target.resolve().parents:
                raise ValueError("evidence escaped run directory")
            if hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("evidence changed")
        return receipt
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise PipelineError(f"Invalid publication reconciliation: {directory.name}") from exc


def published_today(root: Path, day: str, *, repo: Path = ROOT) -> int:
    try:
        epoch = load_epoch(root, repo)
    except EpochError as exc:
        raise PipelineError("Editorial retirement seal validation failed") from exc
    retired = {row["run_id"] for row in epoch["retired_runs"]} if epoch else set()
    count = 0
    for directory in root.iterdir() if root.exists() else ():
        if not directory.is_dir():
            continue
        records = []
        for name in ("result.json", "progress.json"):
            path = directory / name
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("not an object")
            except (OSError, ValueError) as exc:
                raise PipelineError(f"Unreadable publication state: {directory.name}/{name}") from exc
            records.append(payload)
        reconciliation = read_reconciliation(directory)
        if reconciliation is not None:
            if reconciliation["wordpress_write_count"] == 0 and any(
                    row.get("wordpress_write_count") == 1 or
                    (row.get("deep_article") == "published" and row.get("failed") is False)
                    for row in records):
                raise PipelineError(f"Reconciliation contradicts confirmed write: {directory.name}")
            records = [reconciliation]
        if any(payload.get("kst_date") == day and (
                (payload.get("deep_article") == "published" and payload.get("failed") is False)
                or payload.get("wordpress_write_count") == 1
        ) for payload in records):
            count += 1
        elif any(payload.get("wordpress_write_count") == "unknown" for payload in records):
            # Unknown may mean the server accepted a request before a timeout.
            # Even yesterday's unresolved write must be reconciled, not retried.
            if not any(payload.get("wordpress_write_count") == 1 for payload in records):
                if directory.name in retired:
                    continue  # Still unknown, explicitly retired; never a zero-write finding.
                raise PipelineError(f"Publication reconciliation required: {directory.name}")
    return count


def resume_public_audit(run_id: str, *, output_root: Path = OUTPUT,
                        public_auditor: Callable = None) -> dict[str, Any]:
    """Retry only the read-only audit of a saved confirmed publication."""
    reject_legacy_run(run_id, output_root, ROOT)
    run_dir = output_root / run_id
    receipt = json.loads((run_dir / "publication.json").read_text(encoding="utf-8"))
    if receipt.get("wordpress_write_count") != 1:
        raise PipelineError("No confirmed publication receipt to audit")
    audit = (public_auditor or audit_public)(receipt["publication"], receipt["candidate"])
    result = {key: value for key, value in receipt.items() if key != "candidate"}
    result.update(failed=False, deep_article="published", public_audit=audit)
    # Preserve the failed result as historical evidence; this is a separate
    # read-only recovery receipt, not permission to run Publisher again.
    write_json_new(run_dir / "public-audit-recovery.json", result)
    return result


def candidate_category(candidate: Mapping[str, Any]) -> str:
    """Classify the reader's problem, not incidental evidence filenames."""
    subject = " ".join(str(candidate.get(key, "")) for key in
                       ("title_seed", "problem", "unique_takeaway")).casefold()
    if any(term in subject for term in ("rest api", "rest-api", "rest_api", "rest 응답", "wordpress api")):
        return "REST API 발행"
    if any(term in subject for term in ("wordpress", "워드프레스", "sitemap", "사이트맵", "noindex")):
        return "WordPress 운영"
    return "자동화·테스트"


def candidate_in_editorial_scope(candidate: Mapping[str, Any]) -> bool:
    """Require the reader-facing problem to concern WordPress publishing."""
    subject = " ".join(str(candidate.get(key, "")) for key in
                       ("title_seed", "problem", "why_it_matters", "unique_takeaway")).casefold()
    return candidate.get("publishability") == "READY" and any(
        term in subject for term in ("wordpress", "워드프레스", "블로그 발행", "게시글 발행",
                                     "자동발행", "자동 발행", "publisher", "sitemap", "noindex")
    )


def candidate_plan(candidate: Mapping[str, Any]) -> dict[str, Any]:
    title = str(candidate["title_seed"])
    evidence = candidate["evidence"]
    return {
        "title": title,
        "category": candidate_category(candidate),
        "content_type": "evidence_deep_article",
        "tags": ["개발 기록", "자동화", str(candidate["recommended_format"])],
        "reason": str(candidate["real_trigger"]),
        "research_focus": "guides/editorial-concept.md의 WordPress 자동발행 실전 운영 노트 범위를 따른다. evidence_candidate의 주장과 근거만 사용하고 공개 commit, test, log를 직접 대조한다. 실제 실패/변경 → 근거 → 해결 → 독자 실행 방법 → 한계를 설명한다. 범용 뉴스나 다른 프로젝트로 주제를 확장하지 않는다.",
        # The daily pipeline and Reviewer require the primary keyword to appear
        # in the fixed Editor title. Evidence source filenames are identifiers,
        # not necessarily useful search phrases.
        "primary_keyword": title,
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
        "topic_cluster": candidate_category(candidate),
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
    plan["inventory_path"] = candidate.get("_inventory_path", str(MINER_ROOT / "inventory-latest.json"))
    context = make_topic_context(run_id, plan["title"], category=plan["category"], tags=tuple(plan["tags"]), reason=plan["reason"], research_focus=plan["research_focus"], content_type=plan["content_type"])
    context.directory.parent.mkdir(parents=True, exist_ok=False)
    result = run_topic_pipeline(resolve_codex(), context, plan, logger, timeout_seconds=3600, resume=False, publish_lock=threading.Lock(), humanize_lock=threading.Lock())
    if result.get("post_id") is None: raise PipelineError("Publisher did not return post_id")
    return result


def audit_evidence_links(body: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
    public_urls = [str(link).split("#", 1)[0] for link in evidence.get("public_urls", [])]
    matched = [link for link in public_urls if link in body]
    commits = [str(value) for value in evidence.get("commits", [])]
    files = [str(value) for value in evidence.get("files", [])]
    tests = [str(value) for value in evidence.get("tests", [])]
    logs = [str(value) for value in evidence.get("logs", [])]
    checks = {
        "commit": not commits or any(
            any(f"/commit/{sha}" in link for sha in commits) for link in matched
        ),
        "implementation_file": not files or any(
            any(path in link for path in files) for link in matched
        ),
        "test": not tests or any(
            "/tests/" in link or any(path in link for path in logs)
            for link in matched
        ),
        "log": not logs or any(
            any(path in link for path in logs) for link in matched
        ),
    }
    return {"passed": all(checks.values()), "matched_count": len(matched), "checks": checks}


def audit_public(result: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    url = str(result.get("url", ""))
    if not url.startswith("https://"): raise PipelineError("published URL is not HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent":"HuntNews-EvidenceAudit/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
        status = response.status
    title_ok = str(candidate["title_seed"]) in body
    evidence_audit = audit_evidence_links(body, candidate["evidence"])
    evidence_ok = bool(evidence_audit["passed"])
    if status != 200 or not title_ok or not evidence_ok: raise PipelineError("public HTML evidence audit failed")
    return {"url":url,"http_status":status,"title_present":title_ok,"evidence_links_present":evidence_ok,"evidence_link_audit":evidence_audit,"checked_at":datetime.now(UTC).isoformat()}


def execute(*, run_id: str, inventory_path: Path, apply: bool, topic_runner: Callable[[Mapping[str, Any], str, logging.Logger], dict[str, Any]] = run_selected_candidate, public_auditor: Callable[[Mapping[str, Any], Mapping[str, Any]], dict[str, Any]] = audit_public, output_root: Path = OUTPUT, miner_root: Path = MINER_ROOT, repo: Path = ROOT, logger: logging.Logger | None = None) -> dict[str, Any]:
    now = datetime.now(KST); day = now.date().isoformat(); run_dir = output_root / run_id
    reject_legacy_run(run_id, output_root, repo)
    epoch = load_epoch(output_root, repo)
    run_dir.mkdir(parents=True, exist_ok=False)
    progress_path = run_dir / "progress.json"
    write_progress(progress_path, stage="pre_mining", wordpress_write_count=0)
    checkpoint_path = miner_root / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.is_file() else None
    payload, processing, next_checkpoint = build_payload(repo=repo, inventory_path=inventory_path, run_date=now.date(), checkpoint=checkpoint)
    payload["scope_rejections"] = [candidate["candidate_id"] for candidate in payload["candidates"] if not candidate_in_editorial_scope(candidate)]
    payload["candidates"] = [candidate for candidate in payload["candidates"] if candidate_in_editorial_scope(candidate)]
    epoch_rejections = []
    if epoch:
        # Quarantine before the miner's top-three limit. Otherwise three old
        # high-scoring candidates hide a genuine new event and an empty result
        # can advance its checkpoint without ever considering it for publication.
        processed_ids = set((checkpoint or {}).get("processed_event_ids", []))
        pool = [row for row in processing["processed"]
                if row.get("publishability") == "READY" and row["candidate_id"] not in processed_ids]
        payload["scope_rejections"] = [row["candidate_id"] for row in pool if not candidate_in_editorial_scope(row)]
        accepted = []
        for candidate in pool:
            if not candidate_in_editorial_scope(candidate):
                continue
            try:
                validate_candidate(candidate, epoch, repo)
            except EpochError:
                epoch_rejections.append(candidate["candidate_id"])
            else:
                accepted.append(candidate)
        payload["candidates"] = choose_candidates(accepted)
        payload["ready_count"] = len(payload["candidates"])
    payload["epoch_rejections"] = epoch_rejections
    if not payload["candidates"]:
        payload["status"] = "no_publishable_topic"
    miner_dir = miner_root / day / run_id
    run_checkpoint = run_dir / "miner-checkpoint.json"
    persist_miner_run(miner_dir, run_checkpoint, payload, processing, next_checkpoint)
    def advance_checkpoint() -> None:
        atomic_replace(checkpoint_path, (json.dumps(next_checkpoint, ensure_ascii=False, indent=2) + "\n").encode())
    base = {"run_id":run_id,"kst_date":day,"publication_mode":"briefing_only","failed":False,"wordpress_write_count":0,"candidate_count":len(payload["candidates"]),"scope_rejections":payload["scope_rejections"]}
    if epoch:
        base.update(retired_unknown_run_ids=[row["run_id"] for row in epoch["retired_runs"]], epoch_rejections=epoch_rejections)
    if not payload["candidates"]:
        try:
            published_today(output_root, day, repo=repo)
        except PipelineError:
            # No candidate means no Publisher call, so an unresolved historical
            # write need not turn a normal empty evaluation into a failure.
            # Keep its checkpoint intact and expose the pending reconciliation.
            return {**base,"deep_article":"no_publishable_topic","reconciliation_required":True,"checkpoint_advanced":False}
        advance_checkpoint()
        return {**base,"deep_article":"no_publishable_topic"}
    if published_today(output_root, day, repo=repo) >= DAILY_LIMIT:
        return {**base,"deep_article":"daily_limit_reached"}
    candidate = payload["candidates"][0]
    # A public audit cannot match a link absent from the approved source set.
    # Reject that impossible contract before writing anything to WordPress.
    sources = candidate["evidence"]
    if not audit_evidence_links(" ".join(sources.get("public_urls", [])), sources)["passed"]:
        raise PipelineError("Candidate public sources cannot satisfy the publication audit")
    if not apply:
        return {**base,"deep_article":"ready_not_published","candidate_id":candidate["candidate_id"]}
    write_progress(progress_path, stage="publisher_started", wordpress_write_count="unknown")
    published = topic_runner({**candidate, "_inventory_path": str(inventory_path.resolve())}, run_id, logger or configure_logger(now.date()))
    write_progress(progress_path, stage="publisher_completed", wordpress_write_count=1)
    write_json_new(run_dir / "publication.json", {
        **base, "publication_mode": "dual_lane", "wordpress_write_count": 1,
        "candidate_id": candidate["candidate_id"], "candidate": candidate,
        "publication": published,
    })
    # A confirmed WordPress publish must consume the candidate before the
    # independent public-HTML audit. Retrying a published candidate after an
    # audit-only failure would risk a duplicate post.
    advance_checkpoint()
    audit = public_auditor(published,candidate)
    return {**base,"publication_mode":"dual_lane","deep_article":"published","wordpress_write_count":1,"candidate_id":candidate["candidate_id"],"publication":published,"public_audit":audit}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--apply",action="store_true"); parser.add_argument("--dry-run",action="store_true"); parser.add_argument("--run-id",default=""); parser.add_argument("--inventory",type=Path); parser.add_argument("--resume-public-audit", action="store_true"); args=parser.parse_args()
    if args.apply and args.dry_run: parser.error("choose --apply or --dry-run")
    if args.resume_public_audit and (not args.run_id or args.apply or args.dry_run):
        parser.error("--resume-public-audit requires --run-id and cannot publish")
    run_id=args.run_id or make_run_id(); lock=PipelineLock(LOCK)
    try:
        lock.acquire()
        if args.resume_public_audit:
            result = resume_public_audit(run_id)
            print(json.dumps(result, ensure_ascii=False)); return 0
        inventory=args.inventory or (refresh_inventory() if args.apply else MINER_ROOT/"inventory-latest.json")
        result=execute(run_id=run_id,inventory_path=inventory,apply=args.apply)
        write_json_new(OUTPUT/run_id/"result.json",result)
        print(json.dumps(result,ensure_ascii=False)); return 0
    except Exception as exc:
        progress_path=OUTPUT/run_id/"progress.json"
        try: write_count=json.loads(progress_path.read_text(encoding="utf-8")).get("wordpress_write_count", "unknown")
        except Exception: write_count="unknown" if args.apply else 0
        failure={"run_id":run_id,"kst_date":datetime.now(KST).date().isoformat(),"failed":True,"deep_article":"failed","error_type":type(exc).__name__,"wordpress_write_count":write_count}
        try: write_json_new(OUTPUT/run_id/"result.json",failure)
        except Exception: pass
        print(json.dumps(failure,ensure_ascii=False)); return 1
    finally: lock.release()

if __name__ == "__main__": raise SystemExit(main())
