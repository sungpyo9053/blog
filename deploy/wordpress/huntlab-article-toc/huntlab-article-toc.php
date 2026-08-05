<?php
/**
 * Plugin Name: HuntLab Article Table of Contents
 * Description: Adds a warm, accessible H2/H3 table of contents to HuntLab posts.
 * Version: 1.1.4
 * Author: HuntLab
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Convert rendered post HTML into a short, safe summary sentence.
 *
 * @param string $html Source HTML.
 * @param int    $limit Maximum character count.
 * @return string
 */
function huntlab_article_summary_text( $html, $limit = 190 ) {
	$text = trim( preg_replace( '/\s+/u', ' ', wp_strip_all_tags( $html ) ) );
	if ( '' === $text ) {
		return '';
	}
	if ( function_exists( 'mb_strlen' ) && mb_strlen( $text, 'UTF-8' ) > $limit ) {
		return rtrim( mb_substr( $text, 0, $limit, 'UTF-8' ) ) . '…';
	}
	if ( ! function_exists( 'mb_strlen' ) && preg_match_all( '/./us', $text, $characters ) && count( $characters[0] ) > $limit ) {
		return rtrim( implode( '', array_slice( $characters[0], 0, $limit ) ) ) . '…';
	}
	if ( strlen( $text ) > $limit ) {
		return rtrim( substr( $text, 0, $limit ) ) . '…';
	}
	return $text;
}

/**
 * Build a reversible quick summary for older posts from content already shown.
 *
 * New pipeline posts include an explicit "핵심 요약" section, so this fallback
 * is only used when that authored section is absent.
 *
 * @param string $content  Anchored post content.
 * @param array  $sections Parsed H2/H3 sections.
 * @return string
 */
function huntlab_article_quick_summary( $content, $sections ) {
	if ( preg_match( '/<h2\b[^>]*>\s*(?:<[^>]+>\s*)*핵심 요약\s*(?:<\/[^>]+>\s*)*<\/h2>/iu', $content ) ) {
		return '';
	}

	$intro = $content;
	if ( preg_match( '/<h2\b/i', $content, $first_heading, PREG_OFFSET_CAPTURE ) ) {
		$intro = substr( $content, 0, $first_heading[0][1] );
	}
	preg_match_all( '/<p\b[^>]*>(.*?)<\/p>/is', $intro, $paragraph_matches );
	$paragraphs = array();
	foreach ( $paragraph_matches[1] as $paragraph ) {
		$text = huntlab_article_summary_text( $paragraph );
		if ( '' !== $text && strlen( $text ) >= 24 ) {
			$paragraphs[] = $text;
		}
	}

	$steps = array();
	foreach ( $sections as $section ) {
		if ( preg_match( '/^(?:핵심 요약|참고|함께 읽)/u', $section['title'] ) ) {
			continue;
		}
		$steps[] = $section['title'];
		if ( 3 === count( $steps ) ) {
			break;
		}
	}

	/*
	 * Older posts often begin with an H2, so there is no introductory paragraph.
	 * Do not request an automatic excerpt here: it applies content filters
	 * again and can leave a recursively generated summary with an empty value.
	 * Prefer a manual excerpt, then the first substantive paragraph in the post.
	 */
	$manual_excerpt = huntlab_article_summary_text( (string) get_post_field( 'post_excerpt', get_the_ID() ) );
	if ( '' === $manual_excerpt && empty( $paragraphs ) ) {
		preg_match_all( '/<p\b[^>]*>(.*?)<\/p>/is', $content, $content_paragraph_matches );
		foreach ( $content_paragraph_matches[1] as $paragraph ) {
			$text = huntlab_article_summary_text( $paragraph );
			if ( '' !== $text && strlen( $text ) >= 24 ) {
				$paragraphs[] = $text;
				break;
			}
		}
	}

	$what = isset( $paragraphs[0] ) ? $paragraphs[0] : $manual_excerpt;
	$why  = isset( $steps[0] )
		? '“' . $steps[0] . '”라는 문제 또는 판단 기준을 놓치지 않기 위해서입니다.'
		: '';
	$how_steps = array_slice( $steps, 1, 3 );
	if ( count( $how_steps ) < 2 ) {
		$how_steps = $steps;
	}

	if ( '' === $what || '' === $why || count( $steps ) < 2 ) {
		return '';
	}

	$how = implode( ' → ', $how_steps );
	return '<section class="huntlab-article-quick-summary" aria-labelledby="huntlab-quick-summary">'
		. '<h2 id="huntlab-quick-summary">20초 핵심 요약</h2>'
		. '<ul>'
		. '<li><strong>무엇</strong><span>' . esc_html( $what ) . '</span></li>'
		. '<li><strong>왜</strong><span>' . esc_html( $why ) . '</span></li>'
		. '<li><strong>어떻게</strong><span>' . esc_html( $how ) . ' 순서로 확인합니다.</span></li>'
		. '</ul></section>';
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
	$quick_summary = huntlab_article_quick_summary( $content, $sections );

	if ( ! preg_match( '/<h2\b/i', $content, $first_match, PREG_OFFSET_CAPTURE ) ) {
		return $quick_summary . $toc . $content;
	}
	$first_heading = $first_match[0][1];

	return substr( $content, 0, $first_heading ) . $quick_summary . $toc . substr( $content, $first_heading );
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
