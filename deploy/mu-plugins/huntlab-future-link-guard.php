<?php
/**
 * Plugin Name: HuntLab Future Link Guard
 * Description: Pre-written posts cross-link; a link to a post that is not published yet renders as plain text (no 404) until it goes live.
 */

add_filter(
    'the_content',
    static function ( string $content ): string {
        return preg_replace_callback(
            '#<a\s[^>]*href="https://huntlab\.app/([a-z0-9-]+)/?(?:\#[^"]*)?"[^>]*>(.*?)</a>#is',
            static function ( array $m ): string {
                $p = get_page_by_path( $m[1], OBJECT, array( 'post', 'page' ) );
                // Unknown slug (category, tag, deleted) is left alone; only scheduled/draft targets are unwrapped.
                return ( $p && 'publish' !== $p->post_status ) ? $m[2] : $m[0];
            },
            $content
        );
    },
    9
);

// Publishing runs do_enclose(), which HEADs every link in the post; links to still-scheduled posts log 404s. No post here carries media enclosures.
add_filter( 'enclosure_links', '__return_empty_array' );

// Pre-written posts keep the write time as post_modified, so a scheduled post went live with
// dateModified earlier than datePublished (128 published posts on 2026-11-14). Going live counts as the last edit.
add_action(
    'transition_post_status',
    static function ( string $new, string $old, WP_Post $post ): void {
        global $wpdb;
        if ( 'publish' === $new && 'future' === $old && $post->post_modified < $post->post_date ) {
            $wpdb->update(
                $wpdb->posts,
                array( 'post_modified' => $post->post_date, 'post_modified_gmt' => $post->post_date_gmt ),
                array( 'ID' => $post->ID )
            );
            clean_post_cache( $post->ID );
        }
    },
    10,
    3
);
