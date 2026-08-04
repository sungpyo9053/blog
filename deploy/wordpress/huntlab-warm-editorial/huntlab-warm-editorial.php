<?php
/**
 * Plugin Name: HuntLab Warm Editorial Theme
 * Description: Applies HuntLab's warm editorial palette without replacing the active WordPress theme.
 * Version: 1.0.1
 * Author: HuntLab
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Load the visual layer after the active theme so it can remain small and reversible.
 */
function huntlab_warm_editorial_enqueue_styles() {
	$stylesheet_path = plugin_dir_path( __FILE__ ) . 'assets/warm-editorial.css';

	wp_enqueue_style(
		'huntlab-warm-editorial',
		plugins_url( 'assets/warm-editorial.css', __FILE__ ),
		array(),
		(string) filemtime( $stylesheet_path )
	);
}
add_action( 'wp_enqueue_scripts', 'huntlab_warm_editorial_enqueue_styles', 100 );

/**
 * The existing HuntLab navigation and brand plugins print their styles inline.
 * Keep these two brand overrides last without duplicating the full stylesheet.
 */
function huntlab_warm_editorial_late_brand_overrides() {
	?>
	<style id="huntlab-warm-editorial-late-overrides">
		.huntlab-category-tabs{background:rgba(255,250,242,.97)!important;border-color:#e6d9ca!important;box-shadow:0 16px 42px rgba(86,66,45,.09)!important}
		.huntlab-category-tabs__link{background:#fffdf9!important;border-color:#e6d9ca!important;color:#4d463f!important}
		.huntlab-category-tabs__link:hover,.huntlab-category-tabs__link:focus-visible{background:#f9eee6!important;border-color:#a95f49!important;color:#874735!important}
		.huntlab-category-tabs__link.is-active{background:#a95f49!important;border-color:#a95f49!important;color:#fffdf9!important}
		.site-branding .brand::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 96 40'%3E%3Cg fill='%23292621'%3E%3Cpath d='M24 13C34 9 61 9 70 14c4 2 7 1 12-4 1 7-2 11-9 14v6h-7l-1-6H36l-2 7h-7l1-9c-4-2-6-5-6-8l2-1Z'/%3E%3Cpath d='M25 13c-2-7-11-9-17-3l-5 4 6 3c-1 7 5 11 13 8l7-5-4-7Z'/%3E%3Cpath d='M14 8c-6 3-5 12 2 15 3-5 5-11 3-14l-5-1Z' fill='%23a95f49'/%3E%3Ccircle cx='10' cy='13' r='1.4' fill='%23fffaf2'/%3E%3C/g%3E%3C/svg%3E")!important}
	</style>
	<?php
}
add_action( 'wp_head', 'huntlab_warm_editorial_late_brand_overrides', 100 );
