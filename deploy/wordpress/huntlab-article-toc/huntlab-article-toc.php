<?php
/**
 * Plugin Name: HuntLab Article Table of Contents
 * Description: Adds a warm, accessible H2/H3 table of contents to HuntLab posts.
 * Version: 1.0.1
 * Author: HuntLab
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Add stable section anchors and build the navigation from the rendered post.
 *
 * @param string $content Post content.
 * @return string
 */
function huntlab_article_toc_content( $content ) {
	if ( is_admin() || ! is_singular( 'post' ) || ! in_the_loop() || ! is_main_query() ) {
		return $content;
	}

	$sections = array();
	$used_ids = array();
	$index    = 0;
	$pattern  = '/<h([23])([^>]*)>(.*?)<\/h\1>/is';

	$content = preg_replace_callback(
		$pattern,
		function ( $matches ) use ( &$sections, &$used_ids, &$index ) {
			$level      = (int) $matches[1];
			$attributes = $matches[2];
			$inner_html = $matches[3];
			$title      = trim( wp_strip_all_tags( $inner_html ) );

			if ( '' === $title ) {
				return $matches[0];
			}

			$index++;
			$has_id = preg_match( "/\sid=([\"'])([^\"']+)\\1/i", $attributes, $id_match );
			if ( $has_id ) {
				$base_id = sanitize_html_class( $id_match[2] );
			} else {
				$base_id = 'huntlab-section-' . $index;
			}
			$base_id = $base_id ? $base_id : 'huntlab-section-' . $index;
			$id      = $base_id;
			$suffix  = 2;
			while ( isset( $used_ids[ $id ] ) ) {
				$id = $base_id . '-' . $suffix;
				$suffix++;
			}
			$used_ids[ $id ] = true;

			if ( $has_id ) {
				$attributes = preg_replace(
					"/\sid=([\"'])([^\"']+)\\1/i",
					' id="' . esc_attr( $id ) . '"',
					$attributes,
					1
				);
			} else {
				$attributes .= ' id="' . esc_attr( $id ) . '"';
			}
			$sections[] = array(
				'level' => $level,
				'id'    => $id,
				'title' => $title,
			);

			return '<h' . $level . $attributes . '>' . $inner_html . '</h' . $level . '>';
		},
		$content
	);

	if ( count( $sections ) < 2 ) {
		return $content;
	}

	$items = '';
	foreach ( $sections as $section ) {
		$items .= sprintf(
			'<li class="huntlab-article-toc__item huntlab-article-toc__item--h%d"><a href="#%s">%s</a></li>',
			$section['level'],
			esc_attr( $section['id'] ),
			esc_html( $section['title'] )
		);
	}

	$toc = '<aside class="huntlab-article-toc" aria-label="이 글의 목차">'
		. '<details open><summary>한눈에 보기</summary>'
		. '<nav aria-label="글 섹션"><ol>' . $items . '</ol></nav>'
		. '</details></aside>';

	if ( ! preg_match( '/<h2\b/i', $content, $first_match, PREG_OFFSET_CAPTURE ) ) {
		return $toc . $content;
	}
	$first_heading = $first_match[0][1];

	return substr( $content, 0, $first_heading ) . $toc . substr( $content, $first_heading );
}
add_filter( 'the_content', 'huntlab_article_toc_content', 20 );

/**
 * Load the small navigation layer only on posts.
 */
function huntlab_article_toc_assets() {
	if ( ! is_singular( 'post' ) ) {
		return;
	}
	$css_path = plugin_dir_path( __FILE__ ) . 'assets/article-toc.css';
	$js_path  = plugin_dir_path( __FILE__ ) . 'assets/article-toc.js';
	wp_enqueue_style(
		'huntlab-article-toc',
		plugins_url( 'assets/article-toc.css', __FILE__ ),
		array(),
		(string) filemtime( $css_path )
	);
	wp_enqueue_script(
		'huntlab-article-toc',
		plugins_url( 'assets/article-toc.js', __FILE__ ),
		array(),
		(string) filemtime( $js_path ),
		true
	);
}
add_action( 'wp_enqueue_scripts', 'huntlab_article_toc_assets', 100 );
