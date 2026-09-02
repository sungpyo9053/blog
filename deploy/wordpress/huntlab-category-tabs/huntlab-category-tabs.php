<?php
/**
 * Plugin Name: Hunt News Category Tabs
 * Description: Adds fast briefing navigation for Hunt News readers.
 * Version: 4.0.0
 * Author: Hunt News
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Return the visible Hunt News briefing navigation items.
 *
 * @return array<int, array{label:string,url:string,slug:string,meta:string}>
 */
function huntlab_category_tabs_items() {
	$latest_briefings = get_posts(
		array(
			'post_type'      => 'hunt_briefing',
			'post_status'    => 'publish',
			'posts_per_page' => 1,
			'orderby'        => 'date',
			'order'          => 'DESC',
			'no_found_rows'  => true,
		)
	);
	$today_url = $latest_briefings ? get_permalink( $latest_briefings[0] ) : home_url( '/#hunt-news-briefing-board' );
	$archive_url = get_post_type_archive_link( 'hunt_briefing' );
	if ( ! $archive_url ) {
		$archive_url = home_url( '/briefing/' );
	}
	$weekly_category = get_category_by_slug( 'weekly-tech-review' );
	$weekly_url = $weekly_category ? get_category_link( $weekly_category->term_id ) : home_url( '/category/weekly-tech-review/' );
	$explainer_category = get_category_by_slug( 'technical-explainer' );
	$explainer_url = $explainer_category ? get_category_link( $explainer_category->term_id ) : home_url( '/category/technical-explainer/' );

	$items = array();
	if ( $explainer_category && 0 < (int) $explainer_category->count ) {
		$items[] = array(
			'label' => '기술 해설',
			'url'   => $explainer_url,
			'slug'  => 'explainer',
			'meta'  => '깊이 읽기',
		);
	}
	if ( $weekly_category && 0 < (int) $weekly_category->count ) {
		$items[] = array(
			'label' => '주간 회고',
			'url'   => $weekly_url,
			'slug'  => 'weekly',
			'meta'  => '매주',
		);
	}
	$items[] = array(
		'label' => '오늘 브리핑',
		'url'   => $today_url,
		'slug'  => 'today',
		'meta'  => '최신',
	);
	$items[] = array(
		'label' => '날짜 아카이브',
		'url'   => $archive_url,
		'slug'  => 'archive',
		'meta'  => '날짜별',
	);
	$items[] = array(
		'label' => '이용 가이드',
		'url'   => home_url( '/about/' ),
		'slug'  => 'about',
		'meta'  => '편집 기준',
	);
	return $items;
}

/**
 * Resolve the active item on archives and single posts.
 *
 * @return string
 */
function huntlab_category_tabs_active_slug() {
	if ( is_category( 'technical-explainer' ) || ( is_singular( 'post' ) && has_category( 'technical-explainer' ) ) ) {
		return 'explainer';
	}
	if ( is_category( 'weekly-tech-review' ) || ( is_singular( 'post' ) && has_category( 'weekly-tech-review' ) ) ) {
		return 'weekly';
	}
	if ( is_post_type_archive( 'hunt_briefing' ) ) {
		return 'archive';
	}
	if ( is_page( 'about' ) || is_page( 'editorial-policy' ) ) {
		return 'about';
	}

	return ( is_home() || is_front_page() || is_singular( 'hunt_briefing' ) ) ? 'today' : '';
}

/**
 * Render category navigation once near the top of the page.
 */
function huntlab_render_category_tabs() {
	if ( is_admin() ) {
		return;
	}

	$active_slug = huntlab_category_tabs_active_slug();
	?>
	<nav id="huntlab-category-tabs" class="huntlab-category-tabs" aria-label="Hunt News 콘텐츠 탐색">
		<?php foreach ( huntlab_category_tabs_items() as $item ) :
			$aria_label = $item['label'] . ', ' . $item['meta'];
			?>
			<a class="huntlab-category-tabs__link<?php echo $active_slug === $item['slug'] ? ' is-active' : ''; ?>"
				href="<?php echo esc_url( $item['url'] ); ?>"
				data-hunt-news-nav="<?php echo esc_attr( $item['slug'] ); ?>"
				aria-label="<?php echo esc_attr( $aria_label ); ?>"
				<?php echo $active_slug === $item['slug'] ? 'aria-current="page"' : ''; ?>>
				<span class="huntlab-category-tabs__label"><?php echo esc_html( $item['label'] ); ?></span>
				<span class="huntlab-category-tabs__meta" aria-hidden="true">
					<span class="huntlab-category-tabs__count"><?php echo esc_html( $item['meta'] ); ?></span>
				</span>
			</a>
		<?php endforeach; ?>
	</nav>
	<?php
}
add_action( 'wp_body_open', 'huntlab_render_category_tabs', 20 );

