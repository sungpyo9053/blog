# Publication pipeline operational safety readback

Reviewer: `quality_cycle_pipeline` (AI). Observation window: 2026-09-16 02:53–02:55 KST. This is an independent readback of the root operator's activation, not an independent review of code authored by this reviewer and not publication approval.

## Verdict

The activated retirement epoch validates; all nine historical unresolved runs remain `unknown` and cannot resume. The new backup-media candidate passes post-cutoff provenance validation. A new live run is in progress and correctly prevents another publication attempt through the unresolved-write guard. No completed publication is established by these observations.

## Activated boundary and integrity

- Server checkout: `4b15efea26e8d5c0d2e0af898a88d53b019112ef`.
- Exact active epoch SHA-256: `1001ae6c1cd9bb6fde1dd4e94836051804ed58c171a7b15ed3395e330bdac4c6`; approval hash matches and reviewer kind is explicitly `ai`.
- `load_epoch` succeeds on the deployed repository and original server run directory. This checks the complete direct-file hash set of every retired run, linked inventory/quiescence evidence hashes, repository identity, cutoff ancestry, approval, and dates.
- Source cutoff: `e2aa8825f1e99b99305a2e7462425f80b1c565b1`. Actual server `git show -s --format=%H %cI` reports **2026-09-16 02:14:48 +09:00**.
- Actual sealing: **2026-09-16 02:50:19 KST**; epoch start day: `2026-09-16`. Source-event boundary and activation time are intentionally distinct. The cutoff follows every retired September 5–9 attempt and precedes the new operational feature. No seal was regenerated during this review.
- Hash-bound six-status inventory collected at sealing contains 123 unique records: publish 9, draft 113, trash 1, pending/private/future 0. This is the activation snapshot, not a claim that live inventory stays unchanged during the subsequent E2E.
- Quiescence concerns legacy publishing executors and requests, not an absence of all public HTTP traffic. Its approved evidence is validated by `load_epoch`; this review does not replace the operator's earlier process/worker-birth observations.

## Historical uncertainty is preserved

For each exact run below, the original stored state still contains `wordpress_write_count: unknown`; invoking the deployed `reject_legacy_run` rejects resume:

| Run ID | Original uncertainty | Resume |
| --- | --- | --- |
| `20260905T143359Z-7b94ded592` | Preserved | Rejected |
| `20260905T143849Z-aa8c5df434` | Preserved | Rejected |
| `20260907T010017Z-2619e2d463` | Preserved | Rejected |
| `20260907T112219Z-aeda69c46c` | Preserved | Rejected |
| `20260907T113259Z-ed34eb6313` | Preserved | Rejected |
| `20260907T121640Z-a2b66ecbf0` | Preserved | Rejected |
| `20260907T124448Z-e54021079c` | Preserved | Rejected |
| `20260908T010017Z-0eb33447f3` | Preserved | Rejected |
| `20260909T010017Z-9c3cc2008f` | Preserved | Rejected |

Retirement is permanent execution quarantine, **not** evidence that these historical runs wrote zero posts. Any change to pinned files invalidates the exemption. New/current unknown runs remain blocking.

## New candidate and live safety lock

Candidate artifact: `output/topic-miner/2026-09-16/20260915T175232Z-58ef26f9b1/candidates.json`.

- Candidate: `audit-backup-media-f224faf3f9ba`, READY.
- Topic seed: “WordPress DB 복원 뒤 첨부파일 누락을 찾는 검사 만들기”.
- Source anchor: `scripts/audit_backup_media.py`.
- Event: `scripts/audit_backup_media.py@1d64189123d90ee8d0f586cbda663f18f938ac36`.
- Evidence commits: `1d64189123d90ee8d0f586cbda663f18f938ac36` (actual committer time **02:36:19 KST**) and `f4bc7b42376e62ee1ae7195d6a178c63d27263f6` (**02:39:15 KST**).
- Deployed `validate_candidate` passes: strict cutoff ancestry, actual nonempty patches, changed source anchor, no stable-patch replay from pre-cutoff history, and no retired identity/fingerprint match. Commit timestamps alone are not the acceptance criterion.

At **02:55:20 KST**, earlier completed current-day records report zero writes, including dry-run `20260915T175204Z-5c3ef97a03` (one candidate, zero writes). The new execution `20260915T175232Z-58ef26f9b1` has progress stage `publisher_started`, write count `unknown`, and no result/publication receipt yet. This coarse marker precedes the downstream workflow; it does not prove that a WordPress request has occurred.

Calling actual `published_today(..., '2026-09-16', repo=repo)` raises `PipelineError: Publication reconciliation required: 20260915T175232Z-58ef26f9b1`. This is the expected in-progress safety lock, **not a certified current total of zero**. The root operator's zero-count pre-start observation and this later held state are different points in time. Completion still requires Publisher receipt, authenticated readback, public body/HTTP verification, and final daily-count readback.

## Schedules and scope

