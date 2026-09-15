# Round 2 existing-post corrections — independent AI review

status: APPROVED
manifest_sha256: 74d14d0c5c13e2ea73475e82cb2c6db78d49c53a9af5dc6a439195669c491f5c
reviewer: quality_cycle_pipeline
reviewer_kind: ai
checked_at: 2026-09-15T22:45:13.267246+00:00
wordpress_writes: 0

Approval covers only the six existing-post body replacements in this exact manifest.
It does not authorize new posts, title/slug/category/featured-media changes, media deletion,
an AdSense submission or a site-wide score. The independent Reviewer did not author these
bodies. Reviewer, style, SEO, evidence-article, monetization and delegated Publisher
contracts were read, alongside the complete proposed bodies and research/verification.

## Exact targets

| ID | Preserved slug | Approved after HTML SHA-256 |
| --- | --- | --- |
| 50 | wordpress-rest-api-retry | 74d36e41322d4cb9986bc44f0330e6a305d1016604d36c1b12904a0ca5d5f6ae |
| 96 | wordpress-internal-link-backup | 2e381b830ba97a39c5b6a66b49f7813444cdf488ce62f8e182efd46a5cab776c |
| 290 | wordpress-rest-api-fake-client-test | a50a1991f2c3e2feb0669d8824c1080b11a18b4c457943815076ee66b8fddf78 |
| 373 | topic-planner-topics-md-retry | d6afd849d5b15e5540c4a38608f7876eb92abaeb0707222023f590cab06815fc |
| 698 | wordpress-rest-html-200-validation | fc4b7ae7575585bb4b7fb169b7072169b39e714e90d5975075219dcc25c6457a |
| 699 | wordpress-noindex-sitemap-consistency | a0b871aa0e0ab9a871d5b2309a1b7d691e45de229f3a214288c1644aae12b5d2 |

All before/after bytes match the manifest. Fresh authenticated GETs confirmed all six
raw before bodies, unchanged titles and slugs. The complete fresh inventory contained
123 posts: 10 published, 113 drafts. All six replacements were inserted together before
running the editorial gates; all passed. This includes the first-round corrections
already present in WordPress, not an obsolete pre-correction inventory.
The final 96 after hash differs from its intermediate polite-prose revision only because
one trailing newline was added: removing that final newline reproduces the intermediate
SHA-256 `c4efe598ff1c311ff407a2099d88e91ea9fcf3df0145429062d5de461e883d49`.
No sentence or executable block changed in that normalization.

## Independent exact reader execution

The final HTML's Bash blocks were extracted and HTML-unescaped, then executed without
altering their contents using Python 3.12.9. Three fresh temporary checkouts were created:
50/290 with the documented setup; 373 with its own exact setup; 698/699 with their exact
standard-library-only setup. Each checkout selected the public fixed revision
`170c6ba70c419501171ae741b318a2fb6f4ac38d`. The first two created fresh venvs and installed
the documented requirements; the third created a fresh `venv --without-pip` and installed
no packages. An existing operational venv was not substituted for any preparation.

There were 26 executed setup/block/input cases, all with their expected exit status:

| Operation | Actual result |
| --- | --- |
| 50 retry regression | 3 tests, exit 0 |
| 290 fake Publisher contract | 2 tests, exit 0; no actual WordPress creation |
| 373 isolated artifact example | missing twice fails after 2 calls; second-call creation passes; no third call; overall exit 0 |
| 698 REST comparison | HTML 200 exits 1; JSON 201 exits 0; 5 diagnostic tests pass |
| 699 sitemap comparison | contradictory fixture exits 1; corrected fixture exits 0 |
| 698 and 699 final Lab commands | both exit 0; actual result files read back as READY, before exit 1, after exit 0, WordPress writes 0 |
| 96 exact standalone demo | valid true / missing original false; exit 0; no files created |
| 96 documented file-input variant | valid exit 0; 11 invalid cases exit 1; input bytes unchanged |

The 96 file variant changes only the first line as explicitly instructed in the article.
Invalid cases cover empty original, duplicate/bool IDs, duplicate/self targets, unchanged
body, empty list, missing targets, invalid JSON, invalid UTF-8 and input over 10 MB. These
are synthetic input checks, not restoration of the historical 11-post backup.

Exact executable block hashes:

