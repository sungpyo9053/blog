<?php
define( 'ABSPATH', __DIR__ );
$scenario = $argv[2];
if ( 'rest' === $scenario ) { define( 'REST_REQUEST', true ); }
function add_action( ...$args ) {}
function add_filter( ...$args ) {}
function is_admin() { return 'admin' === $GLOBALS['scenario']; }
function is_feed() { return 'feed' === $GLOBALS['scenario']; }
function is_singular( $type ) { return 'briefing' !== $GLOBALS['scenario']; }
function in_the_loop() { return 'outside-loop' !== $GLOBALS['scenario']; }
function is_main_query() { return 'secondary' !== $GLOBALS['scenario']; }
function has_category( $slugs, $post ) { return 'legacy' !== $GLOBALS['scenario']; }
function hunt_news_is_verified_case( $post ) { return 'verified-case' === $GLOBALS['scenario']; }
function get_post() {
 if ( 'missing' === $GLOBALS['scenario'] ) { return null; }
 return (object) array( 'post_type'=>'post', 'post_status'=>'draft' === $GLOBALS['scenario'] ? 'draft':'publish', 'post_password'=>'password' === $GLOBALS['scenario'] ? 'private':'' );
}
function get_post_datetime( $post, $field ) {
 if ( 'missing-date' === $GLOBALS['scenario'] ) { return false; }
 return new DateTimeImmutable( 'date' === $field || 'same-date' === $GLOBALS['scenario'] ? '2026-09-17T10:01:02+09:00':'2026-09-20T14:01:02+09:00' );
}
function esc_attr( $s ) { return htmlspecialchars( $s, ENT_QUOTES, 'UTF-8' ); }
function esc_html( $s ) { return esc_attr( $s ); }
function esc_url( $s ) { return esc_attr( $s ); }
function home_url( $path ) { return 'https://example.test' . $path; }
require $argv[1];
$first = huntlab_physical_article_meta( '<p>ORIGINAL &amp; RAW</p>' );
echo json_encode( array( 'html'=>$first, 'twice'=>huntlab_physical_article_meta( $first ) ) );
