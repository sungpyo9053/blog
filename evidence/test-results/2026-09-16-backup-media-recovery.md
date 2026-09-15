# WordPress attachment recovery check — 2026-09-16

This is a database import and original-attachment file validation, **not** proof of
complete site restoration. No PHP, plugin runtime, browser image fetch, login, email,
webhook, or cron was executed in the restored environment.

## Actual scope

- Source observations: WordPress 7.0.4; MariaDB 10.11.18; uploads about 102 MiB.
- The September 15 editorial rollback backup contains a DB dump and plugins archive.
  It was not a complete disaster-recovery bundle; this test does not recast it as one.
- A new read-only DB export (`--single-transaction --skip-lock-tables`) and uploads
  archive were made for this test. Raw backups remain private with restricted access.
- Transfer byte hashes were compared with the source server before restoration.
- Isolated target: MariaDB 10.11.19, Docker `mariadb:10.11` image digest
  `sha256:07c0aaff7396b74cb7975cba78257178d188e30f531a5db2b617c48beef13c41`.
- Container network mode `none`, no published ports. No production WordPress writes.

## Observed results

The dump imported successfully into a newly created isolated database. It contains
48 tables, 9 public posts, 113 draft posts, and 373 attachment records. Other content
types and revisions were retained; these counts are not the full `wp_posts` row count.

Attachment paths were read from the **restored DB**. Their expected sizes and SHA-256
values were collected independently from the **source uploads directory**, not from
the restored folder. The same manifest was then used for both checks:

```text
DB import: exit 0; tables=48
Before copying uploads: passed=false; missing_files=373
After copying uploads: passed=true; checked_files=373; failures=0
whole_site_restore_verified=false
```

The uploads archive was checked for unsafe paths, symlinks, special files and entries
outside its uploads root before extraction. The checker also rejects path traversal,
symlink references, malformed hashes, duplicate manifest entries and changed bytes.

## Reader reproduction

The repository provides a synthetic text attachment and a no-network CLI example in
`evidence/lab-fixtures/backup-media/README.md`. It contains no operational dump,
account records or real media. This reproduces the missing-file/hash comparison, not
the private database import. The checker needs Python 3.11+ and no external packages.

## Limits

Original `_wp_attached_file` references do not cover generated image sizes, offloaded
media, themes, plugins, config, server compatibility, rewritten URLs or live HTTP
delivery. A valid DB import and matching original file hashes alone do not prove
that a recovered WordPress site starts or behaves correctly. File and database
snapshots also need a coherent capture point; a DB transaction does not freeze files.
