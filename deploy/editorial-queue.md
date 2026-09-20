# Reviewed editorial queue

Superseding 2026-09-20 user correction: `wordpress_schedule=true` uses native
WordPress `future` posts, not filesystem-only reservations. The approved backlog
target is seven. `schedule_editorial_queue.py` owns the lane lock, checks fresh
publish/draft/future inventory, sources and independent release review, then
stores a verified draft and schedules the same ID for a free next-day 10:00 KST
slot within seven days. Unknown mutations remain blocked for reconciliation.
Install the schedule service/timer on the runner and wordpress-future service/
timer on the WordPress host. The latter executes only due publish_future_post
events each minute as www-data; expected granularity is 0–1 minute plus runtime.
The old 10:00 runner does not publish in native scheduling mode.
`fill_editorial_schedule.py` is a bounded one-shot refill of up to seven attempts,
stopping on failure/no candidate; it is not proof of seven actual reservations.
Actual post IDs and dates must be read back. Post-publication verification and
notification run separately. Existing 02:00/14:00 preparation remains available.

The following describes the legacy filesystem-only mode:

Preparation: 02:00 and 14:00 KST, one candidate per run, target 3 queued articles,
hard maximum 7. No WordPress writes during preparation. This is a server-side
reviewed queue, not WordPress future posts. Expiry is 7 days from final review and
preparation. Source snapshots are taken before independent final review.

Release: existing 10:00 KST timer, shared lock and daily ledger, at most one
publication. Immutable files and source digests are checked, complete WordPress
inventory is refreshed, and a separate release reviewer compares current search
intent against all public/draft/other queued articles. No writing or repair is
allowed in the release review. Changed/unknown evidence and duplicate intent HOLD.

The publisher sends no automatic retries. Queue status `publishing` and shared
progress `unknown` are durable barriers before media/tag/post mutations. Confirmed
post creation consumes the day even when public audit fails. Reconciliation is
required after uncertain writes; restarting a timer must not repeat them.

`config/editorial-queue.json` enables this path. Without enablement the previous
direct lane remains. Install both preparation unit files, daemon-reload and enable
the preparation timer only after tests and read-only production checks. Preserve
the existing deep-article timer. Persistent=false prevents catch-up publication.

Tests use synthetic articles and mocks; they do not prove an actual prepared
article or scheduled publication. Record these separately. The target is not a
claim that 3 articles are already queued. Held items remain available for diagnosis;
do not edit their approvals or quietly reset them to queued.
