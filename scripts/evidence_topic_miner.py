#!/usr/bin/env python3
"""Evidence-first topic mining. Git seeds events; local records only enrich them."""

from __future__ import annotations

import argparse, ast, hashlib, html, json, os, re, subprocess, tempfile
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CONTRACT_VERSION = "evidence-topic-miner.v1"
MAX_CANDIDATES = 3
EVIDENCE_FORMATS = {"debugging_log", "feature_build", "migration", "benchmark_experiment", "architecture_decision", "operations_incident"}
ALLOWED_GIT_COMMANDS = {"log", "show", "rev-parse", "remote", "merge-base"}
ALLOWED_SOURCE_PREFIXES = ("publisher/", "scripts/", "deploy/wordpress/", "tests/")
BLOCKED_PARTS = {".git", ".ssh", ".aws", ".secrets", "credentials", "node_modules"}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".sqlite", ".db"}
ARTIFACT_PATTERNS = ("logs/*.log", "logs/*.jsonl", "output/runs/**/publisher-audit.jsonl", "output/audits/**/*.json", "output/audits/**/*.md", "output/evaluations/**/*.json", "output/backups/*.json", "docs/work-records/*.md")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}\b", re.I),
    re.compile(r"(?i)\b(?:Cookie|Set-Cookie)\s*:\s*[^\r\n]+"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"(?i)\b(?:password|passwd|token|secret|api[_-]?key)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?<![0-9A-Za-z])(?:\+?82[- ]?)?0?1[016789][- ]?\d{3,4}[- ]?\d{4}(?![0-9A-Za-z])"),
    re.compile(r"/(?:Users|home)/[^/\s]+/"),
)

def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def sha256_text(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()

def redact_text(value: str) -> str:
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    value = re.sub(r"(?i)([?&](?:token|key|password|secret|signature)=)[^&#\s]+", r"\1[REDACTED]", value)
    return re.sub(r"(https?://)[^/@\s:]+:[^/@\s]+@", r"\1[REDACTED]@", value)

def contains_secret(value: str) -> bool:
    return ("-----BEGIN " in value and "PRIVATE KEY-----" in value) or any(p.search(value) for p in SECRET_PATTERNS[1:])

def safe_relative_path(repo: Path, value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe path: {value}")
    if any(part in BLOCKED_PARTS or part.startswith(".env") for part in candidate.parts) or candidate.suffix.casefold() in BLOCKED_SUFFIXES:
        raise ValueError(f"blocked path: {value}")
    resolved = (repo / candidate).resolve()
    if resolved != repo.resolve() and repo.resolve() not in resolved.parents:
        raise ValueError(f"path escapes repository: {value}")
    return candidate.as_posix()

def sanitize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    query = [(k, "[REDACTED]" if re.search(r"token|key|password|secret|signature", k, re.I) else v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)]
    return urlunsplit((parsed.scheme, f"{parsed.hostname or ''}{':' + str(parsed.port) if parsed.port else ''}", parsed.path, urlencode(query), ""))

def run_git(repo: Path, args: Sequence[str]) -> str:
    if not args or args[0] not in ALLOWED_GIT_COMMANDS:
        raise ValueError("only read-only git commands are allowed")
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, shell=False).stdout

@dataclass(frozen=True)
class CommitRecord:
    sha: str
    timestamp: str
    subject: str
    files: tuple[str, ...]
    symbols_by_file: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    ancestors: tuple[str, ...] = ()
    parents: tuple[str, ...] = ()
    renames: tuple[tuple[str, str], ...] = ()
    is_merge: bool = False
    is_revert: bool = False

@dataclass
class Event:
    anchor: str
    trigger_commit: str = ""
    event_key: str = ""
    commits: list[str] = field(default_factory=list)
    commit_times: dict[str, str] = field(default_factory=dict)
    subjects: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    test_runs: list[dict[str, Any]] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    public_urls: list[str] = field(default_factory=list)
    post_id: int | None = None
    slug: str = ""; title: str = ""; target_reader: str = ""; reader_action: str = ""; unique_takeaway: str = ""
    structured_before_after: Mapping[str, Any] | None = None
    changed_symbols: list[str] = field(default_factory=list)
    ambiguous_evidence: list[str] = field(default_factory=list)
    recommended_format: str = ""
    contract_fields: dict[str, Any] = field(default_factory=dict)
    public_access_verified: bool = False

def diff_symbols(diff_text: str) -> dict[str, tuple[str, ...]]:
    """Return conservative identifier sets per changed file from a zero-context diff."""
    current = ""; found: dict[str, set[str]] = {}
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]; found.setdefault(current, set()); continue
        if not current or not line.startswith(("+", "-")) or line.startswith(("+++", "---")): continue
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", line[1:]):
            normalized = re.sub(r"^(?:test_|Test)", "", token).casefold()
            if normalized not in {"self", "return", "assert", "true", "false", "none", "from", "import", "class", "def"}:
                found[current].add(normalized)
    return {path: tuple(sorted(values)) for path, values in found.items()}

