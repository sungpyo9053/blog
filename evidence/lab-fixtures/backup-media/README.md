# Offline media-backup fixture

The text file represents a referenced attachment. It contains no real site data.
The checker compares bytes and file paths, not image rendering or WordPress startup.

Run from the repository root with Python 3.11 or later. No packages or credentials:

```sh
backup_demo_dir=$(mktemp -d)
python3 scripts/audit_backup_media.py snapshot \
  --uploads evidence/lab-fixtures/backup-media/uploads \
  --input evidence/lab-fixtures/backup-media/references.json \
  --output "$backup_demo_dir/manifest.json"
python3 scripts/audit_backup_media.py audit \
  --uploads "$backup_demo_dir/missing-uploads" \
  --input "$backup_demo_dir/manifest.json" \
  --output "$backup_demo_dir/before.json"
# Expected exit 1: the database's referenced file is not present.
python3 scripts/audit_backup_media.py audit \
  --uploads evidence/lab-fixtures/backup-media/uploads \
  --input "$backup_demo_dir/manifest.json" \
  --output "$backup_demo_dir/after.json"
# Expected exit 0. whole_site_restore_verified remains false.
```

Take the expected manifest from a consistent source snapshot, not from the restored
directory you are checking. For real media, use the attachment references from the
matching DB snapshot. Original attachment files alone do not cover generated image
sizes, plugins, themes, config, remote/offloaded media, or live HTTP behavior.
