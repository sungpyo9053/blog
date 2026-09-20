<?php
/** Minimal WordPress doubles, not a substitute for a real theme/browser test. */
define( 'ABSPATH', __DIR__ );
$scenario = $argv[2];
$queries = array();
function add_filter( ...$args ) {}
function get_post( $id ) { return $GLOBALS['scenario'] === 'published-starts' ? (object) array( 'ID' => $id, 'post_type' => 'post', 'post_status' => 'publish', 'post_password' => '' ) : null; }
function has_category( $slug, $post ) { return true; }
function has_post_thumbnail( $post ) { return $GLOBALS['scenario'] === 'published-starts'; }
function get_the_post_thumbnail( $post, $size, $attrs ) { return '<img src="https://example.test/existing-diagram.png" width="1200" height="630" alt="기존 글 도식">'; }
function get_header() {}
function get_footer() {}
function is_category() { return in_array( $GLOBALS['scenario'], array( 'selected', 'missing-selected' ), true ); }
function get_queried_object() { return (object) array( 'slug' => $GLOBALS['scenario'] === 'selected' ? 'physical-ai-basics' : 'missing' ); }
function get_category_by_slug( $slug ) {
 if ( $GLOBALS['scenario'] === 'absent' || $slug !== 'physical-ai-basics' ) { return false; }
 return (object) array( 'term_id' => 901, 'count' => $GLOBALS['scenario'] === 'empty' ? 0 : 1 );
}
function get_query_var( $key ) { return $GLOBALS['scenario'] === 'page' && $key === 'page' ? 2 : 0; }
function esc_html( $value ) { return htmlspecialchars( (string) $value, ENT_QUOTES, 'UTF-8' ); }
function esc_url( $value ) { return esc_html( $value ); }
function plugins_url( $path, $file ) { return 'https://example.test/plugin/' . $path; }
function home_url( $path ) { return 'https://example.test' . $path; }
function single_cat_title( $separator, $echo ) { return 'Missing category'; }
function get_category_link( $id ) { return 'https://example.test/category/' . $id; }
function get_the_date( $format, $post ) { return '2026.09.16'; }
function hunt_news_reading_minutes( $post ) { return 5; }
function get_permalink( $post ) { return 'https://example.test/lesson/'; }
function get_the_title( $post ) { return '<script>unsafe()</script>'; }
function get_the_excerpt( $post ) { return '<b>Example</b>'; }
function wp_strip_all_tags( $value ) { return strip_tags( $value ); }
function wp_kses_post( $value ) { return $value; }
function paginate_links( $args ) { return 'PAGE=' . $args['current']; }
class WP_Query {
 public $posts;
 public $max_num_pages = 2;
 function __construct( $args ) {
  $GLOBALS['queries'][] = $args;
  $this->posts = $GLOBALS['scenario'] === 'empty' ? array() : array( (object) array( 'ID' => 1001 ) );
 }
 function have_posts() { return count( $this->posts ) > 0; }
}
ob_start();
require $argv[1];
$html = ob_get_clean();
echo json_encode( array( 'html' => $html, 'queries' => $queries ) );
