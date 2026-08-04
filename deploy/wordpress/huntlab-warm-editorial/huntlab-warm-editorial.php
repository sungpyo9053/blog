<?php
/**
 * Plugin Name: HuntLab Warm Editorial Theme
 * Description: Applies HuntLab's warm editorial palette without replacing the active WordPress theme.
 * Version: 1.0.0
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
