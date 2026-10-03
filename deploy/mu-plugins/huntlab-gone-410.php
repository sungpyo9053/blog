<?php
/**
 * Plugin Name: HuntLab Gone 410
 * Description: URLs of posts deliberately unpublished (draft/trash/private) answer 410 instead of 404,
 * so search engines drop them faster. Republishing a post makes its URL live again automatically.
 */

add_action(
    'template_redirect',
    static function (): void {
        if ( ! is_404() ) {
            return;
        }
        $slug = sanitize_title( basename( (string) wp_parse_url( $_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH ) ) );
        if ( '' === $slug ) {
            return;
        }
        global $wpdb;
        $gone = $wpdb->get_var( $wpdb->prepare(
            "SELECT 1 FROM {$wpdb->posts} WHERE post_name IN (%s, %s) AND post_type = 'post' AND post_status IN ('draft','trash','private') LIMIT 1",
            $slug, $slug . '__trashed'
        ) );
        if ( $gone ) {
            status_header( 410 );
            nocache_headers();
        }
    },
    0
);
