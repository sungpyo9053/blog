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