def collect_commits(repo: Path, max_commits: int = 60, since_commit: str = "") -> list[CommitRecord]:
    rows = run_git(repo, ["log", f"{since_commit}..HEAD" if since_commit else "HEAD", f"--max-count={max_commits}", "--date=iso-strict", "--format=%H%x1f%ad%x1f%s"]).splitlines()
    result = []
    for row in rows:
        parts = row.split("\x1f", 2)
        if len(parts) != 3: continue
        sha, timestamp, subject = parts
        files = []
        for name in run_git(repo, ["show", "--pretty=format:", "--name-only", sha]).splitlines():
            try: safe = safe_relative_path(repo, name.strip())
            except ValueError: continue
            if safe and safe.startswith(ALLOWED_SOURCE_PREFIXES): files.append(safe)
        patch = run_git(repo, ["show", "--format=", "--unified=0", "--find-renames", sha])
        name_status = run_git(repo, ["show", "--format=", "--name-status", "--find-renames", sha]).splitlines()
        renames = []
        for status_row in name_status:
            columns = status_row.split("\t")
            if columns and columns[0].startswith("R") and len(columns) == 3:
                try: renames.append((safe_relative_path(repo, columns[1]), safe_relative_path(repo, columns[2])))
                except ValueError: pass
        parents = tuple(run_git(repo, ["show", "-s", "--format=%P", sha]).strip().split())
        result.append(CommitRecord(sha, timestamp, redact_text(subject), tuple(sorted(set(files))), diff_symbols(patch), (), parents, tuple(renames), len(parents) > 1, subject.casefold().startswith("revert")))
    return result

def imported_source_paths(repo: Path, test_path: str) -> list[str]:
    path = repo / safe_relative_path(repo, test_path)
    if not path.is_file() or path.stat().st_size > 512_000: return []
    try: tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError): return []
    result = []
    for node in ast.walk(tree):
        module = node.module if isinstance(node, ast.ImportFrom) else None
        if module and module.startswith(("scripts.", "publisher.")):
            relative = module.replace(".", "/") + ".py"
            if (repo / relative).is_file(): result.append(relative)
    return sorted(set(result))

def test_names(repo: Path, value: str, symbols: Sequence[str] = ()) -> list[str]:
    path = repo / safe_relative_path(repo, value)
    if not path.is_file() or path.stat().st_size > 512_000: return []
    try: tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError): return []
    module, result = value.removesuffix(".py").replace("/", "."), []
    for top in tree.body:
        for node in (top.body if isinstance(top, ast.ClassDef) else [top]):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_") and (not symbols or any(symbol in node.name.casefold() for symbol in symbols)):
                result.append(f"{module}.{top.name + '.' if isinstance(top, ast.ClassDef) else ''}{node.name}")
    return sorted(result)

