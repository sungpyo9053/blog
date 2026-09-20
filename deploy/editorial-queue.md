# Reviewed editorial queue

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
