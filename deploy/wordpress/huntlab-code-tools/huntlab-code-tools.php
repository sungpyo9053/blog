<?php
/**
 * Plugin Name: HuntLab Code Tools
 * Description: Accessible copy and selection controls for article code examples.
 * Version: 1.0.0
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
function huntlab_code_tools_assets() {
	if ( ! is_singular( 'post' ) ) { return; }
	foreach ( array( 'css', 'js' ) as $extension ) {
		$relative = 'assets/code-tools.' . $extension;
		$version = (string) filemtime( plugin_dir_path( __FILE__ ) . $relative );
		$url = plugins_url( $relative, __FILE__ );
		if ( 'css' === $extension ) {
			wp_enqueue_style( 'huntlab-code-tools', $url, array(), $version );
		} else {
			wp_enqueue_script( 'huntlab-code-tools', $url, array(), $version, true );
		}
	}
}
add_action( 'wp_enqueue_scripts', 'huntlab_code_tools_assets', 110 );
