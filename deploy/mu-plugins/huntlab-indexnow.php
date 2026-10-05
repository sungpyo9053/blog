<?php
/**
 * Plugin Name: HuntLab IndexNow
 * Description: Tells IndexNow engines (Bing, Naver, Yandex) about a post or English edition the moment
 * it goes public, including scheduled posts released by WP-Cron. The key is public by design.
 */

const HUNTLAB_INDEXNOW_KEY = '5b413e778afa73b80cfc617219bc9236';

// Serve the ownership key file at /<key>.txt without touching the web root.
add_action(
    'init',
    static function (): void {
        $path = (string) wp_parse_url( $_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH );
        if ( '/' . HUNTLAB_INDEXNOW_KEY . '.txt' === $path ) {
            header( 'Content-Type: text/plain; charset=utf-8' );
            echo HUNTLAB_INDEXNOW_KEY;
            exit;
        }
    },
    0
);

// Ownership proof for Bing Webmaster Tools and Naver Search Advisor; removing it un-verifies the site.
add_action(
    'wp_head',
    static function (): void {
        if ( is_front_page() ) {
            echo '<meta name="msvalidate.01" content="714378BFAD47930C41F5D2703811D27B" />' . "\n";
            echo '<meta name="naver-site-verification" content="8f24fc13c5cb2e150f7c3f1030cbd889d21fd47d" />' . "\n";
        }
    },
    1
);

add_action(
    'transition_post_status',
    static function ( string $new, string $old, WP_Post $post ): void {
        if ( 'publish' !== $new || 'publish' === $old || ! in_array( $post->post_type, [ 'post', 'hunt_en' ], true ) ) {
            return;
        }
        $host = (string) wp_parse_url( home_url(), PHP_URL_HOST );
        wp_remote_post( 'https://api.indexnow.org/indexnow', [
            'blocking' => false,
            'timeout'  => 5,
            'headers'  => [ 'Content-Type' => 'application/json; charset=utf-8' ],
            'body'     => wp_json_encode( [
                'host'        => $host,
                'key'         => HUNTLAB_INDEXNOW_KEY,
                'keyLocation' => home_url( '/' . HUNTLAB_INDEXNOW_KEY . '.txt' ),
                'urlList'     => [ get_permalink( $post ), home_url( '/' ), home_url( '/en/' ) ],
            ] ),
        ] );
    },
    10,
    3
);
