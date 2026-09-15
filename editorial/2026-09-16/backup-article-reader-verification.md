# Backup article — independent reader execution

status: PASS_SCOPED_READER_CHECK

This is a read-only audit of the repair draft from run
`20260915T183332Z-188bac8755`, topic `topic-7e12bb91fa43b14b`.
It is not final Reviewer approval, Publisher approval or publication proof.

## Exact input

The server draft was copied without remote changes into the private local snapshot
`output/quality-cycle-20260916/live-e2e-second/draft.repair.md`.

- Draft SHA-256: `b0400e40fc29d11284828dd46e5a4f90fe13c5f6c08df1ab5428291e5007093c`
- First Bash block (clone/cd/checkout) SHA-256: `cfec8190d89043400006cd807c1f999ca19e3032cdd4f4f498d77e0971fc2493`
- Second Bash block (complete runnable example) SHA-256: `e8a4b647ffdce225c6fb9a58deacc6fdaad5c7293834feb4dd2b371e204e02d2`

The second block is byte-for-byte equal to the second Bash fence in the README
pinned at `635186a4d3f6c9546ec0edd3f9d0e10ae670d26e`. This checks the **repaired article
body**, not just an earlier README baseline or a link to a passing example.

## Actual clean-checkout execution

The first Bash block was executed verbatim inside a new empty temporary directory.
HTTPS clone, `cd blog`, and the pinned checkout all completed with exit 0.
`git rev-parse HEAD` returned `635186a4d3f6c9546ec0edd3f9d0e10ae670d26e`.

The complete second Bash block was then executed verbatim in that checkout,
selecting the already installed Python 3.12.9 through its documented
`BACKUP_PYTHON` setting. It created its own relative temporary directory and venv;
no existing project `.venv` was provided. The actual output was:

```text
Python 3.12.9
{"operation": "snapshot", "passed": true, "files": 1, "whole_site_restore_verified": false}
{"operation": "audit", "passed": false, "files": 1, "whole_site_restore_verified": false}
{"operation": "audit", "passed": true, "files": 1, "whole_site_restore_verified": false}
snapshot_exit=0 missing_exit=1 matching_exit=0
Evidence directory: ./backup-demo.xMGQd8
```

The actual subprocess return code for the full block was 0. Independently reading
the JSON confirmed `before.passed=false` with `missing_file`, `after.passed=true`
with an empty failures array, and `whole_site_restore_verified=false` in both.
The generated local evidence was retained. No WordPress calls or server writes
were made. The independent run used Python 3.12.9, not the article Research's
3.12.3; its timings and directory names are not represented as this audit's output.

## Content sanity check

The prior link-only execution gap is resolved: the body now contains the full
setup/example and explicit expected exits. The literal redaction placeholders are
in a separately labeled evidence excerpt, not the executable Bash block.

No release-blocking P1 was found in the checked text. The repaired draft distinguishes:

- intentional DB-only missing-file control from a production incident;
- public synthetic one-file reproduction from the private 373-file observations;
- the 1d commit containing both comparison results from the later f4 test log;
- source manifest provenance/completeness limitations from hash comparison;
- original attachment verification from whole-site, PHP and HTTP recovery.

No private runtime/home/server path was found in the copied article text. The
separately generated images were still in progress and are **not** approved by this
audit; final image/capture and HTML checks remain necessary. The sanitized text
excerpt with abbreviated commands must not be relabeled as a copy-and-run example.

This audit did not modify Research, the draft, server files, WordPress content or
the pipeline. Final approval must be tied to the actual `publish.md` SHA-256 and
must inspect its rendered HTML and images, not this draft hash alone.