At **02:53 KST**, both daily 04:00 and evidence 10:00 timers were enabled and active/waiting with `Persistent=no`; the Kakao timer was active with next 07:00. The evidence service was activating with live MainPID `1457959`; the daily service was inactive with MainPID 0. The operator's earlier timer pause was an intentional migration window and had already ended before this observation. This review did not change timers or services.

This review performed only SSH reads, local validation calls, Git timestamp queries, and this local report write. It made no server mutation, WordPress write, epoch reactivation, or publication retry. AdSense acceptance and a numerical approval probability are not established by pipeline safety checks.

## Subsequent E2E editorial defect and local prevention

The root operator and content audit identified a P1 in the first Writer draft: a block advertised as copy-and-run contained literal `<check-dir>/manifest.json`, which the shell interprets as redirection rather than a usable directory. This is a real draft-quality defect; an active pipeline or passing prior tests does not imply that the draft was ready to publish. Root reported replacing Research material with an isolated, quoted-path example and verified 0/1/0 outcomes; final Reviewer approval and publication remain separate gates.

At root's subsequent request, a local-only preventive change adds the `unresolved_shell_path_placeholder` editorial failure for explicitly bash/sh/shell-labelled Markdown or HTML code blocks. It intentionally covers only unquoted angle-bracket dir/path placeholders, excluding quoted literal strings, comments, common heredoc data, and text/plain transcripts. It is not a full shell parser, does not execute article code, and does not establish command safety or successful execution. Researcher/Reviewer instructions now explicitly preserve intended control experiments and actual implementation/retest chronology, and require the final copyable command form to match isolated execution evidence. This change was not deployed or used to modify the running server by this reviewer.

## Terminal E2E readback (03:29 KST)

The real attempt terminated before Publisher: the gate recorded only `private_runtime_path` against the exact current publish-body hash, after the second Reviewer had APPROVED at 03:23:38. The service was failed/MainPID 0. The complete operational stage trace has no Publisher invocation or passed publication-contract event, and no publication audit matches the run. Fresh authenticated six-status inventory remained 9 published, 113 drafts and 1 trash, with no candidate identity. A hash-bound, deliberately unapproved zero-write proposal and detailed evidence were prepared privately under `output/quality-cycle-20260916/failed-run-reconciliation-182923/`. Original unknown states remain unchanged; root approval/activation is separate. This is a failed editorial E2E with successful pre-write containment, not successful publication.

Root additionally reported that running the suite on the activated server exposed one fixture-isolation error: `test_resume_published_topic_skips_all_content_stages` used synthetic run ID `run` while reading the real epoch. Root isolated that test's PROJECT_ROOT in a temporary directory; this is a test-environment correction, not a relaxation of runtime ID validation. This review has not independently rerun the subsequently patched server suite and does not claim that later result.

## Reconciled failed attempt and new E2E (03:34:53 KST)

Independent SSH readback now confirms deployed HEAD `15cff965f490250f61778b7cad08609516c6c816`. Actual `read_reconciliation` accepts the root-reviewed receipt for failed run `20260915T175232Z-58ef26f9b1`, returning **0** writes. Receipt SHA-256 is `117f5cbc342d08d6d0767091d909b5d194182866b72a62883b2c651506214247`; reviewer identity explicitly says AI, not human approval. Original progress hash `08f9384510e56733af454684f4a1cec45b635e872f918dd3f63d17f01c2d33ee` and result hash `d5804a7b58ed53c577534d3a54acdfcb035001e93c61578db33ff7746e82a420` are unchanged. This is a separate evidence-backed reconciliation of the known pre-Publisher failure, not a change to the nine uncertain historical runs. `load_epoch` still validates all nine original file sets and all nine resume attempts are rejected.

Dry-run `20260915T183317Z-93774689d1` completed with one candidate, zero writes and `ready_not_published`. A separate new actual run `20260915T183332Z-188bac8755` is in progress: progress says `publisher_started`/`unknown`, with no completed result/publication receipt. Actual `published_today` therefore raises `Publication reconciliation required` for **this new run only**. Root's zero-count check between reconciliation and restart must not be presented as the current count during this new attempt.

At this observation, the evidence service is activating with MainPID `1474593`. The 10:00 evidence timer and 07:00-next Kakao timer are active/waiting (`Persistent=no`). A follow-up exact-unit read confirms **`huntlab-daily-pipeline.timer`** active/waiting, `Persistent=no`, with next 04:00 KST. An initial diagnostic accidentally queried the unused name `huntlab-daily.timer`; its inactive result must not be attributed to the real daily schedule. Root reports the deployed server suite passed 497 tests in 2.987 seconds from root's tool observation (no saved output artifact); this reviewer has not independently rerun that suite during the live attempt. Local tests before the root deployment passed 497 in 6.643 seconds. These environments/results are distinct.

No new-run writes, service changes, receipt installation, or retries were performed by this readback. **The restarted E2E is not yet a final successful publication.**
