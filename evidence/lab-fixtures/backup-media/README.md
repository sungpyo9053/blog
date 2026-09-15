# Offline media-backup fixture

The text file represents a referenced attachment. It contains no real site data.
The checker compares bytes and file paths, not image rendering or WordPress startup.

Download the repository first, then run the example from its root. Downloading
Git and Python or cloning the repository may require network access; the fixture
commands themselves require no network, credentials, pip, or external packages.

```bash
git clone https://github.com/sungpyo9053/blog.git
cd blog
```

Choose an already installed Python 3.11 or later. The name `python3` alone does
not guarantee a recent version. The block below checks it **before** creating any
environment. If it stops, install a supported Python and rerun with, for example,
`export BACKUP_PYTHON=python3.12` (or the path to that installed interpreter).
Do not point it at an unavailable command.

Paste this whole block in Bash from the repository root. The subshell makes its
failure exits safe for your interactive shell. Every run creates a new relative
`./backup-demo.XXXXXX` directory and its own environment; it never reuses or
overwrites your existing `.venv`. Keep this directory to inspect the JSON evidence.

```bash
(
set -eu
backup_python="${BACKUP_PYTHON:-python3}"
command -v "$backup_python" >/dev/null 2>&1 || {
  printf '%s\n' 'Select an installed Python 3.11+ using BACKUP_PYTHON.' >&2
  exit 1
}
"$backup_python" -c 'import sys; print("Python", sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required; select BACKUP_PYTHON and retry")'
test -f scripts/audit_backup_media.py || {
  printf '%s\n' 'Run this block from the blog repository root.' >&2
  exit 1
}
backup_demo_dir=$(mktemp -d ./backup-demo.XXXXXX)
"$backup_python" -m venv --without-pip "$backup_demo_dir/venv"
backup_runner="$backup_demo_dir/venv/bin/python"
"$backup_runner" -c 'import sys; assert sys.version_info >= (3, 11)'

if "$backup_runner" scripts/audit_backup_media.py snapshot \
  --uploads evidence/lab-fixtures/backup-media/uploads \
  --input evidence/lab-fixtures/backup-media/references.json \
  --output "$backup_demo_dir/manifest.json"; then
  backup_snapshot_exit=0
else
  backup_snapshot_exit=$?
fi
test "$backup_snapshot_exit" -eq 0 || exit 1

if "$backup_runner" scripts/audit_backup_media.py audit \
  --uploads "$backup_demo_dir/missing-uploads" \
  --input "$backup_demo_dir/manifest.json" \
  --output "$backup_demo_dir/before.json"; then
  backup_missing_exit=0
else
  backup_missing_exit=$?
fi
test "$backup_missing_exit" -eq 1 || exit 1

if "$backup_runner" scripts/audit_backup_media.py audit \
  --uploads evidence/lab-fixtures/backup-media/uploads \
  --input "$backup_demo_dir/manifest.json" \
  --output "$backup_demo_dir/after.json"; then
  backup_matching_exit=0
else
  backup_matching_exit=$?
fi
test "$backup_matching_exit" -eq 0 || exit 1
printf 'snapshot_exit=%s missing_exit=%s matching_exit=%s\n' \
  "$backup_snapshot_exit" "$backup_missing_exit" "$backup_matching_exit"
printf 'Evidence directory: %s\n' "$backup_demo_dir"
)
```

Expected final status: `snapshot_exit=0 missing_exit=1 matching_exit=0` and overall
exit 0. The middle failure is intentional: the referenced file is absent. Read
`before.json` for `missing_file` and `after.json` for `passed: true` with no failures.
Both audits retain `whole_site_restore_verified: false`. Any other stage status
stops the block. Do not silently ignore a nonzero exit or replace missing outputs
with expected values. The generated directory is not a production backup and may
contain a disposable environment; no cleanup command is run automatically.

Take the expected manifest from a consistent source snapshot, not from the restored
directory you are checking. For real media, use the attachment references from the
matching DB snapshot. Original attachment files alone do not cover generated image
sizes, plugins, themes, config, remote/offloaded media, or live HTTP behavior.
