<?php
/**
 * Plugin Name: HuntLab In-article Ad
 * Description: AdSense in-article unit (slot 6038081617) after ~40% of top-level paragraphs in posts and hunt_en, plus ~75% on long posts.
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
        // Slots at ~40% and, for long posts (12+ paragraphs, benchmark median is 2 in-article), ~75%.
        $starts = array( max( 3, (int) floor( $n * 0.4 ) ) );
        if ( $n >= 12 ) {
            $starts[] = (int) floor( $n * 0.75 );
        }
        if ( $n >= 24 ) { // long calculator guides (5k+ chars): third slot near the end, benchmark median is 3
            $starts[1] = (int) floor( $n * 0.65 );
            $starts[]  = (int) floor( $n * 0.9 );
        }
        $placed = 0;
        $last   = -99;
        foreach ( $parts as $i => $part ) {
            $out .= $part;
            if ( $i === $n ) {
                break;
            }
            $out .= '</p>';
            // Only at top level: never inside a table, list, details, figure or script.
            // Not right before or right after a calculator/form either (accidental-click policy).
            // Two blocks back: calculators end with <p><script></p>, so the block before the caption holds the form.
            $near = substr( $parts[ $i + 1 ], 0, 600 ) . $part . ( $i > 0 ? $parts[ $i - 1 ] : '' );
            if ( $placed < count( $starts ) && $i + 1 >= $starts[ $placed ] && $i - $last >= 3 && ! preg_match( '/<(input|select|button|textarea|form|script)\b/i', $near ) && ! preg_match( '/<(table|ul|ol|details|figure|script|blockquote)\b(?:(?!<\/\1>).)*$/is', $out ) ) {
                $out .= $ad;
                $placed++;
                $last = $i;
            }
        }
        return $out;
    },
    20
);