/**
 * Keep the navigation dependency-free and responsive.
 */
function huntlab_category_tabs_styles() {
	$css = <<<'CSS'
	.huntlab-category-tabs{box-sizing:border-box;display:flex;gap:7px;justify-content:center;position:sticky;top:0;overflow-x:auto;width:100vw;margin-left:calc(50% - 50vw);padding:9px max(16px,calc((100vw - 1240px)/2));border-bottom:1px solid #e5e7eb;background:#fff;box-shadow:0 4px 12px rgba(15,23,42,.07);scrollbar-width:none;z-index:999}.huntlab-category-tabs::-webkit-scrollbar{display:none}.huntlab-category-tabs__link{box-sizing:border-box;display:flex;align-items:center;justify-content:center;gap:4px;min-height:40px;border:1px solid #d9e0e7;border-radius:9px;padding:7px 12px;color:#2d3748;background:#fff;font-size:13px;font-weight:700;line-height:1.2;text-decoration:none;white-space:nowrap;transition:background-color .15s ease,border-color .15s ease,color .15s ease,transform .15s ease}.huntlab-category-tabs__link:hover,.huntlab-category-tabs__link:focus-visible{border-color:#2563eb;color:#1d4ed8;transform:translateY(-1px)}.huntlab-category-tabs__link.is-active{border-color:#2563eb;background:#2563eb;color:#fff}.huntlab-category-tabs__label{min-width:0}.huntlab-category-tabs__meta{display:inline-flex;align-items:center;justify-content:center;gap:3px}.huntlab-category-tabs__count{font-size:11px;font-weight:600;font-variant-numeric:tabular-nums;opacity:.72}.huntlab-category-tabs__new{display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;border-radius:999px;background:#a95f49;color:#fff;font-size:9px;font-weight:800;line-height:1}.huntlab-category-tabs__link.is-active .huntlab-category-tabs__count{opacity:.9}.huntlab-category-tabs__link.is-active .huntlab-category-tabs__new{background:#fff;color:#a95f49}body.admin-bar .huntlab-category-tabs{top:32px}@media(max-width:782px){body.admin-bar .huntlab-category-tabs{top:46px}.huntlab-category-tabs{justify-content:flex-start;padding-inline:12px}.huntlab-category-tabs__link{font-size:13px;min-height:44px;padding:8px 12px}}
CSS;
	echo '<style id="huntlab-category-tabs-css">' . $css . '</style>'; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
}
add_action( 'wp_head', 'huntlab_category_tabs_styles', 30 );

/**
 * Move the navigation directly below the Kadence header.
 */
function huntlab_category_tabs_script() {
	?>
	<script id="huntlab-category-tabs-js">
	document.addEventListener('DOMContentLoaded',function(){var nav=document.getElementById('huntlab-category-tabs');var intro=document.getElementById('huntlab-home-intro');var header=document.querySelector('#masthead,.site-header');if(nav&&intro&&intro.parentNode){intro.insertAdjacentElement('afterend',nav);}else if(nav&&header&&header.parentNode){header.insertAdjacentElement('afterend',nav);}});
	</script>
	<?php
}
add_action( 'wp_footer', 'huntlab_category_tabs_script', 30 );

/**
 * Preserve old archive links while consolidating legacy technical categories.
 */
function hunt_news_redirect_legacy_categories() {
	if ( ! is_category() ) {
		return;
	}

	$legacy_slugs = array(
		'tech',
		'ai',
		'ml-algorithms',
		'harness-engineering',
		'system-architecture',
		'build-log',
	);
	$category     = get_queried_object();
	$slug         = isset( $category->slug ) ? (string) $category->slug : '';

	if ( ! in_array( $slug, $legacy_slugs, true ) ) {
		return;
	}

	$it_category = get_category_by_slug( 'it' );
	if ( ! $it_category ) {
		return;
	}

	$target = get_category_link( $it_category->term_id );
	if ( ! is_wp_error( $target ) ) {
		wp_safe_redirect( $target, 301 );
		exit;
	}
}
add_action( 'template_redirect', 'hunt_news_redirect_legacy_categories', 10 );
