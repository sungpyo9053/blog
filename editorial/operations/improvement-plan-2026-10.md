# HuntLab improvement plan (2026-10-08)

Goal: AdSense $200/month within policy. Grade every day by revenue, outside visits and waitlist sign-ups;
operations work is listed separately. Current state: revenue ~₩0, outside visits ~0/day, 0 of ~25 Physical AI
posts indexed by Google (sitemap: "Discovered – currently not indexed"), 7-day buffer full through 10/14.

## Root cause hypothesis
Google is withholding indexing because of site-level trust: the domain previously mass-published
off-topic AI articles (42 retired with 410 on 10/03), and 10 off-niche WordPress/automation dev-log posts
are still live next to the Physical AI lessons. To be confirmed by the 10/12 index comparison.

## Priorities (impact on revenue × feasibility)

| # | Item | Why it moves revenue | Owner | When |
|---|---|---|---|---|
| P1 | Site trust audit: the 10 live off-niche dev-log posts (wordpress-*, topic-planner, evidence-first) — impressions, internal links, recommendation (keep / noindex / 410) | Mixed-topic AI history is the leading suspect for zero indexing | Claude prepares, **owner approves** (bulk change to public posts) | 10/09 audit → 10/12 decision |
| P2 | Real author page (E-E-A-T): who measures, environment, GitHub experiments repo | Trust signal for indexing and for paid guide buyers | Claude drafts (unpublished), **owner decides real name/credentials** | 10/10 draft |
| P3 | tf2 0.25.23 deadlock article (EN first): measured 5/5 vs 0/5 already in `experiments/` | Fresh, unanswered search demand; feeds guide ch. 3; backlink-worthy | Claude: extend experiment runner to pinned Humble snapshot images, then let discovery/pipeline produce it through the normal gates | 10/09 |
| P4 | 10/12 index comparison (Google/Bing/Naver) → keep course or pivot (fewer deeper posts / separate EN domain / revenue model) | Decides whether search can ever pay | Claude reports, **owner decides** | 10/12 |
| P5 | Distribution: daily GitHub answer routine (≤1/day, exact match only); public experiments repo | Only proven outside-visit channel so far | Claude (running) | daily 00:03 |
| P6 | Paid guide: waitlist live; build when first sign-up | $19–29 × 10/month = $200 without big traffic | Claude builds, **owner: payment account, seller name, price, sender address** | on first sign-up |

## Not doing
- Changing cadence or quality gates (owner rule: keep 7-day buffer).
- Bulk changes to public posts without owner approval.
- Any link/scheme to manipulate rankings.
