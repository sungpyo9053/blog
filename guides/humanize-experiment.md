# Korean technical copy-editing — im-not-ai integration

Physical AI articles use an explicitly configured conservative copy-edit pass.
Legacy articles retain their bounded/expiring experiment settings. Read the pinned
`third_party/im-not-ai/quick-rules.md` fully before editing; provenance and MIT license
are stored alongside it. This imports the Codex-style single-pass rules, not the
Claude-only multi-agent runtime of [`im-not-ai`](https://github.com/epoko77-ai/im-not-ai).
It is a style pass, not an AI-detector bypass and not a license to invent
experience.

## Technical adaptation (takes precedence over generic style rules)

- Preserve teaching vocabulary (관측, 상태, 행동, 정책, 제어, 피드백), variable names,
  mathematical relationships, units, code, tables, claims, source attribution and limits.
- Repetition needed to teach a term is not a defect. Keep useful lists and explanatory
  parallels. Do not mechanically force sentence-length variation or delete connectors.
- Never change a possibility/requirement into a fact, remove a negation, reverse a
  comparison or substitute a technical term with a looser synonym.
- Only edit an identified awkward span. Record the upstream rule ID, exact before/after
  wording and why the meaning is unchanged. No finding means UNCHANGED is correct.
- Do not use upstream G-3 (held rule) to remove genuine uncertainty or balanced evidence.
- Do not invent first-person experience, a personality, experiments or anecdotes.
- The deterministic checker is only a guard. Reviewer must compare original and selected
  wording for meaning, polarity, causality, certainty and technical accuracy.
- Apply once before assembly/final review; do not rerun in the Reviewer repair loop.
  A failed preservation check selects the original and records why; it is not a publish
  approval. The final content still needs independent quality and Publisher checks.

## Contract

- Read `draft.md`; never overwrite it.
- Write only `humanized-draft.md` and `humanize-summary.md` in the topic directory.
- Preserve frontmatter, title, facts, numbers, dates, versions, proper names,
  quotations, citations, URLs, HTML, tables, fenced code, commands, logs, and
  identifiers byte-for-byte where possible.
- Do not add personal experience, test results, sources, claims, or examples.
- Make only local style edits: remove translationese, vary mechanical
  connectors, reduce repetitive openings, and improve sentence rhythm when the
  meaning is unchanged.
- If a sentence is ambiguous or a change would exceed a light copy-edit, leave
  it unchanged.
- The output must remain Korean technical writing suitable for a WordPress
  article. Do not mention this experiment in the article body.

## Summary file

`humanize-summary.md` must record:

```text
status: COMPLETED | UNCHANGED | BLOCKED
source: im-not-ai pinned rules, HuntLab conservative adapter
changed_sections: <comma-separated headings or none>
protected_content: frontmatter, facts, code, logs, links, citations
meaning_or_evidence_changed: no
notes: <short comparison note>
```

Append a findings table with rule_id, before, after and preservation_reason. Record
UNCHANGED without manufacturing edits to achieve an upstream change-rate grade.

In shadow mode the original `draft.md` remains selected. In ON mode a rewrite
may replace the selected draft only after the deterministic preservation check
passes: frontmatter, fenced/inline code, URLs and numbers must be unchanged,
and the character change ratio must not exceed 30%. A failed check retains
the original and records `style-preservation.json`. The Reviewer then reviews
the selected draft. This check does not prove semantic equivalence or human authorship.

For natural Korean, keep the concrete problem near the beginning. Remove
translationese, repeated stock transitions and redundant emphasis. Preserve
technical terms, uncertainty, instructions and limits. Do not invent an
experience, conversational filler or a new metaphor to make writing sound human.
