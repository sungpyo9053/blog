# Site trust audit — off-niche posts (2026-10-09)

Scope: the 10 live posts outside Physical AI / ROS 2. Data: GSC 28 days (09-08..10-06), GA4 28 days page views,
URL Inspection verdict on 10-09. Owner pre-approved noindex on 10-08 ("추천대로 해"); posts with any Search impressions are excluded.

| id | slug | GSC impr | clicks | GA4 views 28d | index verdict | action |
|---|---|---|---|---|---|---|
| 749 | wordpress-db-restore-attachment-audit | 0 | 0 | 18 | NEUTRAL | noindex + sitemap exclude |
| 706 | evidence-first-ready-publishing-pipeline | 0 | 0 | 1 | NEUTRAL | noindex + sitemap exclude |
| 699 | wordpress-noindex-sitemap-consistency | 0 | 0 | 3 | NEUTRAL | noindex + sitemap exclude |
| 698 | wordpress-rest-html-200-validation | 0 | 0 | 2 | NEUTRAL | noindex + sitemap exclude |
| 373 | topic-planner-topics-md-retry | 0 | 0 | 2 | NEUTRAL | noindex + sitemap exclude |
| 301 | wordpress-quick-summary-regex-fix | 0 | 0 | 0 | NEUTRAL | noindex + sitemap exclude |
| 290 | wordpress-rest-api-fake-client-test | 0 | 0 | 1 | NEUTRAL | noindex + sitemap exclude |
| 132 | wordpress-rest-api-pagination | 5 | 0 | 0 | PASS | keep (has impressions) |
| 96 | wordpress-internal-link-backup | 2 | 0 | 2 | PASS | keep (has impressions) |
| 50 | wordpress-rest-api-retry | 0 | 0 | 1 | PASS | noindex + sitemap exclude |

## Applied
- `deploy/mu-plugins/huntlab-noindex-offniche.php` (AIOSEO `aioseo_robots_meta` + `aioseo_sitemap_exclude_posts`).
- Verified: the 8 pages return 200 with `noindex, max-image-preview:large`; post sitemap 36 → 28 URLs; 132/96 and Physical AI posts unchanged.
- Before: every post had `max-image-preview:large` only. Undo: delete the mu-plugin file from wp-content/mu-plugins.

## Finding
Three old dev-log posts (132, 96, 50) are indexed (PASS) while new Physical AI posts are not. Google is not refusing the
whole site; the new posts are likely too new / under-linked. Re-check with the 10-12 index comparison.
