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
        // Ad blocking recovery message (AdSense > Privacy & messaging, published 2026-11-19). Tag copied verbatim from the AdSense UI.
        echo <<<'HTML'
<script async src="https://fundingchoicesmessages.google.com/i/pub-6970683716237249?ers=1"></script><script>(function() {function signalGooglefcPresent() {if (!window.frames['googlefcPresent']) {if (document.body) {const iframe = document.createElement('iframe'); iframe.style = 'width: 0; height: 0; border: none; z-index: -1000; left: -1000px; top: -1000px;'; iframe.style.display = 'none'; iframe.name = 'googlefcPresent'; document.body.appendChild(iframe);} else {setTimeout(signalGooglefcPresent, 0);}}}signalGooglefcPresent();})();</script>

HTML;
    },
    1
);