def group_git_events(repo: Path, commits: Sequence[CommitRecord]) -> dict[str, Event]:
    """Link tests only on unique source/import, symbol and ancestry agreement."""
    events: dict[str, Event] = {}
    claimed_tests: set[tuple[str, str]] = set()
    for commit in sorted(commits, key=lambda item: (item.timestamp, item.sha)):
        if commit.is_merge:
            continue
        sources = [p for p in commit.files if not p.startswith("tests/")]
        tests = [p for p in commit.files if p.startswith("tests/")]
        links = {test: imported_source_paths(repo, test) for test in tests}
        for anchor in sources:
            key = f"{anchor}@{commit.sha}"
            symbols = list(commit.symbols_by_file.get(anchor, ()))
            event = Event(anchor, commit.sha, key, [commit.sha], {commit.sha: commit.timestamp}, [commit.subject], [anchor], changed_symbols=symbols)
            if commit.is_revert: event.ambiguous_evidence.append("revert_requires_explicit_event_manifest")
            if any(new == anchor for _, new in commit.renames): event.ambiguous_evidence.append("rename_requires_explicit_event_manifest")
            if len(sources) > 1: event.ambiguous_evidence.append("multi_file_commit_requires_review")
            if len(symbols) > 12: event.ambiguous_evidence.append("multi_symbol_change_requires_review")
            events[key] = event
        for test in tests:
            test_symbols = set(commit.symbols_by_file.get(test, ()))
            imported = set(links.get(test, ()))
            matches: list[Event] = []
            for event in events.values():
                if event.anchor not in imported and not (len(sources) == 1 and event.anchor in sources): continue
                source_symbols = set(event.changed_symbols)
                if not source_symbols or not test_symbols or not (source_symbols & test_symbols): continue
                if event.trigger_commit != commit.sha:
                    ancestry = event.trigger_commit in commit.ancestors
                    if not ancestry and (repo / ".git").exists():
                        try: run_git(repo, ["merge-base", "--is-ancestor", event.trigger_commit, commit.sha]); ancestry = True
                        except subprocess.CalledProcessError: ancestry = False
                    if not ancestry: continue
                matches.append(event)
            claim = (commit.sha, test)
            if len(matches) != 1 or claim in claimed_tests:
                reason = "ambiguous_test_link" if matches else "unlinked_test_evidence"
                for event in matches:
                    if reason not in event.ambiguous_evidence: event.ambiguous_evidence.append(reason)
                continue
            event = matches[0]; claimed_tests.add(claim)
            if commit.sha not in event.commits:
                event.commits.append(commit.sha); event.commit_times[commit.sha] = commit.timestamp; event.subjects.append(commit.subject)
            if test not in event.files: event.files.append(test)
            event.tests.extend(name for name in test_names(repo, test, sorted(test_symbols & set(event.changed_symbols))) if name not in event.tests)
    return events

def extract_links(value: str) -> list[str]:
    return sorted(set(html.unescape(url) for url in re.findall(r"https?://[^\s\"'<>]+", value)))

def load_inventory(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list): return [dict(x) for x in data if isinstance(x, dict)], {"complete": False, "reason": "legacy_publish_only_inventory", "path": path.name}
    if not isinstance(data, dict) or not isinstance(data.get("posts"), list): raise ValueError("inventory must contain posts")
    meta = dict(data.get("metadata") or {}); meta["path"] = path.name
    return [dict(x) for x in data["posts"] if isinstance(x, dict)], meta

def enrich_pilot_events(repo: Path, events: dict[str, Event], inventory: Sequence[Mapping[str, Any]]) -> None:
    for approval_path in sorted((repo / "output/pilots/adsense-p0").glob("post-*.approval.json")):
        approval = json.loads(approval_path.read_text(encoding="utf-8")); post_id = int(approval.get("post_id", 0))
        row = next((x for x in inventory if int(x.get("post_id", 0)) == post_id), None)
        if row is None: continue
        final_path = approval_path.with_name(f"post-{post_id}.final.html")
        final = final_path.read_text(encoding="utf-8") if final_path.is_file() else ""
        evidence = [x for x in approval.get("evidence", []) if isinstance(x, dict)]
        links = [sanitize_url(str(x["url"])) for x in evidence if x.get("url")] + [sanitize_url(x) for x in extract_links(final)]
        shas = list(dict.fromkeys(re.findall(r"/blob/([0-9a-f]{40})/", " ".join(links))))
        files = list(dict.fromkeys(re.findall(r"/blob/[0-9a-f]{40}/([^?#\s]+)", " ".join(links))))
        anchors = [p for p in files if not p.startswith("tests/")] or (["publisher/wordpress.py"] if post_id == 50 else ["scripts/audit_adsense_content.py"])
        matches = [e for e in events.values() if e.anchor in anchors and any(sha in e.commits for sha in shas)]
        if not matches: continue  # artifacts never seed an event
        event = matches[-1]; event.post_id = post_id; event.slug = str(row.get("slug", "")); event.title = str(approval.get("title") or row.get("title", ""))
        event.public_urls = sorted(set([str(row.get("url", "")), *links]) - {""})
        for sha in shas:
            if sha not in event.commits:
                event.commits.append(sha)
                try: event.commit_times[sha] = run_git(repo, ["show", "-s", "--date=iso-strict", "--format=%ad", sha]).strip()
                except subprocess.CalledProcessError: event.commit_times[sha] = ""
        for value in files:
            try: safe = safe_relative_path(repo, value)
            except ValueError: continue
            if safe not in event.files: event.files.append(safe)
            if safe.startswith("tests/"): event.tests.extend(n for n in test_names(repo, safe, event.changed_symbols) if n not in event.tests)
        for item in evidence:
            if item.get("type") == "public_rest_comparison": event.structured_before_after = dict(item)
            if item.get("type") == "test" and item.get("result"):
                selectors = re.findall(r"\btests\.[A-Za-z0-9_.]+", str(item.get("command", "")))
                if selectors:
                    event.tests = list(dict.fromkeys(selectors))
                event.test_runs.append({"test": str(item.get("command", "")), "status": str(item["result"]).upper(), "exit_code": 0 if str(item["result"]).upper() == "PASS" else None, "recorded_at": datetime.fromtimestamp(approval_path.stat().st_mtime, UTC).isoformat(), "source": approval_path.relative_to(repo).as_posix(), "output_sha256": ""})

