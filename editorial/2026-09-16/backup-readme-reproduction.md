# Backup media README clean-checkout reproduction

status: PASS

Only `evidence/lab-fixtures/backup-media/README.md` was changed. No feature code,
event manifest, server, WordPress resource, commit or push was changed by this task.

## Reader preparation correction

- Separates repository/Python downloads, which may need network, from offline fixture execution.
- Checks the selected Python is installed and at least 3.11 before creating an environment.
- Uses a new relative `./backup-demo.XXXXXX` directory per run, with a task-local `venv --without-pip`; no existing project `.venv` is used or overwritten.
- Quotes generated paths and checks snapshot exit 0, intentional missing audit exit 1, matching audit exit 0 with explicit branches.
- Uses a subshell so `exit` does not close the user's interactive shell.
- Preserves JSON evidence and the task environment; does not run cleanup or use literal `<check-dir>` placeholders.

## Actual fresh-checkout verification

A new HTTPS shallow clone was created from the public repository. Its revision was
`11df99bb9e41dd870acd8aea0c3ca473368d57a8`. No prior `.venv`, credentials or packages
were supplied to that checkout. The proposed README's fenced executable block was
run verbatim from the fresh clone root, selecting an already installed Python
3.12.9 using the documented `BACKUP_PYTHON` override. The new task environment did
not contain pip (`importlib.util.find_spec('pip') is None`).

```text
Python 3.12.9
{"operation": "snapshot", "passed": true, "files": 1, "whole_site_restore_verified": false}
{"operation": "audit", "passed": false, "files": 1, "whole_site_restore_verified": false}
{"operation": "audit", "passed": true, "files": 1, "whole_site_restore_verified": false}
snapshot_exit=0 missing_exit=1 matching_exit=0
Evidence directory: ./backup-demo.dY3oXL
```

Overall fenced-block exit was 0. Independently read before/after JSON: before has
`missing_file`, after has an empty failures array; both preserve
`whole_site_restore_verified=false`. Repeated execution created a different
directory, and both runs' JSON files remained intact.

Negative check selected the installed Python 3.8.2. It printed the requirement
message and exited 1 before the `mktemp`/environment step, as intended.

The first test harness incorrectly extracted prose after the closing Markdown
fence. The fixture itself returned the expected 0/1/0, then Bash attempted to run
the prose and exited 255. The extractor was corrected to stop at the fence; the
README block itself did not require a fix for this harness error. Both evidence
directories were retained. This error is not a WordPress or fixture failure.

This verifies reader setup and the synthetic one-file comparison only. It does
not independently rerun the private database import, 373 operational files, or
whole-site restoration. No benchmark or AdSense approval claim is made.
