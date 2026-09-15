"""Validate a reviewed operational retirement seal; never infer old write counts.

There is deliberately no seal-creation or migration command. Activation requires an
operator-reviewed snapshot and quiescence evidence, plus an exact approval hash.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
STATES = ("publish", "draft", "pending", "private", "future", "trash")


class EpochError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(value: str) -> str:
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", value).casefold())


def evidence_fingerprint(candidate: dict) -> str:
    evidence = candidate.get("evidence", {})
    normalized = {key: sorted(set(str(x) for x in evidence.get(key, [])))
                  for key in ("commits", "files", "tests", "logs", "public_urls")}
    return digest(json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode())


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise EpochError("Epoch timestamp lacks timezone")
    return result


def run_timestamp(run_id: str) -> datetime:
    if not re.fullmatch(r"\d{8}T\d{6}Z-[a-zA-Z0-9_-]+", run_id):
        raise EpochError("Run ID lacks a canonical UTC timestamp")
    return datetime.strptime(run_id.split("-", 1)[0], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)


def git(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], input=data,
                            capture_output=True, timeout=30)
    if result.returncode:
        raise EpochError("Epoch Git provenance verification failed")
    return result.stdout


def artifact(root: Path, reference: dict) -> dict:
    relative = Path(reference["path"])
    target = root / relative
    if relative.is_absolute() or ".." in relative.parts or root.resolve() not in target.resolve().parents:
        raise EpochError("Epoch evidence path escaped its root")
    raw = target.read_bytes()
    if digest(raw) != reference["sha256"]:
        raise EpochError("Epoch evidence hash changed")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise EpochError("Epoch evidence is not an object")
    return value


def load_epoch(root: Path, repo: Path, *, now: datetime | None = None) -> dict | None:
    path = root / "epoch.json"
    approval_path = root / "epoch-approval.json"
    if not path.exists() and not approval_path.exists():
        return None
    try:
        raw = path.read_bytes(); seal = json.loads(raw)
        approval = json.loads(approval_path.read_text())
        if (approval.get("status") != "RETIREMENT_APPROVED"
                or approval.get("epoch_sha256") != digest(raw)
                or not isinstance(approval.get("reviewed_by"), str) or not approval["reviewed_by"].strip()
                or approval.get("reviewer_kind") not in ("ai", "human")
                or type(seal.get("schema_version")) is not int or seal["schema_version"] != 1
                or seal.get("mode") != "retired_unknown_never_retry"):
            raise EpochError("Epoch approval does not match retirement seal")
        sealed_at = timestamp(seal["sealed_at"])
        current = now or datetime.now(UTC)
        if not sealed_at <= timestamp(approval["reviewed_at"]) <= current:
            raise EpochError("Invalid epoch approval time")
        if seal["starts_on"] != sealed_at.astimezone(KST).date().isoformat():
            raise EpochError("Epoch start date must match sealing KST day")
        cutoff = seal["cutoff_commit"]
        if not re.fullmatch("[0-9a-f]{40}", cutoff):
            raise EpochError("Epoch cutoff is not an exact commit")
        git(repo, "merge-base", "--is-ancestor", cutoff, "HEAD")
        if seal["repository_identity_sha256"] != digest(git(repo, "config", "--get", "remote.origin.url").strip()):
            raise EpochError("Retirement belongs to a different repository")
        inventory = artifact(root, seal["inventory"])
        meta = inventory["metadata"]; posts = inventory["posts"]
        if (meta.get("site") != "https://huntlab.app" or meta.get("complete") is not True or set(meta["statuses"]) != set(STATES)
                or not 0 <= (sealed_at - timestamp(meta["collected_at"])).total_seconds() <= 3600
                or not isinstance(posts, list)):
            raise EpochError("Retirement requires a fresh complete six-status inventory")
        ids = [p["id"] for p in posts]
        if (any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids)
                or any(p["status"] not in STATES for p in posts)
                or any(type(meta["statuses"][s]) is not int or meta["statuses"][s] != sum(p["status"] == s for p in posts) for s in STATES)
                or meta["statuses"]["future"] != 0 or meta["statuses"]["pending"] != 0):
            raise EpochError("Retirement inventory identities/counts or queued writes unsafe")
        quiet = artifact(root, seal["quiescence"])
        if not 0 <= (sealed_at - timestamp(quiet["checked_at"])).total_seconds() <= 3600:
            raise EpochError("Quiescence was not fresh at sealing")
        for side in ("local_executor", "downstream_executor"):
            observation = quiet[side]
            if (type(observation["active_jobs"]) is not int or observation["active_jobs"] != 0
                    or type(observation["in_flight_requests"]) is not int or observation["in_flight_requests"] != 0
                    or not isinstance(observation.get("command"), str) or not observation["command"].strip()):
                raise EpochError("Both execution boundaries must be quiescent")
            artifact(root, observation["evidence"])
        retired = seal["retired_runs"]
        if not isinstance(retired, list) or not retired:
            raise EpochError("Epoch has no explicit retired run allowlist")
        seen = set()
        for row in retired:
            rid = row["run_id"]; started = run_timestamp(rid)
            if rid in seen or started.astimezone(KST).date().isoformat() >= seal["starts_on"]:
                raise EpochError("Retirement may not exempt current or future runs")
            seen.add(rid); directory = root / rid
            if directory.resolve().parent != root.resolve():
                raise EpochError("Retired run directory escaped its root")
            # Pin the complete direct file set: even an added result invalidates
            # an orphan's retirement rather than masking late completion.
            actual = {p.name: digest(p.read_bytes()) for p in directory.iterdir() if p.is_file()}
            if actual != row["state_sha256"] or not any(n in actual for n in ("result.json", "progress.json")):
                raise EpochError("Retired run state changed or is missing")
            records = [json.loads((directory / n).read_text()) for n in ("result.json", "progress.json") if n in actual]
            if not any(r.get("wordpress_write_count") == "unknown" for r in records):
                raise EpochError("Retirement only applies to unresolved unknown state")
            for record in records:
                if record.get("kst_date") not in (None, started.astimezone(KST).date().isoformat()):
                    raise EpochError("Run date conflicts with canonical run ID")
        denied = seal["denied"]
        for key in ("candidate_ids", "titles", "slugs", "evidence_fingerprints"):
            if not isinstance(denied[key], list) or not all(isinstance(x, str) and x for x in denied[key]):
                raise EpochError("Invalid retired candidate denylist")
        if not denied["titles"] or not denied["slugs"]:
            raise EpochError("Legacy identity quarantine must be explicit")
        return seal
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired) as exc:
        raise EpochError("Invalid or changed editorial retirement epoch") from exc


def reject_legacy_run(run_id: str, root: Path, repo: Path) -> None:
    seal = load_epoch(root, repo)
    if seal is not None and run_timestamp(run_id) <= timestamp(seal["sealed_at"]):
        raise EpochError("Legacy run execution/resume is permanently quarantined")


def reject_retired_publication(metadata: dict, root: Path, repo: Path) -> None:
    """Recheck the actual approved title/slug, not only a miner's title seed."""
    seal = load_epoch(root, repo)
    if seal is None:
        return
    for field, deny_key in (("title", "titles"), ("slug", "slugs")):
        if not isinstance(metadata.get(field), str) or not identity(metadata[field]):
            raise EpochError("Epoch publication requires an explicit title and slug")
        if identity(metadata[field]) in {identity(x) for x in seal["denied"][deny_key]}:
            raise EpochError("Final publication identity belongs to a retired candidate")