def load_evidence_manifests(repo: Path, events: dict[str, Event]) -> list[dict[str, Any]]:
    results = []
    paths = sorted((repo / "evidence/topic-events").glob("*.json")) + sorted((repo / "output/topic-miner/evidence-events").glob("*.json"))
    for path in paths:
        if path.is_symlink() or path.stat().st_size > 256_000: continue
        data = json.loads(path.read_text(encoding="utf-8")); trigger = str(data.get("trigger_commit", "")); anchor = safe_relative_path(repo, str(data.get("anchor", "")))
        event = next((e for e in events.values() if e.anchor == anchor and trigger in e.commits), None)
        results.append({"path": path.relative_to(repo).as_posix(), "matched": bool(event)})
        if event is None: continue
        for run in data.get("test_runs") or []:
            required = {"test", "status", "exit_code", "recorded_at", "output_sha256"}
            if not isinstance(run, dict) or not required <= set(run): raise ValueError(f"incomplete test run evidence: {path}")
            datetime.fromisoformat(str(run["recorded_at"]).replace("Z", "+00:00"))
            if not re.fullmatch(r"[0-9a-f]{64}", str(run["output_sha256"])): raise ValueError(f"invalid output hash: {path}")
            event.test_runs.append({k: redact_text(str(run[k])) if k == "test" else run[k] for k in required})
        event.structured_before_after = data.get("before_after") or event.structured_before_after
        event.target_reader = redact_text(str(data.get("target_reader", ""))); event.reader_action = redact_text(str(data.get("reader_action", ""))); event.unique_takeaway = redact_text(str(data.get("unique_takeaway", "")))
        event.recommended_format = str(data.get("recommended_format", ""))
        event.contract_fields = dict(data.get("contract_fields") or {})
        event.public_access_verified = data.get("public_access_verified") is True
        if data.get("title_seed"): event.title = redact_text(str(data["title_seed"]))
        if data.get("real_trigger") or data.get("problem"):
            event.subjects = [redact_text(str(data.get("real_trigger", ""))), redact_text(str(data.get("problem", "")))]
        resolved = {str(value) for value in data.get("resolved_ambiguities") or []}
        event.ambiguous_evidence = [value for value in event.ambiguous_evidence if value not in resolved]
        for value in data.get("evidence_files") or []:
            safe = safe_relative_path(repo, str(value))
            if safe not in event.files: event.files.append(safe)
        for value in data.get("tests") or []:
            clean = redact_text(str(value))
            if clean not in event.tests: event.tests.append(clean)
        for value in data.get("logs") or []:
            safe = safe_relative_path(repo, str(value))
            if safe not in event.logs: event.logs.append(safe)
        for url in data.get("public_urls") or []:
            clean = sanitize_url(str(url))
            if clean.startswith("https://") and clean not in event.public_urls: event.public_urls.append(clean)
        sha = str(data.get("fix_commit", ""))
        if sha and sha not in event.commits: event.commits.append(sha); event.commit_times[sha] = str(data.get("fix_at", ""))
    return results

