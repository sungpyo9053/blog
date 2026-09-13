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
