"""Deterministic pre-publication checks, not an AdSense approval predictor."""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path


def unresolved_shell_path_placeholder(text: str) -> bool:
    """Narrow lint, not a shell parser or an execution/safety certificate.

    Inspect only explicitly shell-labelled blocks. Ignore quoted literals,
    comments and heredoc data; transcripts belong in text/plain blocks.
    """
    blocks = []
    for match in re.finditer(r"(?m)^ {0,3}(`{3,}|~{3,})(bash|sh|shell)(?=[ \t\n])[^\n]*\n(.*?)^ {0,3}\1\s*$", text, re.S | re.I):
        blocks.append(match[3])

    class ShellHTML(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.depth = 0
            self.shell = False
            self.parts = []

        def handle_starttag(self, tag, attrs):
            if tag == "pre":
                self.depth += 1
            if self.depth and tag in ("pre", "code"):
                values = dict(attrs)
                classes = (values.get("class") or "").split()
                self.shell |= any(x.lower() in {"language-bash", "language-sh", "language-shell", "lang-bash", "lang-sh", "lang-shell"} for x in classes)
                self.shell |= (values.get("data-language") or "").lower() in {"bash", "sh", "shell"}

        def handle_data(self, data):
            if self.depth:
                self.parts.append(data)

        def handle_endtag(self, tag):
            if tag == "pre" and self.depth:
                self.depth -= 1
                if not self.depth:
                    if self.shell:
                        blocks.append("".join(self.parts))
                    self.shell, self.parts = False, []

    parser = ShellHTML()
    parser.feed(text)
    placeholder = re.compile(r"(?<![\w-])<(?:[a-z][a-z0-9]*[-_])*(?:dir|directory|path)>", re.I)
    # Preserve character positions/newlines while masking shell literal data.
    literals = re.compile(r"\\[\s\S]|'[^']*'|\"(?:\\[\s\S]|[^\"\\])*\"|(?<!\S)#[^\n]*")
    for block in blocks:
        # Common single-delimiter heredocs: data, including XML, is not code.
        block = re.sub(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n.*?^\t*\2\s*$", "", block, flags=re.M | re.S)
        block = literals.sub(lambda m: "\n" * m[0].count("\n") + " ", block)
        if placeholder.search(block):
            return True
    return False


def prose(text: str) -> str:
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```|<pre\b.*?</pre>", " ", text, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


DEFAULT_PROTECTED_TERMS = (
    "피지컬 AI", "관측", "상태", "행동", "정책", "피드백", "제어기", "센서",
    "액추에이터", "강화학습", "모방학습", "시뮬레이션", "실물", "하드웨어",
    "observation", "state", "action", "policy", "feedback", "controller",
    "sensor", "actuator", "ROS 2", "Gymnasium", "MuJoCo", "NVIDIA", "WordPress",
)


def _markdown_tables(text: str) -> list[str]:
    """Freeze complete pipe tables, not incidental pipes in ordinary prose."""
    lines = text.splitlines(keepends=True)
    tables, index = [], 0
    while index + 1 < len(lines):
        delimiter = lines[index + 1].strip().strip("|").strip()
        cells = [cell.strip() for cell in delimiter.split("|")]
        if ("|" in lines[index] and "|" in lines[index + 1]
                and len(cells) >= 2
                and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)):
            end = index + 2
            while end < len(lines) and lines[end].strip() and "|" in lines[end]:
                end += 1
            tables.append("".join(lines[index:end]))
            index = end
        else:
            index += 1
    return tables


def _negative_claims(text: str) -> list[str]:
    """Conservatively freeze clauses with uncertainty/negation markers.

    This is intentionally not a linguistic entailment detector. A harmless
    rewrite of a protected clause is held for review rather than silently
    approving a reversal. Ordinary unmarked semantic changes remain possible.
    """
    negative = re.compile(
        r"아니|않|못하|못했|못한|못한다|없[다는는음어었이]|미검증|미확인|미실행|"
        r"보장하지|검증하지|실행하지|(?:^|\s)안\s|"
        r"\b(?:not|never|no|without|unverified|untested|unknown|cannot)\b|n['’]t\b",
        re.I,
    )
    return [match[0] for match in re.finditer(r"[^.!?\n]+(?:[.!?]|$)", text)
            if negative.search(match[0])]


def style_preservation(before: str, after: str, *, protected_terms=()) -> dict:
    """Conservative copy-edit retention, NOT a semantic-equivalence proof.

    Protect exact structured spans and negated/qualified claims, plus known
    technical terms and caller-supplied case-sensitive literal terms. Reviewers
    must still check evidence attribution, reasoning and changed positive prose.
    No protected content is echoed in the report (it may include private data).
    """
    patterns = {
        "frontmatter": r"\A---\s*\n.*?\n---",
        "code": r"(?m)^ {0,3}(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^ {0,3}(?P=fence)[ \t]*(?:\n|$)|<pre\b.*?</pre>|<code\b.*?</code>|(?P<inline>`+)[^`\n]+(?P=inline)",
        "urls": r"https?://[^\s<>\)\]\"]+",
        "numbers": r"\d+(?:[.,:/-]\d+)*(?:%|ms|GB|MB)?",
        "html_tables": r"<table\b.*?</table>",
        "math": r"\$\$.*?\$\$|(?<![\\$])\$(?!\$)[^$\n]+(?<!\\)\$|\\\(.*?\\\)|\\\[.*?\\\]|<math\b.*?</math>",
        "equation_lines": r"(?m)^[ \t]*[A-Za-zα-ωΑ-Ω][A-Za-z0-9α-ωΑ-Ω_{}()\[\] \t+*/.,-]*(?:=|≤|≥|≠|≈)[^\n]*$",
        "quotes": r"(?m)^(?: {0,3}>[^\n]*(?:\n|$))+|<blockquote\b.*?</blockquote>|<q\b.*?</q>|“[^”]*”|‘[^’]*’|「[^」]*」|『[^』]*』|(?<!\w)\"[^\"\n]+\"|(?<!\w)'[^'\n]+'(?!\w)",
        "identifiers": r"\b(?:[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+|[a-z]+(?:[A-Z][a-z0-9]+)+|[A-Z][A-Z0-9]{1,})\b",
    }
    # Preserve order as well as counts: swapping two numbers/URLs/claims must
    # not pass merely because the same multiset remains somewhere in the text.
    failures = []
    for key, pattern in patterns.items():
        flags = re.S if key == "identifiers" else re.S | re.I
        if ([m[0] for m in re.finditer(pattern, before, flags)]
                != [m[0] for m in re.finditer(pattern, after, flags)]):
            failures.append(key)
    if _markdown_tables(before) != _markdown_tables(after):
        failures.append("markdown_tables")
    if _negative_claims(before) != _negative_claims(after):
        failures.append("qualified_claims")
    if (not isinstance(protected_terms, (tuple, list))
            or any(not isinstance(term, str) or not term.strip() for term in protected_terms)):
        failures.append("invalid_protected_terms")
    else:
        terms = tuple(dict.fromkeys((*DEFAULT_PROTECTED_TERMS, *protected_terms)))
        if any(before.count(term) != after.count(term) for term in terms):
            failures.append("technical_terms")
    change = 1 - SequenceMatcher(None, before, after, autojunk=False).ratio()
    if change > .3:
        failures.append("excessive_rewrite")
    if not after.strip():
        failures.append("empty")
    return {"passed": not failures, "failures": failures, "change_ratio": round(change, 4),
            "semantic_equivalence_verified": False, "independent_review_required": True}


def inspect_article(text: str, inventory: dict, *, now: datetime | None = None, existing_post_id: int | None = None) -> dict:
    """Surface hard failures; semantic quality still requires the Reviewer."""
    failures, duplicates = [], []
    if not isinstance(inventory, dict):
        inventory = {}
    meta = inventory.get("metadata", {})
    if not isinstance(meta, dict):
        meta = {}
    if not meta.get("complete") or not meta.get("full_content"):
        failures.append("incomplete_full_content_inventory")
    try:
        age = ((now or datetime.now(UTC)) - datetime.fromisoformat(meta["collected_at"])).total_seconds()
        if age < -300 or age > 86400:
            failures.append("stale_inventory")
    except (KeyError, TypeError, ValueError):
        failures.append("invalid_inventory_date")
    body = prose(text)
    posts = inventory.get("posts")
    counts = meta.get("statuses")
    valid_rows = isinstance(posts, list) and all(
        isinstance(post, dict) and type(post.get("post_id")) is int
        and post["post_id"] > 0 and isinstance(post.get("content"), str)
        and post.get("status") in {"publish", "draft", "future"} for post in posts
    )
    if not valid_rows:
        failures.append("invalid_inventory_posts")
        posts = []
    elif len({post["post_id"] for post in posts}) != len(posts):
        failures.append("duplicate_inventory_ids")
    actual = {status: sum(post["status"] == status for post in posts) for status in ("publish", "draft")}
    # Legacy snapshots may omit future only when no scheduled rows are present.
    # Scheduling callers separately require an explicit, fresh future inventory.
    if any(post['status'] == 'future' for post in posts) or isinstance(counts, dict) and 'future' in counts:
        actual['future'] = sum(post['status'] == 'future' for post in posts)
    if not isinstance(counts, dict) or any(type(counts.get(status)) is not int or counts[status] != count for status, count in actual.items()):
        failures.append("inventory_status_count_mismatch")
    if not body:
        failures.append("empty_body")
    if re.search(r"물론입니다[!.]|도움이 되셨|요청하신.*정리해|제 지식.*기준", body):
        failures.append("chatbot_framing")
    if unresolved_shell_path_placeholder(text):
        failures.append("unresolved_shell_path_placeholder")
    # Any substantial verbatim passage in another post needs an editorial
    # decision before publication. Exclude code and metadata from comparison.
    # Fixed-width exact strings avoid SequenceMatcher's quadratic behavior on
    # long repetitive Korean prose. Every offset participates; Python sets
    # resolve hash collisions with full string equality, so no matches are lost
    # or invented. Report the confirmed lower bound, not a longest-match claim.
    duplicate_threshold = 180
    windows = {body[offset:offset + duplicate_threshold]
               for offset in range(len(body) - duplicate_threshold + 1)}
    for post in posts:
        if existing_post_id and post.get("post_id") == existing_post_id:
            continue
        other = prose(str(post.get("content", "")))
        if not windows or len(other) < duplicate_threshold:
            continue
        if any(other[offset:offset + duplicate_threshold] in windows
               for offset in range(len(other) - duplicate_threshold + 1)):
            duplicates.append({"post_id": post.get("post_id"),
                               "characters": duplicate_threshold,
                               "characters_is_lower_bound": True})
    if duplicates:
        failures.append("substantial_existing_passage")
    return {"passed": not failures, "failures": failures, "duplicates": duplicates,
            "checked_posts": len(posts),
            "content_sha256": hashlib.sha256(text.encode()).hexdigest()}


def enforce_prepublication(publish_path: Path, inventory_path: Path, *, existing_post_id: int | None = None) -> dict:
    text = publish_path.read_text(encoding="utf-8")
    report = inspect_article(text, json.loads(inventory_path.read_text(encoding="utf-8")), existing_post_id=existing_post_id)
    # Match this actual run directory only, including HTML-encoded captures.
    # Never put the private path itself in the public-facing error/report.
    if str(publish_path.resolve().parent) in html.unescape(text):
        report["failures"].append("private_runtime_path")
        report["passed"] = False
    (publish_path.parent / "editorial-gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not report["passed"]:
        raise ValueError("editorial gate: " + ", ".join(report["failures"]))
    return report