def collect_artifact_metadata(repo: Path, events: Mapping[str, Event]) -> list[dict[str, Any]]:
    paths = {p for pattern in ARTIFACT_PATTERNS for p in repo.glob(pattern)}
    output = []
    for path in sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)[:500]:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000: continue
        relative = safe_relative_path(repo, path.relative_to(repo).as_posix()); raw = path.read_bytes(); text = raw.decode(errors="replace"); matched = []
        for key, event in events.items():
            if any(sha in text for sha in event.commits) or (event.post_id and re.search(rf'"post_id"\s*:\s*{event.post_id}\b', text)):
                matched.append(key)
                if relative not in event.logs: event.logs.append(relative)
        output.append({"path": relative, "size": len(raw), "mtime": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(), "sha256": hashlib.sha256(raw).hexdigest(), "matched_event_keys": sorted(matched)})
    return output

def normalized_tokens(value: str) -> set[str]: return {x for x in re.findall(r"[0-9a-z가-힣]+", value.casefold()) if len(x) > 1}

def existing_overlap(event: Event, inventory: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if event.post_id:
        row = next((x for x in inventory if int(x.get("post_id", 0)) == event.post_id), None)
        if row: return {"result": "exact", "post_id": event.post_id, "url": row.get("url", ""), "status": row.get("status", ""), "reason": "same_post_id_and_search_intent"}
    tokens = normalized_tokens(" ".join([event.title, event.slug, *event.subjects, event.unique_takeaway, event.reader_action])); best = (0.0, None)
    for row in inventory:
        other = normalized_tokens(f"{row.get('title','')} {row.get('slug','')} {row.get('excerpt','')}"); score = len(tokens & other) / len(tokens | other) if tokens and other else 0
        if score > best[0]: best = (score, row)
    if best[0] >= .45 and best[1]: return {"result": "probable", "post_id": best[1].get("post_id"), "url": best[1].get("url", ""), "status": best[1].get("status", ""), "similarity": round(best[0], 4), "reason": "search_intent_overlap_requires_human_review"}
    return {"result": "none"}

def repository_identity(repo: Path) -> str:
    try: remote = run_git(repo, ["remote", "get-url", "origin"]).strip()
    except subprocess.CalledProcessError: remote = ""
    return re.sub(r"(?:https?://|ssh://|git@)(?:[^/@]+@)?", "", remote).replace(":", "/").removesuffix(".git") if remote else hashlib.sha256(run_git(repo, ["rev-parse", "--show-toplevel"]).strip().encode()).hexdigest()[:16]

def candidate_id(event: Event, repo_identity: str) -> str:
    return f"{Path(event.anchor).stem.replace('_','-')}-{sha256_text({'repo':repo_identity,'anchor':event.anchor,'trigger_commit':event.trigger_commit})[:12]}"

def chronology(event: Event) -> bool:
    fails = [r for r in event.test_runs if str(r.get("status", "")).upper() == "FAIL" and int(r.get("exit_code", 0)) != 0]
    passes = [r for r in event.test_runs if str(r.get("status", "")).upper() == "PASS" and int(r.get("exit_code", 1)) == 0]
    times = [v for v in event.commit_times.values() if v]
    return bool(fails and passes and len(event.commits) >= 2 and times and min(str(r["recorded_at"]) for r in fails) < max(times) < max(str(r["recorded_at"]) for r in passes))

def evidence_contract(event: Event) -> tuple[dict[str, Any], list[str]]:
    kind = event.recommended_format
    fields = event.contract_fields
    passes = [r for r in event.test_runs if str(r.get("status", "")).upper() == "PASS" and int(r.get("exit_code", 1)) == 0 and re.fullmatch(r"[0-9a-f]{64}", str(r.get("output_sha256", "")))]
    failures = [r for r in event.test_runs if str(r.get("status", "")).upper() == "FAIL" and int(r.get("exit_code", 0)) != 0 and re.fullmatch(r"[0-9a-f]{64}", str(r.get("output_sha256", "")))]
    requirements: dict[str, bool] = {
        "known_format": kind in EVIDENCE_FORMATS,
        "public_access_verified": event.public_access_verified and bool(event.public_urls),
    }
    if kind == "debugging_log":
        requirements.update({"failed_run": bool(failures), "root_cause": bool(fields.get("root_cause")), "fix_diff": len(event.commits) >= 2, "same_condition_pass": bool(passes), "prevention": bool(fields.get("prevention")), "chronology": chronology(event)})
    elif kind == "feature_build":
        requirements.update({"requirement": bool(fields.get("requirement")), "implementation_diff": bool(event.commits and event.files), "core_test": bool(passes), "completion_result": bool(fields.get("completion_result")), "unsupported_scope": bool(fields.get("unsupported_scope"))})
    elif kind == "migration":
        requirements.update({"before_version": bool(fields.get("before_version")), "after_version": bool(fields.get("after_version")), "behavior_difference": bool(event.structured_before_after), "compatibility": bool(fields.get("compatibility")), "regression_test": bool(passes), "rollback_condition": bool(fields.get("rollback_condition"))})
    elif kind == "benchmark_experiment":
        requirements.update({key: bool(fields.get(key)) for key in ("environment", "input", "baseline", "comparison", "measurements", "limitations")})
    elif kind == "architecture_decision":
        requirements.update({"decision_problem": bool(fields.get("decision_problem")), "alternatives": isinstance(fields.get("alternatives"), list) and len(fields["alternatives"]) >= 2, "criteria": bool(fields.get("criteria")), "adopted": bool(fields.get("adopted")), "rejected": bool(fields.get("rejected")), "decision_record": bool(fields.get("decision_record")), "tradeoffs": bool(fields.get("tradeoffs"))})
    elif kind == "operations_incident":
        requirements.update({key: bool(fields.get(key)) for key in ("observation", "impact", "response", "recovery", "post_verification", "prevention")})
    return {"type": kind or None, "requirements": requirements}, [name for name, ok in requirements.items() if not ok]

def evaluate_event(event: Event, inventory: Sequence[Mapping[str, Any]], repo_identity: str, inventory_complete: bool = True) -> dict[str, Any]:
    overlap = existing_overlap(event, inventory); commits = sorted(set(event.commits), key=lambda s: (event.commit_times.get(s, "9999"), s)); contract, contract_missing = evidence_contract(event)
    fail = any(str(r.get("status", "")).upper() == "FAIL" and int(r.get("exit_code", 0)) != 0 for r in event.test_runs); passed = any(str(r.get("status", "")).upper() == "PASS" and int(r.get("exit_code", 1)) == 0 for r in event.test_runs)
    hashes = bool(event.test_runs) and all(re.fullmatch(r"[0-9a-f]{64}", str(r.get("output_sha256", ""))) for r in event.test_runs)
    gates = {"real_project_trigger": bool(event.trigger_commit in event.commits), "traceable_evidence_contract": not contract_missing and not event.ambiguous_evidence, "transferable_problem": bool(event.target_reader), "no_existing_search_intent_overlap": overlap["result"] == "none", "unique_beyond_docs": bool(event.unique_takeaway), "reader_action": bool(event.reader_action), "public_and_secret_safe_evidence": contract["requirements"].get("public_access_verified", False), "current_public_and_draft_overlap_checked": inventory_complete}
    missing = [k for k, v in gates.items() if not v] + [f"evidence_contract.{name}" for name in contract_missing]
    publishability, reason = (("REJECT", "existing_post_overlap") if overlap["result"] in {"exact", "probable"} else (("NEEDS_EVIDENCE", None) if missing else ("READY", None)))
    subjects = [redact_text(x) for x in event.subjects]; recent = subjects[-1] if subjects else f"{event.anchor} 변경"
    row = {"candidate_id": candidate_id(event, repo_identity), "title_seed": redact_text(event.title or f"{recent}: {Path(event.anchor).name} 변경에서 확인한 것"), "real_trigger": redact_text(" → ".join(subjects[-4:]) or event.anchor), "target_reader": event.target_reader or "같은 자동화 코드를 유지보수하는 개발자", "problem": redact_text(recent), "why_it_matters": event.reader_action or "검증된 결과가 더 있어야 독자 행동을 확정할 수 있다.", "evidence_contract": contract, "evidence": {"commits": commits, "files": sorted(set(event.files)), "tests": sorted(set(event.tests)), "logs": sorted(set(event.logs)), "public_urls": sorted(set(event.public_urls))}, "before_after": event.structured_before_after or {}, "unique_takeaway": event.unique_takeaway or "구조화된 고유 결론 근거가 더 필요하다.", "existing_post_overlap": overlap, "recommended_format": event.recommended_format or None, "publishability": publishability, "missing_evidence": list(dict.fromkeys(missing)), "rejection_reason": reason, "ready_gates": gates, "source_anchor": event.anchor, "event_key": event.event_key, "test_runs": event.test_runs, "ambiguous_evidence": event.ambiguous_evidence}
    if contains_secret(canonical_json(row)): raise ValueError(f"secret-like material remained in {row['candidate_id']}")
    return row

def choose_candidates(records: Sequence[Mapping[str, Any]], limit: int = MAX_CANDIDATES) -> list[dict[str, Any]]:
    if not 0 <= limit <= MAX_CANDIDATES: raise ValueError("invalid limit")
    rows = sorted([dict(x) for x in records if x.get("publishability") == "READY"], key=lambda x: (-sum(len(x.get("evidence",{}).get(k,[])) for k in ("commits","files","tests","logs")), str(x.get("candidate_id"))))
    selected: list[dict[str, Any]] = []; claimed: set[tuple[str, str]] = set()
    for row in rows:
        evidence = row.get("evidence", {})
        keys = {(kind, str(value)) for kind in ("commits", "tests", "logs") for value in evidence.get(kind, [])}
        if keys & claimed: continue
        selected.append(row); claimed |= keys
        if len(selected) == limit: break
    return selected

def atomic_write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data: return
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream: stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def atomic_replace(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream: stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def existing_run_is_current(root: Path, day: date, head: str, checkpoint: Mapping[str, Any] | None, *, inventory_sha256: str = "", miner_sha256: str = "") -> bool:
    if not checkpoint or checkpoint.get("last_collected_commit") != head: return False
    if inventory_sha256 and checkpoint.get("inventory_sha256") != inventory_sha256: return False
    if miner_sha256 and checkpoint.get("miner_sha256") != miner_sha256: return False
    hashes = checkpoint.get("output_hashes") or {}; directory = root / day.isoformat()
    for name in ("candidates.json", "candidates.md", "processing.json"):
        if not (directory/name).is_file() or not hashes.get(name): return False
        if hashlib.sha256((directory/name).read_bytes()).hexdigest() != hashes[name]: raise RuntimeError(f"existing topic miner output hash mismatch: {name}")
    return True

def render_markdown(payload: Mapping[str, Any]) -> str:
    lines = [f"# Evidence-first Topic Miner — {payload['date']}", "", f"- status: `{payload['status']}`", f"- source head: `{payload['source_head']}`", f"- candidates: {len(payload['candidates'])}/{MAX_CANDIDATES}", ""]
    if not payload["candidates"]: lines += ["`no_publishable_topic`", ""]
    for row in payload["candidates"]:
        lines += [f"## {row['title_seed']}", "", "```yaml"]
        for key in ("candidate_id","title_seed","real_trigger","target_reader","problem","why_it_matters"): lines.append(f"{key}: {json.dumps(row[key],ensure_ascii=False)}")
        lines.append(f"evidence_contract: {json.dumps(row['evidence_contract'],ensure_ascii=False)}")
        lines.append("evidence:")
        for key in ("commits","files","tests","logs","public_urls"): lines.append(f"  {key}: {json.dumps(row['evidence'][key],ensure_ascii=False)}")
        for key in ("before_after","unique_takeaway","existing_post_overlap","recommended_format","publishability","missing_evidence","rejection_reason"): lines.append(f"{key}: {json.dumps(row[key],ensure_ascii=False)}")
        lines += ["```", ""]
    return "\n".join(lines).rstrip()+"\n"

def persist_miner_run(directory: Path, checkpoint_path: Path, payload: Mapping[str, Any], processing: Mapping[str, Any], checkpoint: dict[str, Any]) -> None:
    blobs={"candidates.json":(json.dumps(payload,ensure_ascii=False,indent=2)+"\n").encode(),"candidates.md":render_markdown(payload).encode(),"processing.json":(json.dumps(processing,ensure_ascii=False,indent=2)+"\n").encode()}
    for name,data in blobs.items(): atomic_write_new(directory/name,data)
    checkpoint["output_hashes"]={name:hashlib.sha256(data).hexdigest() for name,data in blobs.items()}
    checkpoint["output_directory"]=directory.as_posix()
    atomic_replace(checkpoint_path,(json.dumps(checkpoint,ensure_ascii=False,indent=2)+"\n").encode())

def build_payload(*, repo: Path, inventory_path: Path, run_date: date, max_commits: int = 60, checkpoint: Mapping[str, Any] | None = None):
    inventory, meta = load_inventory(inventory_path); since = str((checkpoint or {}).get("last_collected_commit", ""))
    if since:
        try: run_git(repo, ["merge-base", "--is-ancestor", since, "HEAD"])
        except subprocess.CalledProcessError as exc: raise RuntimeError("checkpoint commit is not an ancestor of HEAD") from exc
    commits = collect_commits(repo, max_commits, since); head = run_git(repo, ["rev-parse", "HEAD"]).strip(); events = group_git_events(repo, commits)
    enrich_pilot_events(repo, events, inventory); manifests = load_evidence_manifests(repo, events); artifacts = collect_artifact_metadata(repo, events)
    previous = set((checkpoint or {}).get("processed_event_ids", [])); records = [evaluate_event(e, inventory, repository_identity(repo), bool(meta.get("complete"))) for _, e in sorted(events.items())]; fresh = [r for r in records if r["candidate_id"] not in previous]; selected = choose_candidates(fresh)
    payload = {"contract_version":CONTRACT_VERSION,"date":run_date.isoformat(),"source_head":head,"checkpoint_from":since or None,"status":"ready" if selected else "no_publishable_topic","candidate_limit":MAX_CANDIDATES,"candidates":selected,"ready_count":len(selected),"inventory":meta}
    processing = {"contract_version":CONTRACT_VERSION,"date":run_date.isoformat(),"source_head":head,"inventory":meta,"evaluated_count":len(records),"new_event_count":len(fresh),"rejected_count":sum(r["publishability"]=="REJECT" for r in records),"evidence_manifests":manifests,"artifact_inventory":artifacts,"processed":records}
    next_checkpoint = {"contract_version":CONTRACT_VERSION,"last_collected_commit":head,"last_successful_date":run_date.isoformat(),"processed_event_ids":sorted(previous|{r["candidate_id"] for r in records}),"inventory_sha256":hashlib.sha256(inventory_path.read_bytes()).hexdigest(),"miner_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for value in (payload, processing, next_checkpoint):
        if contains_secret(canonical_json(value)): raise ValueError("secret-like material remained in output")
    return payload, processing, next_checkpoint

def main() -> int:
    root = Path(__file__).resolve().parents[1]; parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,default=root); parser.add_argument("--date",type=date.fromisoformat,default=datetime.now(UTC).date()); parser.add_argument("--run-id",default=""); parser.add_argument("--max-commits",type=int,default=60); parser.add_argument("--inventory",type=Path,default=root/"output/topic-miner/inventory-latest.json"); parser.add_argument("--output-root",type=Path,default=root/"output/topic-miner"); parser.add_argument("--dry-run",action="store_true"); args=parser.parse_args()
    if args.run_id and not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{10}",args.run_id): parser.error("invalid run-id")
    checkpoint_path=args.output_root/"checkpoint.json"; checkpoint=json.loads(checkpoint_path.read_text()) if checkpoint_path.is_file() else None; head=run_git(args.repo.resolve(),["rev-parse","HEAD"]).strip(); inventory_sha=hashlib.sha256(args.inventory.read_bytes()).hexdigest(); miner_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(); directory=args.output_root/args.date.isoformat()/(args.run_id or "")
    if existing_run_is_current(directory.parent,args.date if not args.run_id else date.fromisoformat(directory.parent.name),head,checkpoint,inventory_sha256=inventory_sha,miner_sha256=miner_sha) and not args.run_id: print(f"status=NOOP source_head={head} output={directory}"); return 0
    payload,processing,next_checkpoint=build_payload(repo=args.repo.resolve(),inventory_path=args.inventory.resolve(),run_date=args.date,max_commits=args.max_commits,checkpoint=checkpoint)
    if args.dry_run: print(json.dumps(payload,ensure_ascii=False,indent=2)); return 0
    persist_miner_run(directory,checkpoint_path,payload,processing,next_checkpoint); print(f"status={payload['status']} candidates={len(payload['candidates'])} ready={payload['ready_count']} output={directory}"); return 0

if __name__ == "__main__": raise SystemExit(main())
