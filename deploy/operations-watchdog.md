# Bounded operations recovery

Ponytail 4.10.0: reuse the existing deep lock, public-audit recovery and notification
receipts; Python stdlib and systemd, no new runtime dependency or autonomous shell.
ECC 2.2.2: TDD workflow and verification-loop used for this implementation.

Every fifteen minutes (`:05/:20/:35/:50`, Asia/Seoul), inspect the last seven days
of deep runs, today's 07/11 report receipts, the current Sunday's weekly result
(after 21:00), and the public site HTTP status. A missing deep run is reported after
12:00; an unfinished inactive execution after two hours. Active jobs are not restarted.
The watchdog's own nonzero service exit and journal expose monitor failures.

## Automatic actions

- Confirmed WordPress publication + failed public audit: retry only the existing
  read-only public audit, at most three watchdog attempts per run.
- Verified publication from the last 24 hours with no notification receipt or
  `not_sent`: confirm public evidence again, then invoke the existing deduplicating
  notifier, at most three watchdog attempts per post. No historical notification backfill.
- Save state before attempting recovery; preserve original failure records.
- Send a new operations incident summary to the approved Kakao self-chat, deduplicated
  by incident set and capped at two summaries per KST day. Ordinary problems must
  persist for three checks; unknown WordPress writes are escalated immediately.
  Resolved transient incidents do not generate user alerts. The same uninterrupted
  incident is not resent the next day; a resolved incident that recurs is new.
  Do not retry an uncertain incident alert. This is separate from repeating a
  post-publication notification.

## Low-touch operation (2026-09-20)

`config/operations-notifications.json` selects weekly routine reporting. Successful
post notifications and healthy 07/11 reports are retained as `suppressed_healthy`,
not falsely marked sent. Failed 07/11 checks are saved as `queued_issue`; the watchdog
rechecks the live state without sending or modifying the original receipt. Recovered
checks are recorded separately by original-receipt hash. Only persistent issues are
escalated. The scheduled checks still run; failures remain visible in private records.
The Sunday report includes deduplicated confirmed automatic deep-lane publication
receipts for Monday–Sunday; manual launch batches are not counted as automatic runs.
The existing 4-week assessment cadence is unchanged.

Kakao is the user's only notification channel. The shared sender prepends mcporter's
own directory to PATH (to select its companion Node) and tests the runtime before
starting any MCP call. A failed preflight becomes definite `not_sent`; failures after
the send starts remain uncertain. Historical uncertain receipts are never rewritten
as known-not-sent. No email/other account is added.

Actions are described in Korean rather than raw error codes. The user need not
inspect logs; unresolved code defects still require invoking the coding agent.
This reduces interruptions, not the need for OAuth interaction, account actions,
or manual authorization for unsupported repair. Kakao outages cannot be reported
through a separate channel because none is available.

Low-touch verification: 732 tests run, 726 passed, 6 pre-existing skips. The focused
reporting/watchdog/weekly suite has 81 passing tests. New regression cases prove
healthy suppression, unknown-receipt preservation, pre-send runtime failure,
three-check escalation, cross-day deduplication, live-status recheck without
overwriting original report records, and weekly receipt deduplication.

In weekly routine mode, historical uncertain individual-post notification receipts
remain unchanged and visible in watchdog issues, but do not trigger operator alerts.
They are never resent. Uncertain publication writes still require immediate escalation.

## Not automatic

No Publisher invocation, article or media creation, content editing, quality-gate
bypass, service restart, Git mutation, model call, code patch/deployment, credentials
change, or OAuth login. Unknown publication/delivery states remain unresolved until
reconciled. No candidate is normal, not a reason to force writing. Website outages,
code defects, missing scheduled jobs, weekly failures and analytics failures are
reported, not claimed fixed. A seven-day window and three-attempt ceiling are deliberate.
There is no independent external alert channel if Kakao is unavailable; the local
incident state and systemd journal remain available. This is bounded recovery, not
general self-repair or an uptime guarantee.

## Operations

Read-only preview: `.venv/bin/python scripts/operations_watchdog.py`.
`--apply` writes private watchdog state and may send Kakao messages; never WordPress.
All invocations use the shared deep-publication lock and a watchdog lock.
Install both unit files from `deploy/`, run `systemctl daemon-reload`, then
`systemctl enable --now huntlab-operations-watchdog.timer`. Validate the installed
unit hashes, an actual service run and `output/operations-watchdog/latest.json`.
Do not delete attempt state to obtain fresh retry budgets.
Stop this component with `systemctl disable --now huntlab-operations-watchdog.timer`;
the daily publishing and weekly editorial timers are independent and remain intact.

## TDD evidence

User journey: ordinary post-publication recovery should not require forwarding a
Kakao message to the chat agent; uncertain writes must not be repeated.

- `c4c4b80`: 16 tests executed RED because recovery module did not exist.
- `324710f`: the same 16 tests GREEN; bounded recovery implementation.
- `8fc3376`: expanded 22 tests, one RED: a dry-run incorrectly hid a missing real run.
- `d903fd7`: 22 tests GREEN; dry-run records excluded from scheduled-run evidence.
- `ee0e2cb`: two behavioral RED cases after server preview exposed historical
  notification backfill; `59e6dae`: 24 tests GREEN with age and fresh-public guards.
- Command: `.venv/bin/python -m unittest tests.test_operations_watchdog -q`.
- Tests cover dry-run side effects, unknown writes, retry limits, active jobs, external
  URL rejection, invalid records/recovery, alert uncertainty, missing schedules,
  public probe, systemd state and CLI lock release. These are mocked failure cases;
  real server service execution is recorded separately, not equated with fault injection.

## Verification (2026-09-20)

- Python compile and `git diff --check`: PASS.
- Whole repository: 718 tests run, 712 passed, 6 existing skips; no failed tests.
- New watchdog: 25 tests passed; stdlib `trace` line coverage 93% (228 executable
  lines). This is changed-module line coverage, not branch or whole-repository coverage.
- Type checker/linter: not run; pyright/ruff are not installed or configured here.
  Compilation and diff checking do not replace those checks.
- Security/diff review: fixed owned-site probe, owned publication URL validation,
  no raw exception/credential output, no external command from logs/model text,
  persisted attempt limits, shared lock, unknown deliveries not retried, no WP writes.
- Server: 38 watchdog/notification tests passed; systemd unit verification passed.
- Actual service executed twice at about09:22–09:23 KST, exit0 both times. It found
  post777's existing uncertain notification and did not retry it. A separate new
  operations warning returned `sent`; the second execution preserved the exact
  state hash, with no second send. No automatic repair was needed/claimed in these
  live runs; recovery fault cases above remain mock-based tests.
- Public post777 body SHA256 and modified_gmt unchanged before/after. Watchdog
  reports WordPress writes0 and has no WordPress write path.
- Timer enabled, next09:35 KST; installed service/timer SHA256 matched tracked files.
- Live private records: `output/operations-watchdog/latest.json`, `state.json` and
  `journalctl -u huntlab-operations-watchdog.service`. This is not long-term validation.
