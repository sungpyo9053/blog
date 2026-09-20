<?php
/** Isolated display-only contract doubles; no database or network. */
define( 'ABSPATH', __DIR__ );
$scenario = $argv[2];
function add_filter( ...$args ) {}
function get_post( $id ) {
 if ( $GLOBALS['scenario'] === 'missing' && $id === 773 ) { return null; }
 return (object) array( 'ID' => $id, 'post_type' => 'post', 'post_status' => $GLOBALS['scenario'] === 'draft' && $id === 773 ? 'draft' : 'publish', 'post_password' => $GLOBALS['scenario'] === 'password' && $id === 773 ? 'secret' : '' );
}
function has_category( $slug, $post ) { return ! in_array( $GLOBALS['scenario'], array( 'wrong-category', 'legacy' ), true ); }
function is_singular( $type ) { return $GLOBALS['scenario'] !== 'briefing'; }
function in_the_loop() { return $GLOBALS['scenario'] !== 'outside-loop'; }
function is_main_query() { return $GLOBALS['scenario'] !== 'secondary'; }
function is_feed() { return $GLOBALS['scenario'] === 'feed'; }
function get_the_ID() { return $GLOBALS['scenario'] === 'new-post' ? 777 : 768; }
function get_permalink( $post ) { return 'https://example.test/post-' . $post->ID . '/'; }
function get_the_title( $post ) { return '<unsafe> Lesson ' . $post->ID; }
function home_url( $path ) { return 'https://example.test' . $path; }
function esc_html( $value ) { return htmlspecialchars( $value, ENT_QUOTES, 'UTF-8' ); }
function esc_url( $value ) { return esc_html( $value ); }
if ( $scenario === 'rest' ) { define( 'REST_REQUEST', true ); }
require $argv[1];
echo json_encode( array( 'html' => huntlab_physical_learning_navigation( 'ORIGINAL' ), 'starts' => array_keys( huntlab_physical_starting_posts() ) ) );
