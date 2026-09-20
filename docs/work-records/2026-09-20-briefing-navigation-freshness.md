# Briefing navigation and stale-source repair

Implementation/deployment: `852e85d`, 2026-09-20 KST.

## Confirmed causes

- `/briefing/` intentionally rendered only core signals and selected sources; other
  sections required a date-detail click with weak discovery. It was not missing data.
- The runner's editorial collector timer was disabled. The actual cache was checked
  at `2026-09-05T14:20:00.970173+00:00` (189 rows). Analysis loaded this cache without
  the existing six-hour freshness validation. Optional planner checks only warned.
- Selected-source headings asserted "today" irrespective of publication age.

## Applied changes

- Prominent full-report link and seven conditional section links; date details get
  an in-page table of contents. Responsive wrapping, 44px targets, keyboard focus.
- Neutral selected-source title, publication-time age badges, and an explicit warning
  when collection was older than six hours at report generation. Older reports use
  their own report date, not the wall clock. Missing source dates are not replaced
  with report creation dates. Historical evidence is not silently swapped out.
- Daily service now collects sources in `ExecStartPre`, with failure blocking analysis.
  Analysis rejects stale caches and stale frozen resume snapshots before a model call.
  The separate disabled collector timer stays disabled; no second schedule required.

## Evidence and boundaries

- Local: 736 tests run, 729 passed, 7 skipped; diff check passed. PHP unavailable
  locally. Runner focused suite: 48 run, 47 passed, 1 PHP-dependent skip.
- WordPress host PHP syntax check passed; seven actual PHP date-classification boundary
  cases passed. Deployed PHP/CSS SHA256 matched local files exactly.
- Actual collector service exited 0; cache checked at `2026-09-20T03:30:44.219328+00:00`,
  21/24 sources successful, 180 rows. Fresh cache passed the gate; retained old cache
  failed it. Failed individual feeds are not presented as complete source coverage.
- Installed daily service matches tracked unit hash; systemd verification passed;
  daily timer remains enabled. This is collection and gate verification, not a new
  full analyst-to-publication run. Next scheduled briefing remains 04:00 KST.
- Live browser: summary-to-detail click passed; desktop application-decision and
  mobile keyword anchors landed within 1px of their headings. All seven target IDs
  exist; all four older selected items show background badges. Temporary 390px
  viewport had no document horizontal overflow and was reset afterwards. Keyboard
  Tab reached the first section link with a visible solid outline. This is browser
  viewport testing, not a physical iPhone or screen-reader certification.
- Existing reports and article bodies were not rewritten or republished. No extra
  Kakao send or deep article was triggered. The latest old report retains its warning
  until a separately validated fresh report replaces it.

## Recovery

- WordPress two-file backup: `/var/backups/huntlab/20260920-briefing-navigation/`.
- Runner source cache: `backups/editorial-sources-before-20260920-ui.json`.
- Runner previous service: `/var/backups/huntlab-daily-before-20260920.service`.
- Restore only the exact affected files if rollback is needed; do not rewrite old
  manifests, fabricate updated collection times, or remove unrelated user changes.
