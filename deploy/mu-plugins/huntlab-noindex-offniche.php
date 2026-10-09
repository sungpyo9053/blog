<?php
/**
 * Plugin Name: HuntLab Off-niche Noindex
 * Description: Keeps the 2026 WordPress/automation dev-log posts online but out of search, so the site reads as
 * one Physical AI / ROS 2 topic. Owner-approved 2026-10-08; audit in editorial/operations/site-trust-audit-2026-10.md.
 * Posts with any Search impressions (132, 96) are deliberately left indexable. Undo: delete this file.
 */

const HUNTLAB_OFFNICHE_NOINDEX = [ 749, 706, 699, 698, 373, 301, 290, 50 ];

add_filter(
    'aioseo_robots_meta',
    static function ( $attributes ) {
        if ( is_singular( 'post' ) && in_array( get_queried_object_id(), HUNTLAB_OFFNICHE_NOINDEX, true ) ) {
            $attributes['noindex'] = 'noindex';
        }
        return $attributes;
    }
);

add_filter(
    'aioseo_sitemap_exclude_posts',
    static fn( $ids ) => array_values( array_unique( array_merge( (array) $ids, HUNTLAB_OFFNICHE_NOINDEX ) ) )
);
