<?php
/**
 * Plugin Name: HuntLab In-article Ad
 * Description: One AdSense in-article unit (slot 6038081617) after ~40% of top-level paragraphs in posts and hunt_en.
 */

add_filter(
    'the_content',
    static function ( string $content ): string {
        // Same exclusions as huntlab-adsense-verification.php (no ads for staff, briefings, 404, search).
        if ( is_admin() || is_feed() || is_user_logged_in() || ! is_singular( array( 'post', 'hunt_en' ) ) || ! in_the_loop() || ! is_main_query() ) {
            return $content;
        }
        $parts = explode( '</p>', $content );
        $n     = count( $parts ) - 1;
        if ( $n < 6 ) { // short posts: policy risk of ad-heavy thin pages
            return $content;
        }
        $ad = '<ins class="adsbygoogle" style="display:block;text-align:center;margin:1.5em 0" data-ad-layout="in-article" data-ad-format="fluid" data-ad-client="ca-pub-6970683716237249" data-ad-slot="6038081617"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({});</script>';
        $out   = '';
        $done  = false;
        $start = max( 3, (int) floor( $n * 0.4 ) );
        foreach ( $parts as $i => $part ) {
            $out .= $part;
            if ( $i === $n ) {
                break;
            }
            $out .= '</p>';
            // Only at top level: never inside a table, list, details, figure or script.
            // Not right before a calculator/form either (accidental-click policy).
            $next = substr( $parts[ $i + 1 ], 0, 600 );
            if ( ! $done && $i + 1 >= $start && ! preg_match( '/<(input|select|button|textarea|form|script)\b/i', $next ) && ! preg_match( '/<(table|ul|ol|details|figure|script|blockquote)\b(?:(?!<\/\1>).)*$/is', $out ) ) {
                $out .= $ad;
                $done = true;
            }
        }
        return $out;
    },
    20
);
