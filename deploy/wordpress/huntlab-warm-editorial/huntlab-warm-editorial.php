<?php
/**
 * Plugin Name: HuntLab Warm Editorial Theme
 * Description: Applies HuntLab's warm editorial palette without replacing the active WordPress theme.
 * Version: 1.1.0
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
 * Give the posts index a quiet editorial introduction without changing the
 * active theme or the layout of article pages.
 */
function huntlab_warm_editorial_home_intro() {
	if ( is_admin() || ! ( is_home() || is_front_page() ) ) {
		return;
	}
	?>
	<section id="huntlab-home-intro" class="huntlab-home-intro" aria-labelledby="huntlab-home-intro-title">
		<div class="huntlab-home-intro__copy">
			<p class="huntlab-home-intro__eyebrow">HuntLab · 직접 해보고 기록하는 기술 블로그</p>
			<h1 id="huntlab-home-intro-title">복잡한 기술을,<br>오래 써먹을 수 있게.</h1>
			<p class="huntlab-home-intro__description">실행 결과와 실패 기록을 바탕으로 AI, 개발, 클라우드 운영에서 실제로 필요한 판단을 정리합니다.</p>
			<ul class="huntlab-home-intro__promises" aria-label="HuntLab 콘텐츠 원칙">
				<li>직접 실행</li>
				<li>실패도 기록</li>
				<li>운영 판단까지</li>
			</ul>
		</div>
		<div class="huntlab-home-intro__dog" aria-hidden="true">
			<span class="huntlab-home-intro__dog-body"></span>
			<span class="huntlab-home-intro__dog-head"></span>
			<span class="huntlab-home-intro__dog-ear"></span>
			<span class="huntlab-home-intro__dog-tail"></span>
		</div>
	</section>
	<script id="huntlab-home-intro-position">
	document.addEventListener('DOMContentLoaded',function(){var intro=document.getElementById('huntlab-home-intro');var main=document.querySelector('#main,main.site-main');if(intro&&main&&main.parentNode){main.parentNode.insertBefore(intro,main);}});
	</script>
	<?php
}
add_action( 'wp_body_open', 'huntlab_warm_editorial_home_intro', 25 );

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
