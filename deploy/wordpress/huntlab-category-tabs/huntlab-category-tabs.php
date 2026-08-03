<?php
/**
 * Plugin Name: HuntLab Category Tabs
 * Description: Adds fast category navigation for desktop and mobile visitors.
 * Version: 1.0.0
 * Author: HuntLab
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Return the visible HuntLab category navigation items.
 *
 * @return array<int, array{label:string,url:string,slug:string}>
 */
function huntlab_category_tabs_items() {
	$items = array(
		array(
			'label' => '전체',
			'url'   => home_url( '/' ),
			'slug'  => 'all',
		),
	);

	$categories = array(
		'tech'      => 'Tech',
		'ai'        => 'AI',
		'build-log' => 'Build Log',
		'economy'   => 'Economy',
		'society'   => 'Society',
		'hot-issue' => 'Hot Issue',
	);

	foreach ( $categories as $slug => $label ) {
		$category = get_category_by_slug( $slug );
		if ( ! $category || 0 === (int) $category->count ) {
			continue;
		}

		$category_url = get_category_link( $category->term_id );
		if ( is_wp_error( $category_url ) ) {
			continue;
		}

		$items[] = array(
			'label' => $label,
			'url'   => $category_url,
			'slug'  => $slug,
		);
	}

	return $items;
}

/**
 * Resolve the active item on archives and single posts.
 *
 * @return string
 */
function huntlab_category_tabs_active_slug() {
	if ( is_category() ) {
		$category = get_queried_object();
		return isset( $category->slug ) ? (string) $category->slug : '';
	}

	if ( is_single() ) {
		$post_categories = get_the_category();
		if ( $post_categories ) {
			return (string) $post_categories[0]->slug;
		}
	}

	return ( is_home() || is_front_page() ) ? 'all' : '';
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
	<nav id="huntlab-category-tabs" class="huntlab-category-tabs" aria-label="글 카테고리">
		<?php foreach ( huntlab_category_tabs_items() as $item ) : ?>
			<a class="huntlab-category-tabs__link<?php echo $active_slug === $item['slug'] ? ' is-active' : ''; ?>"
				href="<?php echo esc_url( $item['url'] ); ?>"
				<?php echo $active_slug === $item['slug'] ? 'aria-current="page"' : ''; ?>><?php echo esc_html( $item['label'] ); ?></a>
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
.huntlab-category-tabs{box-sizing:border-box;display:flex;gap:8px;background:#fff;z-index:999}.huntlab-category-tabs__link{box-sizing:border-box;display:block;border:1px solid #d9e0e7;border-radius:999px;padding:8px 13px;color:#2d3748;background:#fff;font-size:14px;font-weight:600;line-height:1.2;text-decoration:none;white-space:nowrap;transition:background-color .15s ease,border-color .15s ease,color .15s ease,transform .15s ease}.huntlab-category-tabs__link:hover,.huntlab-category-tabs__link:focus-visible{border-color:#2563eb;color:#1d4ed8;transform:translateY(-1px)}.huntlab-category-tabs__link.is-active{border-color:#2563eb;background:#2563eb;color:#fff}@media(min-width:1280px){.huntlab-category-tabs{position:fixed;left:14px;top:50%;transform:translateY(-50%);flex-direction:column;width:116px;padding:10px;border:1px solid #e5e7eb;border-radius:16px;box-shadow:0 10px 28px rgba(15,23,42,.12)}.huntlab-category-tabs__link{text-align:center;border-radius:10px}}@media(max-width:1279px){.huntlab-category-tabs{position:sticky;top:0;overflow-x:auto;padding:9px 14px;border-bottom:1px solid #e5e7eb;box-shadow:0 4px 12px rgba(15,23,42,.07);scrollbar-width:none}.huntlab-category-tabs::-webkit-scrollbar{display:none}body.admin-bar .huntlab-category-tabs{top:32px}}@media(max-width:782px){body.admin-bar .huntlab-category-tabs{top:46px}.huntlab-category-tabs{padding-inline:12px}.huntlab-category-tabs__link{font-size:13px;padding:8px 12px}}
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
	document.addEventListener('DOMContentLoaded',function(){var nav=document.getElementById('huntlab-category-tabs');var header=document.querySelector('#masthead,.site-header');if(nav&&header&&header.parentNode){header.insertAdjacentElement('afterend',nav);}});
	</script>
	<?php
}
add_action( 'wp_footer', 'huntlab_category_tabs_script', 30 );
