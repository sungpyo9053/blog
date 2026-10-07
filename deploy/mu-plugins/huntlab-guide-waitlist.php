<?php
/**
 * Plugin Name: HuntLab Guide Waitlist
 * Description: "Get notified when the ROS 2 troubleshooting guide launches" form at the end of English posts
 * and the English hub. Validates demand before anything is sold. Emails stay in a private option and are used
 * for one launch email only. GET /huntlab/v1/guide-waitlist (editors only) returns the count.
 */

const HUNTLAB_WAITLIST_OPTION = 'huntlab_guide_waitlist';

function huntlab_waitlist_form(): string {
    if ( isset( $_GET['joined'] ) ) {
        return '<aside class="huntlab-waitlist"><p><strong>Thanks, you are on the list.</strong> '
            . 'You will get one email when the guide launches.</p></aside>';
    }
    $action = esc_url( admin_url( 'admin-post.php' ) );
    $back   = esc_attr( (string) wp_parse_url( get_permalink() ?: home_url( '/en/' ), PHP_URL_PATH ) );
    $policy = esc_url( home_url( '/privacy-policy/' ) );
    return <<<HTML
<aside class="huntlab-waitlist" aria-label="Guide waitlist">
<h2>ROS 2 troubleshooting guide (coming soon)</h2>
<p>A step-by-step diagnosis guide built from these measured runs: tf2 extrapolation errors, QoS mismatches,
discovery and colcon build problems, with the scripts to reproduce each check. Leave your email to hear when it launches.</p>
<form method="post" action="{$action}">
<input type="hidden" name="action" value="huntlab_waitlist">
<input type="hidden" name="back" value="{$back}">
<p style="position:absolute;left:-9999px" aria-hidden="true"><label>Leave empty <input type="text" name="website" tabindex="-1" autocomplete="off"></label></p>
<label for="huntlab-waitlist-email">Email</label>
<input id="huntlab-waitlist-email" type="email" name="email" required maxlength="190" autocomplete="email">
<button type="submit">Notify me</button>
<p><small>One launch email only, no newsletter. Ask and we delete it. <a href="{$policy}">Privacy policy</a>.</small></p>
</form>
</aside>
HTML;
}

add_filter(
    'the_content',
    static function ( string $content ): string {
        $hub = function_exists( 'huntlab_hub_page' ) ? huntlab_hub_page( 'en' ) : null;
        $on  = is_singular( 'hunt_en' ) || ( $hub && is_page( $hub->ID ) );
        return ( $on && in_the_loop() && is_main_query() ) ? $content . huntlab_waitlist_form() : $content;
    },
    16
);

$huntlab_waitlist_submit = static function (): void {
    $back = '/' . ltrim( (string) wp_parse_url( (string) ( $_POST['back'] ?? '/en/' ), PHP_URL_PATH ), '/' );
    // Honeypot filled or bad address: answer like success so bots learn nothing.
    $email = sanitize_email( wp_unslash( (string) ( $_POST['email'] ?? '' ) ) );
    $ip    = (string) ( $_SERVER['HTTP_CF_CONNECTING_IP'] ?? $_SERVER['REMOTE_ADDR'] ?? '' );
    $key   = 'huntlab_wl_' . md5( $ip );
    $tries = (int) get_transient( $key );
    if ( '' === (string) ( $_POST['website'] ?? '' ) && is_email( $email ) && $tries < 5 ) {
        set_transient( $key, $tries + 1, HOUR_IN_SECONDS );
        $list = get_option( HUNTLAB_WAITLIST_OPTION, [] );
        $addr = strtolower( $email );
        if ( ! isset( $list[ $addr ] ) && count( $list ) < 5000 ) {
            $list[ $addr ] = [ 'at' => wp_date( 'c', null, new DateTimeZone( 'Asia/Seoul' ) ), 'page' => $back ];
            update_option( HUNTLAB_WAITLIST_OPTION, $list, false );
        }
    }
    wp_safe_redirect( home_url( $back ) . '?joined=1#huntlab-waitlist-email' );
    exit;
};
add_action( 'admin_post_nopriv_huntlab_waitlist', $huntlab_waitlist_submit );
add_action( 'admin_post_huntlab_waitlist', $huntlab_waitlist_submit );

add_action(
    'rest_api_init',
    static function (): void {
        register_rest_route( 'huntlab/v1', '/guide-waitlist', [
            'methods'             => 'GET',
            'permission_callback' => static fn() => current_user_can( 'edit_posts' ),
            'callback'            => static fn() => [ 'count' => count( get_option( HUNTLAB_WAITLIST_OPTION, [] ) ) ],
        ] );
    }
);
