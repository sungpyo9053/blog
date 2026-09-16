# Kakao self-chat reports

`huntlab-kakao-report.timer` sends at 07:00 and 11:00 Asia/Seoul.
07:00 reports today's briefing; 11:00 reports today's briefing and deep article.
Briefing publication is read from the public WordPress REST API. Deep article
status uses run results and successful Publisher audit records; a pending run
is never described as successful. Each message is at most 200 characters.

The runner uses a dedicated Node 22 + mcporter 0.9.0 installation under
`/home/ubuntu/.local/share/huntlab-mcp`. Its `.bin` directory must precede
system Node in PATH. PlayMCP's `mcp-gateway` connection and OAuth credentials
live outside the repository in `/home/ubuntu/.mcporter/` (directory 0700,
credentials 0600). Authenticate using the official PlayMCP external-agent
guide; never put tokens in repository files, command logs, or reports.

Preview with `.venv/bin/python scripts/send_kakao_report.py --slot 07` or
`--slot 11`. `--send` performs delivery. A per-date/per-slot receipt in
`output/kakao-reports/` prevents duplicate sends. Unconfirmed delivery is not
retried automatically because the provider may already have accepted it.
Check the recipient and `journalctl -u huntlab-kakao-report.service` before
any manual retry. Authentication revocation/expiry may require reconnection.

Install the service and timer into `/etc/systemd/system/`, run daemon-reload,
then enable/start the timer. `Persistent=false` prevents install-time catch-up.
Verify the next scheduled times and a real service delivery before handoff.

## Verified article publication notification

`scripts/publication_notification.py` reuses the same approved PlayMCP self-chat
connection. The deep-article runner calls it **after saving** the publication
result and passing the independent public HTML audit. It does not send for
READY-only, failed, no-topic, or unverified results. It requires the exact
HuntLab HTTPS article URL, HTTP 200, title, and evidence-link confirmation.

Receipts live separately in `output/kakao-publications/post-<id>.json` and are
deduplicated by WordPress post ID, across pipeline run IDs. A notification error
must not alter the saved publication success or invoke Publisher again. The
07:00/11:00 status summaries remain separate from the publication event.

The deep-article service needs the same private Node/mcporter PATH and
`MCPORTER_BIN` as `huntlab-kakao-report.service`. No OAuth token is added to the
unit, repository, receipt, or log.

Preview eligibility (no send):

```sh
.venv/bin/python scripts/publication_notification.py --result output/evidence-deep-article-runs/<run-id>/result.json
```

Retry only a notification after fixing a missing executable/configuration:

```sh
.venv/bin/python scripts/publication_notification.py --result output/evidence-deep-article-runs/<run-id>/result.json --send
```

Already-sent receipts do not resend. `not_sent` means the executable never
started and is retryable. `attempting` or `delivery_unconfirmed` means delivery
may already have occurred; no automatic retry is allowed. After checking the
actual self-chat, an operator may explicitly add `--retry-unconfirmed`, accepting
the possible duplicate-notification risk. The CLI only sends a notification;
it cannot create, update, or republish a WordPress post. A recovered public audit
can use its saved `public-audit-recovery.json` instead of `result.json`.
