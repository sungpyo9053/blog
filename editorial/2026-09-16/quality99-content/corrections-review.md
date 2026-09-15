# Existing-post corrections — independent AI review

status: APPROVED
manifest_sha256: 0dd524ce7c55c776e28002db34772f7f4ec447c9d80b7da50638242209773704
reviewer: quality_cycle_audit
reviewer_kind: ai
wordpress_writes: 0

Approval is limited to the exact manifest and three existing-post body corrections below.
It does not authorize new posts, title/slug/category/media changes or a 99-point assessment.
The author did not approve their own work. Reviewed CLAUDE.md, the current Reviewer contract,
delegated AI-review boundary in publisher-guide, Research, before/after HTML and verification.

## Exact approved targets

| ID | Existing title / slug | Approved after HTML SHA-256 |
| --- | --- | --- |
| 132 | 첫 REST 응답에서 19개가 빠졌다: WordPress 119개 글 전수 감사 / wordpress-rest-api-pagination | d62d3772b604bb0cde0e539d7ffe97879e1d62fe53cc7a7abde7b0b582beb988 |
| 301 | WordPress 20초 핵심 요약 중복 삽입 버그 제목 정규식 수정 작업 기록 / wordpress-quick-summary-regex-fix | 1fc963d72004677692349763b651d60850907db66f727704626cd6add0649ad0 |
| 749 | WordPress DB 복원 뒤 첨부파일 누락을 찾는 검사 만들기 / wordpress-db-restore-attachment-audit | 87ceb0b0d8f81eeb84f50cdcfa3827ec86d926e8781ad8da805bfe816b1937a3 |

Calculated manifest and all six before/after hashes; they match the manifest. Before raw
bodies and slugs match the captured full inventory. Publisher must still perform its fresh
authenticated raw/identity comparison and complete all preflight checks before any write.
This approval becomes invalid if the manifest or approved bodies change.

## Independent reader execution

Executed the new Bash heredocs extracted and HTML-unescaped from the proposed final HTML,
without changing the blocks, in empty temporary directories. The documented prerequisite,
Python 3.11+, was satisfied using installed Python 3.12.9 selected through PATH. Neither new
example requires checkout, .venv, packages, credentials or a working-directory fixture;
checkout revision is therefore not applicable to these standalone snippets.

| Post | Exact new Bash block SHA-256 | Actual result |
| --- | --- | --- |
| 132 | 022add88f1308992832bad4e5982cd04d16aff2786d27e69d3928ee2f08e6843 | exit 0; page lengths 3/3/3/1; total 10; pages 4; unique_ids 10; passed true; files created 0 |
| 301 | 7994cdce414ffe645c182a8be5351f4d4b6b178c916095ce94dfdd27889230dc | exit 0; summary_h2 1; automatic_boxes 0; passed true; files created 0 |

Also independently ran test_examples.py: two unittest methods passed, containing the
documented 12 controlled subcases. These are not 12 separate test methods or production
failure injections. An initial diagnostic extraction selected 132's existing historical
curl block; it made a read-only GET and two local temporary files. It was not counted as
the new-example verification. The exact new heredoc above was subsequently selected and
executed independently, with zero files created. No WordPress write occurred.

749's Bash examples, links and image references are unchanged by the proposed correction;
the prior independently verified complete reader procedure remains intact. Its intentional
DB-only control, synthetic one-file reproduction, separately documented private 373-file
result and explicit non-verification of whole-site recovery are preserved.

## Facts, privacy, overlap and reader value

Rechecked the [WordPress pagination reference](https://developer.wordpress.org/rest-api/using-the-rest-api/pagination/)
for page/total headers and ID ordering, and the [Python HTMLParser reference](https://docs.python.org/3/library/html.parser.html)
for tag/data callbacks and character-reference conversion. The new text's claims stay within
these APIs and the actual observations. HTMLParser is not a browser DOM/visibility proof;
the article explicitly excludes JS, CSS visibility and PHP runtime verification.

132 preserves the historical 119 count and labels the new 10-count observation as dated,
not a permanent expected total. Its 300-post bound, redirect/content-type/size failure,
duplicate and changing-total checks, and non-atomic snapshot limitation are stated.
301 counts actual headings/class tokens rather than escaped example strings, gives a
page-specific expected result, and distinguishes diagnostic failure from a proven cause.
749 removes awkward exact-title repetition and redundant output without inventing history.

Compared the three replacements together against the complete captured 123-post inventory
(10 publish, 113 draft), excluding each article's own ID. All three editorial gates passed.
The full title inventory and relevant nearby bodies were examined for search intent:
132's whole-collection completeness differs from 380's ETag freshness and 698's REST response
validation; 301's duplicate summary diagnosis differs from 699's noindex/sitemap consistency;
749's attachment integrity differs from 96's JSON body backup and 16's general installation.
No new competing search intent or duplicated conclusion was found. This is not a claim
that every unrelated archived article was newly fact-checked.

No new private runtime paths, credentials, unsupported personal experience or unsubstantiated
success guarantees appear in the additions. Existing images and historical evidence are
unchanged; these narrow corrections do not fabricate replacement captures. No new H1,
advertising claim, taxonomy or identity mutation was introduced.

## Publisher conditions and remaining scope

Use the existing approved-corrections updater: fresh inventory, stale-raw guard, protected
metadata comparison, backup before body-only write, zero blind retries, exact readback and
public body verification. A concurrent edit or ambiguous attempt must stop/reconcile; this
approval is not permission to overwrite newer content. All three preflights must pass
before writing any post. Review any changed manifest again.

No release-blocking defect was found in these corrections. C1/C2 implementation review can
use this evidence, but their publication conditions remain unverified until Publisher and
public checks finish. C3's separate full-10-post final review, U1/U2, operational deployment,
long-term observation and full disaster recovery are not certified by this approval.