| Block | SHA-256 |
| --- | --- |
| 50/290/373 setup | 6a1efbff992ed0c1df8aa4655508b7550ccfe8b6d0cff342828d5d3a3f82e51a |
| 698/699 setup | 6df6c606e5e461179713a6e0950564f103129283480e541688205c61b84a55f2 |
| 50 tests | 8467b151d8aa0a1cd77dce2b076590144d8537e67342b3498fd5bd8fc403a1ae |
| 290 tests | 541af563b48bb2ff29c4bc0e4fb2bb98df1e454ecc8c6f076add9b13c19bcd41 |
| 373 example | 204e94f8dca6289ea624398989fc29961e86e877d684855cf522c025665e9f08 |
| 698 before | 896333d6c4e98564d2677fd48a917d28181a330e43a6acb7eac405cd964df018 |
| 698 after | 71f66ca16a949aff6dec449aab8324500845aad345673e278d03f97bdbb74111 |
| 698 tests | 6f81223fc36063c426e4e256e499f7e14af7fd69b58d2fd644563b05ad3ab1af |
| 698 Lab | c0abd54c1520d062d91fb8fab053cf9fcb1cd86b3653ccd5dbc401a80142fc85 |
| 699 before | fad52f637732fa8fd1294d27187141317fd7cb2e918b212b6b80925dbffeb396 |
| 699 after | f9192071ca5e9d4d71e01f3a9d92567960235164f59a146ce834cdf0d8414615 |
| 699 Lab | 2f3d74b7393a6ca25db4ef8b41a334686a3a08f21595e080a9d4b0a72b5b5b08 |
| 96 standalone | 63397dcb41874187119a60dbe46333446b108396da9164ea94e7a9c193bbc512 |
| 96 documented file-input variant | e59f9f066c8eac23b693eaff26b85985b0e1ac1f88f859bacfc2918b3911e20d |

Private detailed evidence is retained under the exact manifest hash in
`output/quality99-round2-independent/`, including the fresh inventory, input fixture
hashes, every exit and actual Lab-result hashes. The execution record SHA-256 is
`fe91f5b36fd3d206721a7f186fda1d68807ab76c880567af9c3649545a50c7aa`.
An earlier run detected a concurrent body change and was not treated as approval.
The final run checked the unchanged complete manifest again before saving this evidence.

## Facts, scope, style and privacy

96's added validation has a usable standalone entry point and preserves the article's
polite register. It explicitly does not prove source authenticity, URL reachability or
rollback. 50 and 290 now provide one complete, pinned preparation sequence rather than
repeated setup prose. Their fixtures do not justify claims of real network failure or
production POST safety. 373 separates its dated historical incident from the new isolated
two-call example. 698 separates the historical four tests from the strengthened five-test
implementation; 698/699 do not invent an operator's earlier intentions or present an
intentional fixture failure as an unexpected production incident.

The unpinned setup issue in 373/698/699 was returned to the Writer: these examples depend
on repository APIs, fixture paths and expected output. All three are now fixed to the
executed revision and direct readers to a separate empty folder. This controls source
drift, not permanent availability of downloads or all future dependency versions.

373's first old capture had unreadable Korean glyphs and excessive empty space. Both
public images were inspected independently. Removing only the first image's insertion
is appropriate because the adjacent text retains the full pertinent dated log, duration,
failure and read-command exit. The legible second capture remains. No image was generated
or edited to manufacture evidence; the underlying WordPress media file is not deleted.
The remaining capture contains no observed private absolute runtime path or credential.
The old private path in the text transcript is now anonymized. Exact original backup
bytes must remain private and must not be committed as public before-body evidence.

Primary-source checks support the relevant API statements:
[HTTP Retry-After](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3),
[WordPress Posts](https://developer.wordpress.org/rest-api/reference/posts/),
[Python file checks](https://docs.python.org/3/library/pathlib.html#pathlib.Path.is_file),
and [Google canonical signals](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls).
Google's canonical/sitemap signals are not a universal self-canonical mandate or an
AdSense approval guarantee; 699 correctly distinguishes the project's audit policy.

The full inventory's titles and relevant neighboring bodies were compared for intent.
50 addresses Retry-After parsing, 290 an isolated create/draft contract, 698 response
format/identity, and 132 collection completeness. These are distinct reader failures.
373 concerns missing stage artifacts; neighboring log-parser and timeout drafts concern
different failure mechanisms, while 706 classifies publication outcomes. 96's JSON body
backup differs from 749's DB-to-upload-file integrity. 699's noindex/sitemap disagreement
differs from 301's duplicate rendered summary. No new competing intent or borrowed
conclusion was introduced by this combined correction. This is not a fresh fact-check
of every unrelated archived draft.

## Publisher conditions

No blocking defect remains in this exact six-body proposal. Publisher must independently
run the existing updater's fresh complete inventory and raw/identity preflight, preserve
all protected metadata, back up exact originals before writing, disable blind retries,
and verify authenticated readback plus public bodies. A changed manifest, concurrent edit
or ambiguous previous attempt invalidates permission to proceed blindly. These local
reader tests and read-only checks do not establish that the corrections are deployed.
Whole-site browser UX, long-term reliability, full disaster recovery and a 99-point
assessment remain separate verification scopes.
