# Korean humanization shadow experiment

This is a bounded, two-draft shadow experiment inspired by the public
[`im-not-ai`](https://github.com/epoko77-ai/im-not-ai) project (MIT license).
It is a style pass, not an AI-detector bypass and not a license to invent
experience.

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
source: im-not-ai (shadow experiment)
changed_sections: <comma-separated headings or none>
protected_content: frontmatter, facts, code, logs, links, citations
meaning_or_evidence_changed: no
notes: <short comparison note>
```

The Reviewer remains the only approval gate. The Assembler and Publisher use
the original `draft.md`; this artifact is for comparison and evidence only.