def validate_candidate(candidate: dict, seal: dict, repo: Path) -> None:
    denied = seal["denied"]
    if (candidate.get("candidate_id") in denied["candidate_ids"]
            or identity(str(candidate.get("title_seed", ""))) in {identity(x) for x in denied["titles"]}
            or (candidate.get("slug") and identity(candidate["slug"]) in {identity(x) for x in denied["slugs"]})
            or evidence_fingerprint(candidate) in denied["evidence_fingerprints"]):
        raise EpochError("Retired candidate identity cannot be retried")
    anchor, separator, trigger = str(candidate.get("event_key", "")).rpartition("@")
    commits = candidate.get("evidence", {}).get("commits", [])
    if not separator or anchor != candidate.get("source_anchor") or trigger not in commits or not commits:
        raise EpochError("Candidate lacks exact new trigger provenance")
    cutoff = seal["cutoff_commit"]
    cutoff_time = timestamp(git(repo, "show", "-s", "--format=%cI", cutoff).decode().strip())
    new_patch_ids = set()
    for commit in commits:
        if not re.fullmatch("[0-9a-f]{40}", commit) or commit == cutoff:
            raise EpochError("Candidate commit is not strictly new")
        git(repo, "merge-base", "--is-ancestor", cutoff, commit)
        git(repo, "merge-base", "--is-ancestor", commit, "HEAD")
        if timestamp(git(repo, "show", "-s", "--format=%cI", commit).decode().strip()) <= cutoff_time:
            raise EpochError("Candidate commit predates the source cutoff")
        if len(git(repo, "show", "-s", "--format=%P", commit).split()) != 1:
            raise EpochError("New candidate requires an unambiguous non-merge diff")
        patch_ids = git(repo, "patch-id", "--stable", data=git(repo, "show", "--format=medium", commit)).splitlines()
        if not patch_ids:
            raise EpochError("Candidate has no actual patch")
        new_patch_ids.update(line.split()[0] for line in patch_ids)
    old_patch_ids = {line.split()[0] for line in git(repo, "patch-id", "--stable", data=git(repo, "log", "--no-merges", "-p", cutoff)).splitlines()}
    if new_patch_ids & old_patch_ids:
        raise EpochError("Candidate replays an old patch")
    changed = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", trigger).decode().splitlines()
    if anchor not in changed:
        raise EpochError("New trigger did not change the claimed source anchor")
