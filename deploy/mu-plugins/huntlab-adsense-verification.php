<?php
/**
 * Plugin Name: HuntLab AdSense
 * Description: AdSense ownership meta tag + Auto ads script (formats are chosen in the AdSense UI).
 */

add_action(
    'wp_head',
    static function (): void {
        echo '<meta name="google-adsense-account" content="ca-pub-6970683716237249">' . "\n";
        // No ads on short briefings (thin-content policy risk) or for logged-in staff (invalid traffic).
        if ( is_user_logged_in() || is_singular( 'hunt_briefing' ) || is_404() || is_search() ) {
            return;
        }
        echo '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6970683716237249" crossorigin="anonymous"></script>' . "\n";
    },
    1
);
