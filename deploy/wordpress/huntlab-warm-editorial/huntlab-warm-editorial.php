<?php
/**
 * Plugin Name: Hunt News Warm Editorial Theme
 * Description: Applies Hunt News's approachable editorial layout without replacing the active WordPress theme.
 * Version: 6.0.0
 * Author: Hunt News
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

/** Register one public briefing archive entry per completed 02:00 run. */
function hunt_news_register_briefing_type() {
	register_post_type(
		'hunt_briefing',
		array(
			'labels' => array( 'name' => '매일 브리핑', 'singular_name' => '매일 브리핑' ),
			'public' => true, 'show_in_rest' => true, 'has_archive' => 'briefing',
			'rewrite' => array( 'slug' => 'briefing', 'with_front' => false ),
			'supports' => array( 'title', 'editor', 'excerpt' ),
			'menu_icon' => 'dashicons-calendar-alt',
		)
	);
	if ( 'v1' !== get_option( 'hunt_news_briefing_rewrite_version' ) ) {
		flush_rewrite_rules( false );
		update_option( 'hunt_news_briefing_rewrite_version', 'v1', false );
	}
}
add_action( 'init', 'hunt_news_register_briefing_type' );

/**
 * Build search metadata from the evidence-backed daily analysis while keeping
 * the visible report title and date archive stable.
 *
 * @return array{title:string,description:string}
 */
function hunt_news_briefing_search_metadata() {
	if ( ! is_singular( 'hunt_briefing' ) ) {
		return array( 'title' => '', 'description' => '' );
	}

	$post_id  = get_queried_object_id();
	$manifest = get_post_meta( $post_id, '_hunt_news_briefing_manifest', true );
	$analysis = is_array( $manifest ) && isset( $manifest['analysis'] ) && is_array( $manifest['analysis'] ) ? $manifest['analysis'] : array();
	$keywords = array();
	foreach ( array_slice( (array) ( $analysis['keywords'] ?? array() ), 0, 3 ) as $keyword ) {
		$name = sanitize_text_field( (string) ( $keyword['keyword'] ?? '' ) );
		if ( '' !== $name && ! in_array( $name, $keywords, true ) ) {
			$keywords[] = $name;
		}
	}

	$date        = get_the_date( 'Y-m-d', $post_id );
	$title       = $keywords ? implode( '·', $keywords ) . ' | ' . $date . ' 기술 브리핑 - Hunt News' : '';
	$headline    = sanitize_text_field( (string) ( $analysis['headline'] ?? '' ) );
	$summary     = sanitize_text_field( (string) ( $analysis['summary'] ?? '' ) );
	$description = '';
	if ( '' !== $headline ) {
		$description = '오늘의 핵심: ' . rtrim( $headline, ".。!? " ) . '. ';
	}
	if ( '' !== $summary ) {
		$description .= wp_html_excerpt( $summary, 85, '…' );
	}
	if ( '' !== $description ) {
		$description = trim( $description ) . ' 근거와 개발자 행동을 정리했습니다.';
	}

	return array( 'title' => $title, 'description' => $description );
}

/** Keep the homepage search promise aligned with the original editorial product. */
function hunt_news_home_search_metadata() {
	if ( ! ( is_home() || is_front_page() ) ) {
		return array( 'title' => '', 'description' => '' );
	}
	return array(
		'title'       => 'AI·개발 기술 해설과 실무 판단 - Hunt News',
		'description' => 'AI와 개발 기술의 변경점을 공식 원문, 비교, 예제와 실패 조건으로 검증해 실제 적용 여부를 판단할 수 있게 설명합니다. 일일 브리핑과 주간 회고도 제공합니다.',
	);
}

/** Keep automated daily report archives public but out of the searchable article corpus. */
function hunt_news_briefing_robots( $robots ) {
	if ( is_post_type_archive( 'hunt_briefing' ) || is_singular( 'hunt_briefing' ) ) {
		$robots['noindex'] = true;
		$robots['follow']  = true;
	}
	return $robots;
}
add_filter( 'wp_robots', 'hunt_news_briefing_robots', 20 );

/** Mirror the briefing robots contract into AIOSEO, which suppresses Core output. */
function hunt_news_briefing_aioseo_robots( $robots ) {
	if ( is_post_type_archive( 'hunt_briefing' ) || is_singular( 'hunt_briefing' ) ) {
		unset( $robots['index'], $robots['nofollow'] );
		$robots['noindex'] = 'noindex';
		$robots['follow']  = 'follow';
	}
	return $robots;
}
add_filter( 'aioseo_robots_meta', 'hunt_news_briefing_aioseo_robots', 20 );

/** Keep noindexed briefing reports out of AIOSEO discovery sitemaps. */
function hunt_news_briefing_aioseo_sitemap_indexes( $indexes ) {
	return array_values(
		array_filter(
			(array) $indexes,
			function ( $index ) {
				$location = is_array( $index ) ? (string) ( $index['loc'] ?? '' ) : '';
				return false === strpos( $location, '/hunt_briefing-sitemap' );
			}
		)
	);
}
add_filter( 'aioseo_sitemap_indexes', 'hunt_news_briefing_aioseo_sitemap_indexes', 20 );

function hunt_news_briefing_aioseo_sitemap_posts( $entries, $post_type ) {
	return 'hunt_briefing' === $post_type ? array() : $entries;
}
add_filter( 'aioseo_sitemap_posts', 'hunt_news_briefing_aioseo_sitemap_posts', 20, 2 );

function hunt_news_briefing_aioseo_sitemap_archives( $entries ) {
	return array_values(
		array_filter(
			(array) $entries,
			function ( $entry ) {
				$location = is_array( $entry ) ? (string) ( $entry['loc'] ?? '' ) : '';
				return false === strpos( $location, '/briefing/' );
			}
		)
	);
}
add_filter( 'aioseo_sitemap_post_archives', 'hunt_news_briefing_aioseo_sitemap_archives', 20 );

/** Use a keyword-rich title only in document/search metadata. */
function hunt_news_briefing_search_title( $title ) {
	$home_metadata = hunt_news_home_search_metadata();
	if ( '' !== $home_metadata['title'] ) {
		return $home_metadata['title'];
	}
	$metadata = hunt_news_briefing_search_metadata();
	return '' !== $metadata['title'] ? $metadata['title'] : $title;
}
add_filter( 'pre_get_document_title', 'hunt_news_briefing_search_title', 20 );
add_filter( 'aioseo_title', 'hunt_news_briefing_search_title', 20 );

/** Use the analysis summary as the briefing search snippet. */
function hunt_news_briefing_search_description( $description ) {
	$home_metadata = hunt_news_home_search_metadata();
	if ( '' !== $home_metadata['description'] ) {
		return $home_metadata['description'];
	}
	$metadata = hunt_news_briefing_search_metadata();
	return '' !== $metadata['description'] ? $metadata['description'] : $description;
}
add_filter( 'aioseo_description', 'hunt_news_briefing_search_description', 20 );

/** Mark the report-first surfaces without affecting legacy article URLs. */
function hunt_news_briefing_body_class( $classes ) {
	if ( is_home() || is_front_page() || is_post_type_archive( 'hunt_briefing' ) || is_singular( 'hunt_briefing' ) ) {
		$classes[] = 'hunt-news-briefing-mode';
	}
	return $classes;
}
add_filter( 'body_class', 'hunt_news_briefing_body_class' );

/**
 * Return all public daily reports grouped by local calendar month.
 *
 * @return array<string, array<int, WP_Post>>
 */
function hunt_news_briefing_archive_months() {
	$months = array();
	$posts  = get_posts(
		array(
			'post_type'              => 'hunt_briefing',
			'post_status'            => 'publish',
			'posts_per_page'         => 400,
			'orderby'                => 'date',
			'order'                  => 'DESC',
			'no_found_rows'          => true,
			'update_post_meta_cache' => false,
		)
	);
	foreach ( $posts as $post ) {
		$key = get_the_date( 'Y.m', $post );
		$months[ $key ][] = $post;
	}
	$current_datetime = current_datetime();
	$current_month    = $current_datetime->format( 'Y.m' );
	$tomorrow_month   = $current_datetime->modify( '+1 day' )->format( 'Y.m' );
	if ( $tomorrow_month !== $current_month && ! isset( $months[ $tomorrow_month ] ) ) {
		$months = array( $tomorrow_month => array() ) + $months;
	}
	return $months;
}

/** Render the primary month/date navigation for daily reports. */
function hunt_news_render_briefing_navigation() {
	$months   = hunt_news_briefing_archive_months();
	$current  = is_singular( 'hunt_briefing' ) ? get_queried_object_id() : 0;
	$first_id = 0;
	foreach ( $months as $posts ) {
		if ( $posts ) {
			$first_id = $posts[0]->ID;
			break;
		}
	}
	$active_id = $current ? $current : $first_id;
	?>
	<aside id="hunt-news-date-nav" class="hunt-news-date-nav" aria-label="날짜별 Hunt News 브리핑">
		<div class="hunt-news-date-nav__heading">
			<div><span>HUNT ARCHIVE</span><strong>매일 브리핑</strong></div>
			<button type="button" class="hunt-news-date-nav__toggle" aria-expanded="false" aria-controls="hunt-news-date-months">날짜 선택</button>
		</div>
		<div id="hunt-news-date-months" class="hunt-news-date-nav__months">
			<?php if ( ! $months ) : ?>
				<p class="hunt-news-date-nav__empty">첫 브리핑이 발행되면 날짜가 여기에 쌓입니다.</p>
			<?php endif; ?>
			<?php foreach ( $months as $month => $posts ) :
				$contains_active = in_array( $active_id, wp_list_pluck( $posts, 'ID' ), true );
				?>
				<details<?php echo $contains_active ? ' open' : ''; ?>>
					<summary>Hunt News [<?php echo esc_html( $month ); ?>]</summary>
					<?php if ( ! $posts ) : ?>
						<p class="hunt-news-date-nav__empty">내일 02시 첫 브리핑이 발행됩니다.</p>
					<?php else : ?><ul>
						<?php foreach ( $posts as $post ) : ?>
							<li><a href="<?php echo esc_url( get_permalink( $post ) ); ?>"<?php echo $post->ID === $active_id ? ' aria-current="page"' : ''; ?>>Hunt News <?php echo esc_html( get_the_date( 'Y-m-d', $post ) ); ?></a></li>
						<?php endforeach; ?>
					</ul><?php endif; ?>
				</details>
			<?php endforeach; ?>
		</div>
	</aside>
	<?php
}

/**
 * The Hunt News category hero owns the archive H1, so suppress Kadence's
 * duplicate category hero before it renders server-side.
 */
function hunt_news_remove_legacy_category_hero() {
	if ( is_category() ) {
		remove_action( 'kadence_hero_header', 'Kadence\\hero_title' );
	}
}
add_action( 'wp', 'hunt_news_remove_legacy_category_hero', 20 );

/**
 * Keep unfinished category shells out of search results. An empty archive is
 * useful while the first issue is being prepared, but it is not a useful
 * landing page for readers or an advertising review surface.
 *
 * @param array<string,bool> $robots Current WordPress robots directives.
 * @return array<string,bool>
 */
function hunt_news_noindex_empty_category_archives( $robots ) {
	if ( ! is_category() ) {
		return $robots;
	}
	$category = get_queried_object();
	if ( $category instanceof WP_Term && 0 === (int) $category->count ) {
		unset( $robots['index'] );
		$robots['noindex'] = true;
		$robots['follow']  = true;
	}
	return $robots;
}
add_filter( 'wp_robots', 'hunt_news_noindex_empty_category_archives', 20 );

/**
 * Special editorial series remain part of the product, but their archives
 * should not expose a theme-generated empty result before the first valid issue.
 * A temporary redirect preserves the future URL and automatically stops once
 * the category contains a published post.
 */
function hunt_news_redirect_empty_special_editorial_archive() {
	if ( ! is_category( array( 'weekly-tech-review', 'technical-explainer' ) ) ) {
		return;
	}
	$category = get_queried_object();
	if ( ! ( $category instanceof WP_Term ) || 0 < (int) $category->count ) {
		return;
	}
	$target = get_post_type_archive_link( 'hunt_briefing' );
	wp_safe_redirect( $target ? $target : home_url( '/briefing/' ), 302, 'Hunt News' );
	exit;
}
add_action( 'template_redirect', 'hunt_news_redirect_empty_special_editorial_archive', 1 );

/**
 * Return a stable, public-only snapshot for the home briefing board.
 *
 * @param int $limit Maximum number of posts.
 * @return array<int, WP_Post>
 */
function hunt_news_briefing_posts( $limit = 12 ) {
	return get_posts(
		array(
			'post_type'              => 'post',
			'post_status'            => 'publish',
			'posts_per_page'         => max( 1, min( 24, absint( $limit ) ) ),
			'orderby'                => 'date',
			'order'                  => 'DESC',
			'ignore_sticky_posts'    => true,
			'no_found_rows'          => true,
			'update_post_meta_cache' => false,
		)
	);
}

/**
 * Return the latest published post in a reader-facing special category.
 * Empty categories intentionally return null so no placeholder surface leaks.
 *
 * @param string $slug Category slug.
 * @return WP_Post|null
 */
function hunt_news_latest_special_post( $slug ) {
	$category = get_category_by_slug( sanitize_title( $slug ) );
	if ( ! $category || 0 === (int) $category->count ) {
		return null;
	}
	$posts = get_posts(
		array(
			'post_type'              => 'post',
			'post_status'            => 'publish',
			'posts_per_page'         => 1,
			'category'               => (int) $category->term_id,
			'orderby'                => 'date',
			'order'                  => 'DESC',
			'ignore_sticky_posts'    => true,
			'no_found_rows'          => true,
			'update_post_meta_cache' => false,
		)
	);
	return $posts ? $posts[0] : null;
}

/** Return recent original articles from one editorial category. */
function hunt_news_special_posts( $slug, $limit = 6 ) {
	$category = get_category_by_slug( sanitize_title( $slug ) );
	if ( ! $category || 0 === (int) $category->count ) {
		return array();
	}
	return get_posts(
		array(
			'post_type'              => 'post',
			'post_status'            => 'publish',
			'posts_per_page'         => max( 1, min( 12, absint( $limit ) ) ),
			'category'               => (int) $category->term_id,
			'orderby'                => 'date',
			'order'                  => 'DESC',
			'ignore_sticky_posts'    => true,
			'no_found_rows'          => true,
			'update_post_meta_cache' => false,
		)
	);
}

/** Render an original-analysis homepage while keeping daily reports in their archive. */
function hunt_news_render_editorial_home() {
	$explainers       = hunt_news_special_posts( 'technical-explainer', 6 );
	$reviews          = hunt_news_special_posts( 'weekly-tech-review', 3 );
	$latest_explainer = $explainers ? $explainers[0] : null;
	$latest_review    = $reviews ? $reviews[0] : null;
	$manifest         = hunt_news_latest_briefing_manifest();
	$analysis         = ! empty( $manifest['analysis'] ) && is_array( $manifest['analysis'] ) ? $manifest['analysis'] : array();
	$briefing_url     = get_post_type_archive_link( 'hunt_briefing' );
	$explainer_term   = get_category_by_slug( 'technical-explainer' );
	$review_term      = get_category_by_slug( 'weekly-tech-review' );
	$explainer_url    = $explainer_term ? get_category_link( $explainer_term->term_id ) : home_url( '/category/technical-explainer/' );
	$review_url       = $review_term ? get_category_link( $review_term->term_id ) : home_url( '/category/weekly-tech-review/' );
	?>
	<div id="hunt-news-originals" class="hunt-news-editorial-home">
		<section class="hunt-news-editorial-lead" aria-labelledby="hunt-news-editorial-lead-title">
			<header><p>ORIGINAL ANALYSIS</p><h2 id="hunt-news-editorial-lead-title">이번 주, 직접 판단할 기술 변화</h2><span>요약보다 비교·예제·실패 조건을 먼저 봅니다.</span></header>
			<div class="hunt-news-editorial-lead__grid">
				<?php if ( $latest_explainer ) : ?>
				<article class="hunt-news-editorial-feature">
					<p>기술 해설</p><time datetime="<?php echo esc_attr( get_the_date( DATE_W3C, $latest_explainer ) ); ?>"><?php echo esc_html( get_the_date( 'Y.m.d', $latest_explainer ) ); ?></time>
					<h3><a href="<?php echo esc_url( get_permalink( $latest_explainer ) ); ?>"><?php echo esc_html( get_the_title( $latest_explainer ) ); ?></a></h3>
					<span><?php echo esc_html( hunt_news_briefing_summary( $latest_explainer ) ); ?></span>
					<ul><li>변경 전후</li><li>따라 할 예제</li><li>적용하지 않을 조건</li></ul>
					<a href="<?php echo esc_url( get_permalink( $latest_explainer ) ); ?>">해설 읽기 <b aria-hidden="true">→</b></a>
				</article>
				<?php endif; ?>
				<div class="hunt-news-editorial-side">
					<?php if ( $latest_review ) : ?><article><p>주간 기술 회고</p><h3><a href="<?php echo esc_url( get_permalink( $latest_review ) ); ?>"><?php echo esc_html( get_the_title( $latest_review ) ); ?></a></h3><span><?php echo esc_html( hunt_news_briefing_summary( $latest_review ) ); ?></span><a href="<?php echo esc_url( get_permalink( $latest_review ) ); ?>">이번 주 판단 보기 →</a></article><?php endif; ?>
					<article class="hunt-news-editorial-briefing"><p>오늘의 브리핑 · <?php echo esc_html( hunt_news_briefing_display_date( $manifest, 'Y.m.d' ) ); ?></p><h3><?php echo esc_html( (string) ( $analysis['headline'] ?? '오늘 수집한 기술 변화를 날짜별 보고서로 정리했습니다.' ) ); ?></h3><span>브리핑은 매일 유지하며 검색용 독립 글로 쪼개지 않습니다.</span><a href="<?php echo esc_url( $briefing_url ); ?>">날짜별 브리핑 보기 →</a></article>
				</div>
			</div>
		</section>

		<?php if ( $explainers ) : ?>
		<section class="hunt-news-original-grid" aria-labelledby="hunt-news-original-grid-title">
			<header><div><p>DEEP READS</p><h2 id="hunt-news-original-grid-title">문제를 해결하는 기술 해설</h2></div><a href="<?php echo esc_url( $explainer_url ); ?>">전체 해설 보기 →</a></header>
			<div><?php foreach ( $explainers as $index => $post ) : ?><article><span><?php echo esc_html( sprintf( '%02d', $index + 1 ) ); ?></span><time datetime="<?php echo esc_attr( get_the_date( DATE_W3C, $post ) ); ?>"><?php echo esc_html( get_the_date( 'Y.m.d', $post ) ); ?></time><h3><a href="<?php echo esc_url( get_permalink( $post ) ); ?>"><?php echo esc_html( get_the_title( $post ) ); ?></a></h3><p><?php echo esc_html( hunt_news_briefing_summary( $post ) ); ?></p><a href="<?php echo esc_url( get_permalink( $post ) ); ?>">근거와 예제 보기 →</a></article><?php endforeach; ?></div>
		</section>
		<?php endif; ?>

		<section class="hunt-news-editorial-method" aria-labelledby="hunt-news-editorial-method-title"><div><p>HOW WE WORK</p><h2 id="hunt-news-editorial-method-title">한 글에 남기는 네 가지</h2></div><ol><li><b>1</b><strong>무엇이 바뀌었나</strong><span>원문과 버전을 확인합니다.</span></li><li><b>2</b><strong>기존과 무엇이 다른가</strong><span>비교 대상과 전제를 밝힙니다.</span></li><li><b>3</b><strong>누구에게 적용되나</strong><span>환경과 적용 범위를 제한합니다.</span></li><li><b>4</b><strong>어디서 실패하나</strong><span>반례와 롤백 조건을 남깁니다.</span></li></ol><nav><a href="<?php echo esc_url( home_url( '/editorial-policy/' ) ); ?>">편집 원칙</a><a href="<?php echo esc_url( home_url( '/about/' ) ); ?>">만드는 사람과 방식</a><a href="<?php echo esc_url( $review_url ); ?>">주간 회고</a></nav></section>
	</div>
	<script id="hunt-news-editorial-home-position">document.addEventListener('DOMContentLoaded',function(){var home=document.getElementById('hunt-news-originals');var intro=document.getElementById('huntlab-home-intro');var main=document.querySelector('#main,main.site-main');if(home&&intro&&intro.parentNode){intro.insertAdjacentElement('afterend',home);}if(main){main.hidden=true;}});</script>
	<?php
}

/**
 * Keep home-card summaries short and based only on the published article.
 *
 * @param WP_Post $post Post object.
 * @return string
 */
function hunt_news_briefing_summary( $post ) {
	$summary = has_excerpt( $post ) ? get_the_excerpt( $post ) : wp_strip_all_tags( $post->post_content );
	return wp_html_excerpt( trim( wp_strip_all_tags( $summary ) ), 116, '…' );
}

/**
 * Resolve one visible primary category without inventing a new taxonomy.
 *
 * @param WP_Post $post Post object.
 * @return array{name:string,url:string,slug:string}
 */
function hunt_news_briefing_category( $post ) {
	$categories = get_the_category( $post->ID );
	if ( ! $categories ) {
		return array( 'name' => '브리핑', 'url' => home_url( '/' ), 'slug' => 'briefing' );
	}
	$category = $categories[0];
	$url      = get_category_link( $category->term_id );
	return array(
		'name' => $category->name,
		'url'  => is_wp_error( $url ) ? home_url( '/' ) : $url,
		'slug' => $category->slug,
	);
}

/**
 * Count observed taxonomy terms in the same post snapshot.
 *
 * @param array<int, WP_Post> $posts Posts used by the board.
 * @param int                 $limit Maximum keyword rows.
 * @return array<int, array{name:string,count:int,percent:int,url:string}>
 */
function hunt_news_briefing_keywords( $posts, $limit = 7 ) {
	$terms = array();
	foreach ( $posts as $post ) {
		$post_terms = get_the_tags( $post->ID );
		if ( ! $post_terms ) {
			$post_terms = get_the_category( $post->ID );
		}
		foreach ( array_slice( $post_terms, 0, 4 ) as $term ) {
			$key = sanitize_title( $term->name );
			if ( ! isset( $terms[ $key ] ) ) {
				$url = get_term_link( $term );
				$terms[ $key ] = array(
					'name'  => $term->name,
					'count' => 0,
					'url'   => is_wp_error( $url ) ? home_url( '/' ) : $url,
				);
			}
			$terms[ $key ]['count']++;
		}
	}
	usort(
		$terms,
		function ( $left, $right ) {
			if ( $left['count'] === $right['count'] ) {
				return strcmp( $left['name'], $right['name'] );
			}
			return $right['count'] <=> $left['count'];
		}
	);
	$terms = array_slice( $terms, 0, max( 1, absint( $limit ) ) );
	$max   = $terms ? max( array_column( $terms, 'count' ) ) : 1;
	foreach ( $terms as &$term ) {
		$term['percent'] = max( 24, (int) round( ( $term['count'] / $max ) * 100 ) );
	}
	unset( $term );
	return $terms;
}

/**
 * Select an honest time-based reading path from the recent post snapshot.
 *
 * @param array<int, WP_Post> $posts Recent posts.
 * @return array<int, array{label:string,description:string,post:WP_Post}>
 */
function hunt_news_briefing_timeline( $posts ) {
	$now     = current_time( 'timestamp' );
	$buckets = array(
		'today' => array( 'label' => '오늘', 'description' => '지금 먼저 확인할 변화', 'min' => 0, 'max' => DAY_IN_SECONDS ),
		'week'  => array( 'label' => '이번 주', 'description' => '일정과 조건을 다시 볼 것', 'min' => DAY_IN_SECONDS, 'max' => 7 * DAY_IN_SECONDS ),
		'month' => array( 'label' => '이번 달', 'description' => '신청·계약 전에 점검할 것', 'min' => 7 * DAY_IN_SECONDS, 'max' => 31 * DAY_IN_SECONDS ),
		'watch' => array( 'label' => '계속 보기', 'description' => '후속 발표를 추적할 것', 'min' => 31 * DAY_IN_SECONDS, 'max' => PHP_INT_MAX ),
	);
	$used = array();
	$rows = array();
	foreach ( $buckets as $bucket ) {
		$selected = null;
		foreach ( $posts as $post ) {
			if ( isset( $used[ $post->ID ] ) ) {
				continue;
			}
			$age = max( 0, $now - get_post_time( 'U', false, $post ) );
			if ( $age >= $bucket['min'] && $age < $bucket['max'] ) {
				$selected = $post;
				break;
			}
		}
		if ( $selected ) {
			$used[ $selected->ID ] = true;
			$rows[] = array( 'label' => $bucket['label'], 'description' => $bucket['description'], 'post' => $selected );
		}
	}
	return $rows;
}

/**
 * Return only a complete, recent pipeline manifest. Stale state never masquerades
 * as today's collection result and the homepage falls back to public posts.
 *
 * @return array<string,mixed>
 */
function hunt_news_latest_briefing_manifest() {
	if ( is_singular( 'hunt_briefing' ) ) {
		$historical = get_post_meta( get_queried_object_id(), '_hunt_news_briefing_manifest', true );
		if ( is_array( $historical ) && 'briefing-manifest.v1' === ( $historical['contract_version'] ?? '' ) && ! empty( $historical['complete'] ) ) {
			return $historical;
		}
	}
	$manifest = get_option( 'hunt_news_briefing_manifest', array() );
	if ( ! is_array( $manifest ) || 'briefing-manifest.v1' !== ( $manifest['contract_version'] ?? '' ) || empty( $manifest['complete'] ) ) {
		return array();
	}
	$generated = strtotime( (string) ( $manifest['generated_at'] ?? '' ) );
	$now       = current_time( 'timestamp', true );
	if ( ! $generated || $generated > $now + HOUR_IN_SECONDS || $generated < $now - ( 3 * DAY_IN_SECONDS ) ) {
		return array();
	}
	$published = isset( $manifest['published'] ) && is_array( $manifest['published'] ) ? $manifest['published'] : array();
	return 2 === count( $published ) ? $manifest : array();
}

/**
 * Use the stored analysis timestamp instead of the wall clock for report labels.
 * A failed daily run must not make yesterday's manifest look like today's report.
 *
 * @param array<string,mixed> $manifest Stored briefing manifest.
 * @param string              $format   WordPress date format.
 * @return string
 */
function hunt_news_briefing_display_date( $manifest, $format = 'Y-m-d' ) {
	if ( is_singular( 'hunt_briefing' ) ) {
		return get_the_date( $format, get_queried_object_id() );
	}
	$generated_at = (string) ( $manifest['analysis']['generated_at'] ?? $manifest['generated_at'] ?? '' );
	$timestamp    = strtotime( $generated_at );
	return $timestamp ? wp_date( $format, $timestamp ) : '';
}

/**
 * Show the date for cross-day source items and only the time for same-day items.
 *
 * @param string $published_at Source publication timestamp.
 * @param string $report_at    Briefing analysis timestamp.
 * @return string
 */
function hunt_news_source_time_label( $published_at, $report_at ) {
	$published = strtotime( (string) $published_at );
	$report    = strtotime( (string) $report_at );
	if ( ! $published ) {
		return '';
	}
	$format = $report && wp_date( 'Y-m-d', $published ) === wp_date( 'Y-m-d', $report ) ? 'H:i' : 'm.d H:i';
	return wp_date( $format, $published );
}

/**
 * Prefer the two verified publications from the latest manifest, then fill the
 * third briefing slot with the next public post.
 *
 * @param array<int,WP_Post> $recent_posts Recent public posts.
 * @param array<string,mixed> $manifest Latest manifest.
 * @return array<int,WP_Post>
 */
function hunt_news_manifest_signal_posts( $recent_posts, $manifest ) {
	$ordered = array();
	$used    = array();
	foreach ( (array) ( $manifest['published'] ?? array() ) as $item ) {
		$post = get_post( absint( $item['post_id'] ?? 0 ) );
		if ( $post && 'post' === $post->post_type && 'publish' === $post->post_status ) {
			$ordered[]        = $post;
			$used[ $post->ID ] = true;
		}
	}
	foreach ( $recent_posts as $post ) {
		if ( count( $ordered ) >= 3 ) {
			break;
		}
		if ( ! isset( $used[ $post->ID ] ) ) {
			$ordered[] = $post;
		}
	}
	return array_slice( $ordered, 0, 3 );
}

/**
 * Resolve the independent articles that belong to a stored daily briefing.
 * Historical briefing pages must never silently show today's recent posts.
 *
 * @param array<string,mixed> $manifest Stored manifest.
 * @return array<int,WP_Post>
 */
function hunt_news_manifest_posts( $manifest ) {
	$posts = array();
	foreach ( (array) ( $manifest['published'] ?? array() ) as $item ) {
		$post = get_post( absint( $item['post_id'] ?? 0 ) );
		if ( $post && 'post' === $post->post_type && 'publish' === $post->post_status ) {
			$posts[] = $post;
		}
	}
	return $posts;
}

/** @return array<int,array<string,mixed>> */
function hunt_news_manifest_publications_by_post( $manifest ) {
	$items = array();
	foreach ( (array) ( $manifest['published'] ?? array() ) as $item ) {
		$post_id = absint( $item['post_id'] ?? 0 );
		if ( $post_id ) {
			$items[ $post_id ] = $item;
		}
	}
	return $items;
}

/** @return array<int,array{name:string,url:string,count:int,percent:int,label:string}> */
function hunt_news_manifest_keywords( $manifest ) {
	$topics = (array) ( $manifest['collection']['top_topics'] ?? array() );
	$max    = 1;
	foreach ( $topics as $topic ) {
		$max = max( $max, absint( $topic['approx_traffic'] ?? 0 ) );
	}
	$keywords = array();
	foreach ( array_slice( $topics, 0, 7 ) as $topic ) {
		$name    = sanitize_text_field( (string) ( $topic['topic'] ?? '' ) );
		$traffic = absint( $topic['approx_traffic'] ?? 0 );
		if ( '' === $name ) {
			continue;
		}
		$keywords[] = array(
			'name'    => $name,
			'url'     => add_query_arg( 's', $name, home_url( '/' ) ),
			'count'   => $traffic,
			'percent' => max( 24, (int) round( ( $traffic / $max ) * 100 ) ),
			'label'   => $traffic ? number_format_i18n( $traffic ) . '+' : '관측',
		);
	}
	return $keywords;
}

/**
 * Return category-specific editorial context for the archive hero.
 *
 * @return array<string, array{label:string,title:string,description:string,promises:array<int,string>,image:string,alt:string}>
 */
function huntlab_warm_editorial_category_intros() {
	return array(
		'ai-ml-core'          => array(
			'label' => 'AI/ML 핵심', 'title' => '모델 이름보다,<br>검증과 실제 영향을.',
			'description' => '에이전트, 모델, 평가와 AI 인프라 변화를 공식 원문과 독립 보도로 확인합니다.',
			'promises' => array( '공식 원문', '평가', '실무 영향' ), 'image' => 'ai.webp',
			'alt' => 'AI 모델과 평가 지표, 인프라가 연결된 기술 뉴스 미니어처',
		),
		'development-trends'  => array(
			'label' => '개발 트렌드', 'title' => '화제보다,<br>개발 흐름의 변화를.',
			'description' => '오픈소스, 클라우드, 데이터와 보안 변경이 개발·운영에 미치는 영향을 정리합니다.',
			'promises' => array( '릴리스', '마이그레이션', '운영 판단' ), 'image' => 'tech.webp',
			'alt' => '코드와 클라우드 서비스, 데이터 흐름이 연결된 개발 트렌드 미니어처',
		),
		'ai-official-blogs'   => array(
			'label' => 'AI 공식 블로그', 'title' => '발표보다,<br>근거와 한계를.',
			'description' => '공식 연구·제품 발표를 독립 출처와 함께 읽고 홍보와 검증된 사실을 구분합니다.',
			'promises' => array( '공식 발표', '독립 확인', '한계' ), 'image' => 'ml-algorithms.webp',
			'alt' => '공식 발표 문서와 독립 검증 카드가 나란히 놓인 AI 블로그 미니어처',
		),
		'korea-it'            => array(
			'label' => '국내 IT', 'title' => '보도자료보다,<br>국내 기술 산업의 변화.',
			'description' => '국내 기업, 플랫폼, 반도체와 클라우드 소식을 공시와 공식 자료로 확인합니다.',
			'promises' => array( '기업 공시', '기술 변화', '산업 영향' ), 'image' => 'system-architecture.webp',
			'alt' => '국내 기업과 반도체, 클라우드 인프라가 연결된 국내 IT 미니어처',
		),
		'korea-current-affairs' => array(
			'label' => '국내 시사', 'title' => '정쟁보다,<br>기술 정책과 산업 영향을.',
			'description' => 'AI·플랫폼·반도체 정책과 규제가 개발자, 기업과 일자리에 만드는 변화를 설명합니다.',
			'promises' => array( '정책 원문', '산업 영향', '확인할 것' ), 'image' => 'society.webp',
			'alt' => '정책 문서와 기술 산업, 개발 현장이 이어지는 국내 시사 미니어처',
		),
		'weekly-tech-review'    => array(
			'label'       => '주간 기술 회고',
			'title'       => '기사 목록보다,<br>한 주의 방향과 다음 판단을.',
			'description' => '일일 브리핑에서 반복된 변화와 실제로 달라진 판단을 묶어 다음 주 확인할 신호를 정리합니다.',
			'promises'    => array( '반복된 변화', '개발자 영향', '다음 주 신호' ),
			'image'       => 'system-architecture.webp',
			'alt'         => '일주일의 기술 변화와 다음 주 확인 신호를 연결한 주간 기술 회고 미니어처',
		),
		'technical-explainer'   => array(
			'label'       => '기술 해설',
			'title'       => '뉴스보다 깊게,<br>예제로 끝까지.',
			'description' => '검색 수요가 확인된 기술 변화를 코드·설정·비교와 실패 조건까지 독립 해설로 풀어냅니다.',
			'promises'    => array( '구체적인 문제', '따라 할 예제', '실패와 적용 조건' ),
			'image'       => 'tech.webp',
			'alt'         => '기술 문서와 코드 예제, 성공과 실패 결과가 이어지는 기술 해설 미니어처',
		),
		'life'                => array(
			'label'       => '생활',
			'title'       => '발표보다,<br>내 일상의 변화를.',
			'description' => '교통, 주거, 건강, 교육과 소비 변화가 누구에게 언제 적용되고 지금 무엇을 확인해야 하는지 설명합니다.',
			'promises'    => array( '적용 대상', '시행일', '내가 할 일' ),
			'image'       => 'hot-issue.webp',
			'alt'         => '공식 문서의 변화가 시간선을 따라 가정과 일상으로 전달되는 과정을 표현한 미니어처',
		),
		'politics'            => array(
			'label'       => '정치',
			'title'       => '진영보다,<br>쟁점과 생활 영향을.',
			'description' => '법안과 정책 원문, 찬반의 근거와 전제를 나누고 내 권리·안전·세금에 무엇이 달라지는지 설명합니다.',
			'promises'    => array( '원문', '찬반 근거', '생활 영향' ),
			'image'       => 'society.webp',
			'alt'         => '서로 다른 주장과 공식 문서가 검증 관문을 지나 시민 생활로 이어지는 정치 쟁점 미니어처',
		),
		'real-estate'         => array(
			'label'       => '부동산',
			'title'       => '전망보다,<br>내 계약과 주거를.',
			'description' => '전월세, 청약, 대출 규제와 세금 변화가 누구에게 언제 적용되는지 조건별로 설명합니다.',
			'promises'    => array( '계약 조건', '현금흐름', '거주 선택' ),
			'image'       => 'economy.webp',
			'alt'         => '주택과 계약서, 대출 계산표가 가계의 현금흐름으로 연결되는 부동산 변화 미니어처',
		),
		'culture-entertainment' => array(
			'label'       => '문화·엔터',
			'title'       => '화제보다,<br>내 소비와 선택을.',
			'description' => '구독료, 티켓, 계약과 플랫폼 변화가 보고 듣고 즐기는 방식에 어떤 차이를 만드는지 설명합니다.',
			'promises'    => array( '요금', '계약', '소비 선택' ),
			'image'       => 'build-log.webp',
			'alt'         => '콘텐츠 카드와 티켓, 플랫폼 장치가 소비자의 선택으로 이어지는 문화 엔터 미니어처',
		),
		'it'                  => array(
			'label'       => 'IT',
			'title'       => '기술 이름보다,<br>내가 겪는 변화를.',
			'description' => 'AI와 플랫폼, 앱과 서비스의 작동 원리를 사용자 행동에서 시작해 쉬운 말로 설명합니다.',
			'promises'    => array( '사용자 경험', '작동 원리', '선택 기준' ),
			'image'       => 'tech.webp',
			'alt'         => '휴대전화와 서비스 모듈, 데이터 흐름이 연결된 IT 생활 변화 미니어처',
		),
		'ml-algorithms'       => array(
			'label'       => 'ML Algorithms',
			'title'       => '점수보다,<br>의사결정 구조를.',
			'description' => '데이터 조건과 평가 기준을 먼저 밝히고, 알고리즘이 어떤 판단을 만드는지 실행 결과로 설명합니다.',
			'promises'    => array( '데이터', '알고리즘', '평가' ),
			'image'       => 'ml-algorithms.webp',
			'alt'         => '데이터가 분기 구조를 거쳐 평가 결과로 나뉘는 머신러닝 과정을 표현한 도자기 미니어처',
		),
		'harness-engineering' => array(
			'label'       => 'Harness Engineering',
			'title'       => '자동화보다,<br>실패하지 않는 흐름을.',
			'description' => '재시도와 멱등성, 승인 게이트와 관측 가능성을 함께 설계해 오래 운영할 수 있는 자동화를 기록합니다.',
			'promises'    => array( '재시도', '멱등성', 'Guardrail' ),
			'image'       => 'harness-engineering.webp',
			'alt'         => '재시도 고리와 승인 게이트, 관측 계기가 연결된 자동화 파이프라인 도자기 미니어처',
		),
		'system-architecture' => array(
			'label'       => 'System Architecture',
			'title'       => '구성요소보다,<br>흐름과 경계를.',
			'description' => '서비스와 데이터의 경계, 장애 격리, 확장 경로를 실제 운영의 선택과 트레이드오프로 풀어냅니다.',
			'promises'    => array( '확장', '장애 격리', 'Trade-off' ),
			'image'       => 'system-architecture.webp',
			'alt'         => '게이트웨이와 서비스, 큐, 캐시, 저장소가 장애 우회 경로로 연결된 시스템 아키텍처 미니어처',
		),
		'tech'                => array(
			'label'       => 'Tech',
			'title'       => '도구보다,<br>작동 원리와 운영 판단.',
			'description' => '새 기술을 소개하는 데서 멈추지 않고 구현, 디버깅, 운영에서 다시 써먹을 판단을 남깁니다.',
			'promises'    => array( '구현', '디버깅', '운영' ),
			'image'       => 'tech.webp',
			'alt'         => '코드 화면과 모듈, 서버 장치, 개발 도구가 놓인 기술 작업대 도자기 미니어처',
		),
		'ai'                  => array(
			'label'       => 'AI',
			'title'       => '모델보다,<br>검증 가능한 활용을.',
			'description' => '모델 이름보다 입력과 출력, 평가 조건, 비용과 한계를 확인해 실제로 쓸 수 있는 AI 활용을 다룹니다.',
			'promises'    => array( '모델', '평가', '활용' ),
			'image'       => 'ai.webp',
			'alt'         => '입력 카드가 인공지능 모델 장치와 평가 계기를 거쳐 결과로 나오는 도자기 미니어처',
		),
		'build-log'           => array(
			'label'       => 'Build Log',
			'title'       => '결과보다,<br>만드는 과정과 판단을.',
			'description' => '완성 화면만 보여주지 않고 바꾼 이유, 실패 로그, 변경 전후와 운영 경험을 함께 남깁니다.',
			'promises'    => array( '실패 기록', '변경 전후', '운영 경험' ),
			'image'       => 'build-log.webp',
			'alt'         => '변경 전후 모듈과 공구, 로그 카드, 측정 계기가 놓인 개발 작업대 도자기 미니어처',
		),
		'economy'             => array(
			'label'       => '경제',
			'title'       => '숫자보다,<br>생활에 닿는 의미를.',
			'description' => '공식 통계의 기준과 맥락을 확인하고, 숫자의 변화가 가계와 기업의 선택에 미치는 영향을 설명합니다.',
			'promises'    => array( '공식 통계', '맥락', '생활 영향' ),
			'image'       => 'economy.webp',
			'alt'         => '경제 데이터 토큰이 가계와 기업, 공공 부문을 거쳐 측정 계기로 흐르는 도자기 미니어처',
		),
		'society'             => array(
			'label'       => '사회',
			'title'       => '이슈보다,<br>제도와 실제 영향을.',
			'description' => '공식 자료와 적용 조건을 확인하고, 제도의 변화가 사람과 일상에 닿는 과정을 정리합니다.',
			'promises'    => array( '공식 자료', '사실 확인', '실제 적용' ),
			'image'       => 'society.webp',
			'alt'         => '공식 문서가 제도 관문을 지나 가정과 공동체에 전달되는 사회 시스템 도자기 미니어처',
		),
		'hot-issue'           => array(
			'label'       => 'Hot Issue',
			'title'       => '속보보다,<br>확인된 사실과 맥락을.',
			'description' => '서로 다른 출처와 원문을 교차 확인해 지금 무엇이 달라졌고 실제 영향은 무엇인지 짚습니다.',
			'promises'    => array( '교차 확인', '원문', '실제 영향' ),
			'image'       => 'hot-issue.webp',
			'alt'         => '서로 다른 출처 카드가 확대경과 검증 관문, 시간선을 거쳐 확인되는 도자기 미니어처',
		),
	);
}

/**
 * Give the posts index and category archives a quiet editorial introduction
 * without changing the active theme or article pages.
 */
function huntlab_warm_editorial_home_intro() {
	if ( is_admin() || ! ( is_home() || is_front_page() || is_category() || is_post_type_archive( 'hunt_briefing' ) || is_singular( 'hunt_briefing' ) ) ) {
		return;
	}

	$is_category = is_category();
	$intro       = null;
	$brief_posts = array();

	if ( $is_category ) {
		$category = get_queried_object();
		$intros   = huntlab_warm_editorial_category_intros();
		$slug     = isset( $category->slug ) ? (string) $category->slug : '';
		$intro    = isset( $intros[ $slug ] ) ? $intros[ $slug ] : null;
		if ( ! $intro ) {
			return;
		}
	} else {
		$brief_posts = hunt_news_briefing_posts( 12 );
	}
	$brief_manifest = $is_category ? array() : hunt_news_latest_briefing_manifest();
	if ( is_singular( 'hunt_briefing' ) && $brief_manifest ) {
		$brief_posts = hunt_news_manifest_posts( $brief_manifest );
	}
	?>
	<section id="huntlab-home-intro" class="huntlab-home-intro<?php echo $is_category ? ' huntlab-home-intro--category' : ''; ?>" aria-labelledby="huntlab-home-intro-title">
		<div class="huntlab-home-intro__copy">
			<p class="huntlab-home-intro__eyebrow"><?php echo $is_category ? esc_html( 'Hunt News · ' . $intro['label'] ) : 'Hunt News · 기술을 판단하는 편집'; ?></p>
			<h1 id="huntlab-home-intro-title"><?php echo $is_category ? wp_kses( $intro['title'], array( 'br' => array() ) ) : '무엇이 바뀌었고,<br>어디까지 적용할 수 있나.'; ?></h1>
			<p class="huntlab-home-intro__description"><?php echo $is_category ? esc_html( $intro['description'] ) : '발표를 다시 요약하는 대신 공식 원문과 독립 자료를 대조하고, 예제와 실패 조건을 통해 개발자가 실제로 적용할 수 있는 범위를 설명합니다.'; ?></p>
			<ul class="huntlab-home-intro__promises" aria-label="<?php echo esc_attr( $is_category ? $intro['label'] . ' 콘텐츠 원칙' : 'Hunt News 콘텐츠 원칙' ); ?>">
				<?php foreach ( $is_category ? $intro['promises'] : array( '근거 대조', '예제와 비교', '실패 조건' ) as $promise ) : ?>
					<li><?php echo esc_html( $promise ); ?></li>
				<?php endforeach; ?>
			</ul>
			<?php if ( ! $is_category ) : ?>
				<div class="huntlab-home-intro__status" aria-label="브리핑 상태">
					<span><?php echo esc_html( hunt_news_briefing_display_date( $brief_manifest, 'Y.m.d' ) ); ?></span>
					<span>독립 해설 주 2회 · 주간 회고 1회</span>
					<?php if ( $brief_manifest ) : ?><span>날짜별 기술 브리핑은 매일 유지</span><?php endif; ?>
					<a href="#hunt-news-originals">최신 해설 보기 <b aria-hidden="true">↓</b></a>
				</div>
			<?php endif; ?>
		</div>
		<?php if ( $is_category ) : ?>
			<figure class="huntlab-home-intro__visual">
				<img src="<?php echo esc_url( plugins_url( 'assets/categories/' . $intro['image'], __FILE__ ) ); ?>" width="1000" height="563" alt="<?php echo esc_attr( $intro['alt'] ); ?>" loading="eager" decoding="async" fetchpriority="high">
			</figure>
		<?php endif; ?>
	</section>
	<script id="huntlab-home-intro-position">
	document.addEventListener('DOMContentLoaded',function(){var intro=document.getElementById('huntlab-home-intro');var main=document.querySelector('#main,main.site-main');if(intro&&main&&main.parentNode){main.parentNode.insertBefore(intro,main);}});
	</script>
	<?php
}
add_action( 'wp_body_open', 'huntlab_warm_editorial_home_intro', 25 );

/**
 * Return the posts with the most verified reads during the latest seven days.
 * Counts come from the same 30-second and 25%-depth signal sent to GA4.
 *
 * @param int $limit       Maximum number of rows.
 * @param int $days_window Number of UTC calendar days to include.
 * @return array<int, array{post:WP_Post,count:int}>
 */
function hunt_news_popular_rows( $limit = 10, $days_window = 7 ) {
	$stats  = get_option( 'hunt_news_popular_reads', array() );
	$days   = isset( $stats['days'] ) && is_array( $stats['days'] ) ? $stats['days'] : array();
	$totals = array();
	$today  = current_time( 'timestamp', true );
	$today_key = gmdate( 'Y-m-d', $today );
	$yesterday_key = gmdate( 'Y-m-d', $today - DAY_IN_SECONDS );

	$days_window = max( 1, min( 7, absint( $days_window ) ) );
	for ( $offset = 0; $offset < $days_window; $offset++ ) {
		$key = gmdate( 'Y-m-d', $today - ( $offset * DAY_IN_SECONDS ) );
		if ( empty( $days[ $key ] ) || ! is_array( $days[ $key ] ) ) {
			continue;
		}
		foreach ( $days[ $key ] as $post_id => $count ) {
			$post_id = absint( $post_id );
			if ( $post_id ) {
				$totals[ $post_id ] = isset( $totals[ $post_id ] ) ? $totals[ $post_id ] + absint( $count ) : absint( $count );
			}
		}
	}

	$rows = array();
	foreach ( $totals as $post_id => $count ) {
		$post = get_post( $post_id );
		if ( ! $post || 'post' !== $post->post_type || 'publish' !== $post->post_status ) {
			continue;
		}
		$today_count     = isset( $days[ $today_key ][ $post_id ] ) ? absint( $days[ $today_key ][ $post_id ] ) : 0;
		$yesterday_count = isset( $days[ $yesterday_key ][ $post_id ] ) ? absint( $days[ $yesterday_key ][ $post_id ] ) : 0;
		$trend            = $today_count > $yesterday_count ? 'up' : ( $today_count < $yesterday_count ? 'down' : 'steady' );
		$rows[]           = array( 'post' => $post, 'count' => $count, 'trend' => $trend );
	}

	usort(
		$rows,
		function ( $left, $right ) {
			if ( $left['count'] === $right['count'] ) {
				return strcmp( $right['post']->post_date_gmt, $left['post']->post_date_gmt );
			}
			return $right['count'] <=> $left['count'];
		}
	);

	return array_slice( $rows, 0, max( 1, absint( $limit ) ) );
}

/**
 * Render an honest, compact popularity board without substituting latest posts.
 */
function hunt_news_render_popular_news() {
	$realtime_rows = hunt_news_popular_rows( 10, 1 );
	$weekly_rows   = hunt_news_popular_rows( 10, 7 );
	$stats         = get_option( 'hunt_news_popular_reads', array() );
	?>
	<section id="hunt-news-popular" class="hunt-news-popular" aria-labelledby="hunt-news-popular-title">
		<button type="button" class="hunt-news-popular__toggle" aria-expanded="false" aria-controls="hunt-news-popular-panel"><span>인기뉴스</span><b aria-hidden="true">‹</b></button>
		<div id="hunt-news-popular-panel" class="hunt-news-popular__panel">
			<header class="hunt-news-popular__header">
				<h2 id="hunt-news-popular-title" class="screen-reader-text">우리 인기뉴스</h2>
				<div class="hunt-news-popular__tabs" role="tablist" aria-label="인기뉴스 집계 기간">
					<button type="button" id="hunt-news-popular-tab-realtime" class="hunt-news-popular__tab is-active" role="tab" aria-selected="true" aria-controls="hunt-news-popular-realtime" tabindex="0" data-popular-tab="realtime">실시간 인기</button>
					<button type="button" id="hunt-news-popular-tab-weekly" class="hunt-news-popular__tab" role="tab" aria-selected="false" aria-controls="hunt-news-popular-weekly" tabindex="-1" data-popular-tab="weekly">최근 7일</button>
				</div>
			</header>
			<div id="hunt-news-popular-realtime" class="hunt-news-popular__tabpanel" role="tabpanel" aria-labelledby="hunt-news-popular-tab-realtime" data-popular-panel="realtime">
			<?php if ( $realtime_rows ) : ?>
				<ol class="hunt-news-popular__list">
					<?php foreach ( $realtime_rows as $index => $row ) : ?>
						<?php $short_title = wp_html_excerpt( wp_strip_all_tags( get_the_title( $row['post'] ) ), 34, '…' ); ?>
						<?php $trend_label = 'up' === $row['trend'] ? '상승' : ( 'down' === $row['trend'] ? '하락' : '변동 없음' ); ?>
						<?php $trend_arrow = 'up' === $row['trend'] ? '↑' : ( 'down' === $row['trend'] ? '↓' : '→' ); ?>
						<li><a href="<?php echo esc_url( get_permalink( $row['post'] ) ); ?>" aria-label="<?php echo esc_attr( get_the_title( $row['post'] ) . ', ' . $trend_label ); ?>"><strong><?php echo esc_html( (string) ( $index + 1 ) ); ?></strong><span><?php echo esc_html( $short_title ); ?></span><em class="hunt-news-popular__trend hunt-news-popular__trend--<?php echo esc_attr( $row['trend'] ); ?>" aria-hidden="true"><?php echo esc_html( $trend_arrow ); ?></em></a></li>
					<?php endforeach; ?>
				</ol>
			<?php else : ?>
				<p class="hunt-news-popular__empty">오늘의 실제 읽기 데이터를 집계하고 있습니다.</p>
			<?php endif; ?>
			</div>
			<div id="hunt-news-popular-weekly" class="hunt-news-popular__tabpanel" role="tabpanel" aria-labelledby="hunt-news-popular-tab-weekly" data-popular-panel="weekly" hidden>
			<?php if ( $weekly_rows ) : ?>
				<ol class="hunt-news-popular__list">
					<?php foreach ( $weekly_rows as $index => $row ) : ?>
						<?php $short_title = wp_html_excerpt( wp_strip_all_tags( get_the_title( $row['post'] ) ), 34, '…' ); ?>
						<?php $trend_label = 'up' === $row['trend'] ? '상승' : ( 'down' === $row['trend'] ? '하락' : '변동 없음' ); ?>
						<?php $trend_arrow = 'up' === $row['trend'] ? '↑' : ( 'down' === $row['trend'] ? '↓' : '→' ); ?>
						<li><a href="<?php echo esc_url( get_permalink( $row['post'] ) ); ?>" aria-label="<?php echo esc_attr( get_the_title( $row['post'] ) . ', ' . $trend_label ); ?>"><strong><?php echo esc_html( (string) ( $index + 1 ) ); ?></strong><span><?php echo esc_html( $short_title ); ?></span><em class="hunt-news-popular__trend hunt-news-popular__trend--<?php echo esc_attr( $row['trend'] ); ?>" aria-hidden="true"><?php echo esc_html( $trend_arrow ); ?></em></a></li>
					<?php endforeach; ?>
				</ol>
			<?php else : ?>
				<p class="hunt-news-popular__empty">최근 7일의 실제 읽기 데이터를 집계하고 있습니다.</p>
			<?php endif; ?>
			</div>
			<p class="hunt-news-popular__updated">GA4 조회와 30초 이상·25% 이상 읽은 신호 반영<?php echo ! empty( $stats['updated_at'] ) ? ' · ' . esc_html( wp_date( 'm월 d일 H:i', strtotime( $stats['updated_at'] ) ) ) . ' 갱신' : ''; ?></p>
		</div>
	</section>
	<?php
}

/**
 * Store one privacy-preserving verified read per visitor and post every six hours.
 */
function hunt_news_record_popular_read( $request ) {
	$post_id = absint( $request->get_param( 'post_id' ) );
	$post    = get_post( $post_id );
	if ( ! $post || 'post' !== $post->post_type || 'publish' !== $post->post_status ) {
		return new WP_Error( 'invalid_post', '공개 기사만 집계할 수 있습니다.', array( 'status' => 400 ) );
	}

	$ip        = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
	$user_agent = isset( $_SERVER['HTTP_USER_AGENT'] ) ? sanitize_text_field( wp_unslash( $_SERVER['HTTP_USER_AGENT'] ) ) : '';
	$visitor   = hash_hmac( 'sha256', $post_id . '|' . $ip . '|' . $user_agent, wp_salt( 'nonce' ) );
	$key       = 'hunt_news_read_' . substr( $visitor, 0, 32 );
	if ( get_transient( $key ) ) {
		return rest_ensure_response( array( 'counted' => false ) );
	}

	set_transient( $key, 1, 6 * HOUR_IN_SECONDS );
	$stats = get_option( 'hunt_news_popular_reads', array() );
	$days  = isset( $stats['days'] ) && is_array( $stats['days'] ) ? $stats['days'] : array();
	$today = gmdate( 'Y-m-d', current_time( 'timestamp', true ) );
	$days[ $today ] = isset( $days[ $today ] ) && is_array( $days[ $today ] ) ? $days[ $today ] : array();
	$days[ $today ][ $post_id ] = isset( $days[ $today ][ $post_id ] ) ? absint( $days[ $today ][ $post_id ] ) + 1 : 1;

	$cutoff = gmdate( 'Y-m-d', current_time( 'timestamp', true ) - ( 8 * DAY_IN_SECONDS ) );
	foreach ( array_keys( $days ) as $day ) {
		if ( $day < $cutoff ) {
			unset( $days[ $day ] );
		}
	}
	update_option( 'hunt_news_popular_reads', array( 'updated_at' => current_time( 'mysql', true ), 'days' => $days ), false );

	return rest_ensure_response( array( 'counted' => true ) );
}

function hunt_news_register_popular_read_route() {
	register_rest_route(
		'hunt-news/v1',
		'/engaged-view',
		array(
			'methods'             => 'POST',
			'callback'            => 'hunt_news_record_popular_read',
			'permission_callback' => '__return_true',
			'args'                => array( 'post_id' => array( 'required' => true, 'type' => 'integer' ) ),
		)
	);
	register_rest_route(
		'hunt-news/v1',
		'/briefing-run',
		array(
			'methods'             => 'POST',
			'callback'            => 'hunt_news_store_briefing_manifest',
			'permission_callback' => function () {
				return current_user_can( 'edit_posts' );
			},
		)
	);
}
add_action( 'rest_api_init', 'hunt_news_register_popular_read_route' );

/**
 * Sanitize the required evidence-backed daily analysis.
 *
 * @param mixed $payload Untrusted analysis payload.
 * @return array
 */
function hunt_news_sanitize_daily_analysis( $payload ) {
	if ( ! is_array( $payload ) ) { return array(); }
	$contract_version = (string) ( $payload['contract_version'] ?? '' );
	if ( ! in_array( $contract_version, array( 'daily-briefing-analysis.v1', 'daily-briefing-analysis.v2' ), true ) ) {
		return array();
	}
	$variable_sections = 'daily-briefing-analysis.v2' === $contract_version;
	$safe_urls = static function ( $urls ) {
		$result = array();
		foreach ( array_slice( (array) $urls, 0, 4 ) as $url ) {
			$url = esc_url_raw( (string) $url );
			if ( 0 === strpos( $url, 'https://' ) ) {
				$result[] = $url;
			}
		}
		return array_values( array_unique( $result ) );
	};
	$safe = array(
		'contract_version' => $contract_version,
		'generated_at' => sanitize_text_field( (string) ( $payload['generated_at'] ?? '' ) ),
		'source_snapshot_hash' => sanitize_text_field( (string) ( $payload['source_snapshot_hash'] ?? '' ) ),
		'headline' => sanitize_text_field( (string) ( $payload['headline'] ?? '' ) ),
		'summary' => sanitize_textarea_field( (string) ( $payload['summary'] ?? '' ) ),
		'retrospective' => array( 'status' => 'baseline', 'previous_generated_at' => '', 'previous_snapshot_hash' => '', 'items' => array() ),
		'core_signals' => array(), 'keywords' => array(), 'matrix' => array(), 'timeline' => array(),
		'insight_cards' => array(), 'themes' => array(), 'developer_insights' => array(),
		'watchlist' => array(), 'source_title_translations' => array(), 'must_read' => array(),
	);
	$retrospective = (array) ( $payload['retrospective'] ?? array() );
	if ( 'available' === ( $retrospective['status'] ?? '' ) ) {
		$previous_hash = sanitize_text_field( (string) ( $retrospective['previous_snapshot_hash'] ?? '' ) );
		$previous_time = sanitize_text_field( (string) ( $retrospective['previous_generated_at'] ?? '' ) );
		$seen_indexes  = array();
		$review_items  = array();
		foreach ( array_slice( (array) ( $retrospective['items'] ?? array() ), 0, 3 ) as $row ) {
			$signal_index = absint( $row['previous_signal_index'] ?? 0 );
			$verdict      = sanitize_key( (string) ( $row['verdict'] ?? '' ) );
			$evidence     = $safe_urls( $row['evidence_urls'] ?? array() );
			if ( ! in_array( $signal_index, array( 1, 2, 3 ), true ) || isset( $seen_indexes[ $signal_index ] ) || ! in_array( $verdict, array( 'confirmed', 'changed', 'unresolved' ), true ) || empty( $evidence ) ) {
				return array();
			}
			$seen_indexes[ $signal_index ] = true;
			$review_items[] = array(
				'previous_signal_index' => $signal_index,
				'previous_label' => sanitize_text_field( (string) ( $row['previous_label'] ?? '' ) ),
				'previous_detail' => sanitize_textarea_field( (string) ( $row['previous_detail'] ?? '' ) ),
				'verdict' => $verdict,
				'current_status' => sanitize_textarea_field( (string) ( $row['current_status'] ?? '' ) ),
				'action' => sanitize_textarea_field( (string) ( $row['action'] ?? '' ) ),
				'evidence_urls' => $evidence,
			);
		}
		$valid_review_count = $variable_sections ? ( 1 <= count( $review_items ) && 3 >= count( $review_items ) ) : 3 === count( $review_items );
		$expected_indexes = range( 1, count( $review_items ) );
		$actual_indexes   = array_map( 'intval', array_keys( $seen_indexes ) );
		sort( $actual_indexes );
		if ( ! $valid_review_count || $expected_indexes !== $actual_indexes || ! preg_match( '/^[a-f0-9]{64}$/', $previous_hash ) || '' === $previous_time ) {
			return array();
		}
		usort( $review_items, static function ( $left, $right ) { return $left['previous_signal_index'] <=> $right['previous_signal_index']; } );
		$safe['retrospective'] = array(
			'status' => 'available',
			'previous_generated_at' => $previous_time,
			'previous_snapshot_hash' => $previous_hash,
			'items' => $review_items,
		);
	} elseif ( 'baseline' !== ( $retrospective['status'] ?? 'baseline' ) ) {
		return array();
	}
	foreach ( array_slice( (array) ( $payload['core_signals'] ?? array() ), 0, 3 ) as $row ) {
		$safe['core_signals'][] = array(
			'metric' => sanitize_text_field( (string) ( $row['metric'] ?? '' ) ),
			'label' => sanitize_text_field( (string) ( $row['label'] ?? '' ) ),
			'detail' => sanitize_textarea_field( (string) ( $row['detail'] ?? '' ) ),
			'action' => sanitize_textarea_field( (string) ( $row['action'] ?? '' ) ),
			'tone' => in_array( ( $row['tone'] ?? '' ), array( 'green', 'amber', 'red', 'violet' ), true ) ? $row['tone'] : 'amber',
			'evidence_urls' => $safe_urls( $row['evidence_urls'] ?? array() ),
		);
	}
	foreach ( array_slice( (array) ( $payload['keywords'] ?? array() ), 0, 7 ) as $row ) {
		$safe['keywords'][] = array(
			'keyword' => sanitize_text_field( (string) ( $row['keyword'] ?? '' ) ),
			'score' => min( 10, absint( $row['score'] ?? 0 ) ),
			'direction' => in_array( ( $row['direction'] ?? '' ), array( 'up', 'down', 'stable' ), true ) ? $row['direction'] : 'stable',
			'basis' => sanitize_textarea_field( (string) ( $row['basis'] ?? '' ) ),
		);
	}
	foreach ( array_slice( (array) ( $payload['matrix'] ?? array() ), 0, 4 ) as $row ) {
		$safe['matrix'][] = array(
			'quadrant' => in_array( ( $row['quadrant'] ?? '' ), array( 'focus', 'future', 'apply', 'watch' ), true ) ? $row['quadrant'] : 'watch',
			'label' => sanitize_text_field( (string) ( $row['label'] ?? '' ) ),
			'meaning' => sanitize_textarea_field( (string) ( $row['meaning'] ?? '' ) ),
			'action' => sanitize_textarea_field( (string) ( $row['action'] ?? '' ) ),
			'evidence_urls' => $safe_urls( $row['evidence_urls'] ?? array() ),
		);
	}
	foreach ( array_slice( (array) ( $payload['timeline'] ?? array() ), 0, 4 ) as $row ) {
		$safe['timeline'][] = array(
			'horizon' => in_array( ( $row['horizon'] ?? '' ), array( 'today', 'week', 'month', 'year' ), true ) ? $row['horizon'] : 'today',
			'action' => sanitize_textarea_field( (string) ( $row['action'] ?? '' ) ),
			'reason' => sanitize_textarea_field( (string) ( $row['reason'] ?? '' ) ),
			'evidence_urls' => $safe_urls( $row['evidence_urls'] ?? array() ),
		);
	}
	foreach ( array( 'insight_cards' => 3, 'themes' => 4, 'developer_insights' => 4 ) as $field => $limit ) {
		foreach ( array_slice( (array) ( $payload[ $field ] ?? array() ), 0, $limit ) as $row ) {
			$safe[ $field ][] = array(
				'title' => sanitize_text_field( (string) ( $row['title'] ?? '' ) ),
				'analysis' => sanitize_textarea_field( (string) ( $row['analysis'] ?? '' ) ),
				'action' => sanitize_textarea_field( (string) ( $row['action'] ?? '' ) ),
				'evidence_urls' => $safe_urls( $row['evidence_urls'] ?? array() ),
			);
		}
	}
	foreach ( array_slice( (array) ( $payload['watchlist'] ?? array() ), 0, 3 ) as $row ) {
		$safe['watchlist'][] = array(
			'title' => sanitize_text_field( (string) ( $row['title'] ?? '' ) ),
			'reason' => sanitize_textarea_field( (string) ( $row['reason'] ?? '' ) ),
			'trigger' => sanitize_textarea_field( (string) ( $row['trigger'] ?? '' ) ),
			'evidence_urls' => $safe_urls( $row['evidence_urls'] ?? array() ),
		);
	}
	$translated_urls = array();
	foreach ( array_slice( (array) ( $payload['source_title_translations'] ?? array() ), 0, 60 ) as $row ) {
		$source_url   = esc_url_raw( (string) ( $row['source_url'] ?? '' ) );
		$korean_title = sanitize_text_field( (string) ( $row['korean_title'] ?? '' ) );
		if ( 0 !== strpos( $source_url, 'https://' ) || '' === $korean_title || isset( $translated_urls[ $source_url ] ) ) { continue; }
		$translated_urls[ $source_url ] = true;
		$safe['source_title_translations'][] = array( 'source_url' => $source_url, 'korean_title' => $korean_title );
	}
	foreach ( array_slice( (array) ( $payload['must_read'] ?? array() ), 0, 5 ) as $row ) {
		$source_url = esc_url_raw( (string) ( $row['source_url'] ?? '' ) );
		if ( 0 !== strpos( $source_url, 'https://' ) ) { continue; }
		$safe['must_read'][] = array(
			'title' => sanitize_text_field( (string) ( $row['title'] ?? '' ) ),
			'korean_title' => sanitize_text_field( (string) ( $row['korean_title'] ?? '' ) ),
			'category' => sanitize_text_field( (string) ( $row['category'] ?? '' ) ),
			'source' => sanitize_text_field( (string) ( $row['source'] ?? '' ) ),
			'source_url' => $source_url,
			'why_it_matters' => sanitize_textarea_field( (string) ( $row['why_it_matters'] ?? '' ) ),
			'action' => sanitize_textarea_field( (string) ( $row['action'] ?? '' ) ),
		);
	}
	if ( $variable_sections ) {
		$valid_counts = 1 <= count( $safe['core_signals'] ) && 3 >= count( $safe['core_signals'] )
			&& 3 <= count( $safe['keywords'] ) && 5 >= count( $safe['keywords'] )
			&& 2 >= count( $safe['matrix'] )
			&& 1 <= count( $safe['timeline'] ) && 3 >= count( $safe['timeline'] )
			&& 1 <= count( $safe['insight_cards'] ) && 2 >= count( $safe['insight_cards'] )
			&& 2 >= count( $safe['themes'] ) && 2 >= count( $safe['developer_insights'] )
			&& ! ( $safe['themes'] && $safe['developer_insights'] )
			&& 2 >= count( $safe['watchlist'] )
			&& 3 <= count( $safe['must_read'] ) && 5 >= count( $safe['must_read'] );
		$action_count = 0;
		foreach ( array( 'core_signals', 'matrix', 'timeline', 'insight_cards', 'themes', 'developer_insights', 'must_read' ) as $field ) {
			foreach ( $safe[ $field ] as $row ) {
				$action_count += '' !== ( $row['action'] ?? '' ) ? 1 : 0;
			}
		}
		foreach ( $safe['retrospective']['items'] as $row ) {
			$action_count += '' !== ( $row['action'] ?? '' ) ? 1 : 0;
		}
		if ( ! $valid_counts || 7 < $action_count ) { return array(); }
	} elseif ( 3 !== count( $safe['core_signals'] ) || 7 !== count( $safe['keywords'] ) || 4 !== count( $safe['matrix'] ) || 4 !== count( $safe['timeline'] ) || 5 !== count( $safe['must_read'] ) ) {
		return array();
	}
	return $safe;
}

/**
 * Validate and store a bounded public-safe run manifest from the publisher.
 * Publication already succeeded before this optional observer write occurs.
 *
 * @param WP_REST_Request $request Request.
 * @return WP_REST_Response|WP_Error
 */
function hunt_news_store_briefing_manifest( $request ) {
	$payload = $request->get_json_params();
	if ( ! is_array( $payload ) || 'briefing-manifest.v1' !== ( $payload['contract_version'] ?? '' ) || empty( $payload['complete'] ) ) {
		return new WP_Error( 'invalid_briefing_contract', '완료된 briefing-manifest.v1만 저장할 수 있습니다.', array( 'status' => 400 ) );
	}
	$run_id = sanitize_text_field( (string) ( $payload['run_id'] ?? '' ) );
	if ( ! preg_match( '/^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{10}$/', $run_id ) ) {
		return new WP_Error( 'invalid_briefing_run', 'run_id 형식이 올바르지 않습니다.', array( 'status' => 400 ) );
	}
	$publication_mode = sanitize_key( (string) ( $payload['publication_mode'] ?? 'legacy_top2' ) );
	if ( ! in_array( $publication_mode, array( 'legacy_top2', 'briefing_only' ), true ) ) {
		return new WP_Error( 'invalid_briefing_publication_mode', '브리핑 발행 모드가 올바르지 않습니다.', array( 'status' => 400 ) );
	}
	$published = isset( $payload['published'] ) && is_array( $payload['published'] ) ? $payload['published'] : array();
	$expected_publications = 'briefing_only' === $publication_mode ? 0 : 2;
	if ( $expected_publications !== count( $published ) ) {
		return new WP_Error( 'invalid_briefing_publications', '발행 모드와 검증된 공개 글 수가 일치하지 않습니다.', array( 'status' => 400 ) );
	}
	$safe_posts = array();
	foreach ( $published as $item ) {
		$post_id = absint( $item['post_id'] ?? 0 );
		$post    = get_post( $post_id );
		if ( ! $post || 'post' !== $post->post_type || 'publish' !== $post->post_status ) {
			return new WP_Error( 'invalid_briefing_post', '공개 상태인 WordPress 글만 연결할 수 있습니다.', array( 'status' => 400 ) );
		}
		$safe_posts[] = array(
			'run_id'                        => $run_id,
			'topic_id'                      => sanitize_text_field( (string) ( $item['topic_id'] ?? '' ) ),
			'post_id'                       => $post_id,
			'url'                           => get_permalink( $post ),
			'published_at'                  => sanitize_text_field( (string) ( $item['published_at'] ?? '' ) ),
			'title'                         => get_the_title( $post ),
			'category'                      => sanitize_text_field( (string) ( $item['category'] ?? '' ) ),
			'primary_keyword'               => sanitize_text_field( (string) ( $item['primary_keyword'] ?? '' ) ),
			'selection_track'               => sanitize_key( (string) ( $item['selection_track'] ?? '' ) ),
			'selection_reason'              => sanitize_text_field( (string) ( $item['selection_reason'] ?? '' ) ),
			'reader_action'                 => sanitize_text_field( (string) ( $item['reader_action'] ?? '' ) ),
			'life_impact'                   => sanitize_text_field( (string) ( $item['life_impact'] ?? '' ) ),
			'effective_date'                => sanitize_text_field( (string) ( $item['effective_date'] ?? '' ) ),
			'google_trends_approx_traffic'  => absint( $item['google_trends_approx_traffic'] ?? 0 ),
			'whereispost_total_searches'    => absint( $item['whereispost_total_searches'] ?? 0 ),
			'source_count'                  => min( 20, absint( $item['source_count'] ?? 0 ) ),
			'source_domains'                => array_slice( array_map( 'sanitize_text_field', (array) ( $item['source_domains'] ?? array() ) ), 0, 20 ),
		);
	}
	$top_topics = array();
	foreach ( array_slice( (array) ( $payload['collection']['top_topics'] ?? array() ), 0, 7 ) as $topic ) {
		$name = sanitize_text_field( (string) ( $topic['topic'] ?? '' ) );
		if ( '' !== $name ) {
			$top_topics[] = array(
				'topic'             => $name,
				'approx_traffic'    => absint( $topic['approx_traffic'] ?? 0 ),
				'last_seen_at'      => sanitize_text_field( (string) ( $topic['last_seen_at'] ?? '' ) ),
				'news_source_count' => min( 20, absint( $topic['news_source_count'] ?? 0 ) ),
			);
		}
	}
	$source_items = array();
	foreach ( array_slice( (array) ( $payload['editorial_sources']['items'] ?? array() ), 0, 60 ) as $item ) {
		$url = esc_url_raw( (string) ( $item['url'] ?? '' ) );
		if ( '' === $url || 0 !== strpos( $url, 'https://' ) ) {
			continue;
		}
		$source_items[] = array(
			'category' => sanitize_text_field( (string) ( $item['category'] ?? '' ) ),
			'source' => sanitize_text_field( (string) ( $item['source'] ?? '' ) ),
			'title' => sanitize_text_field( (string) ( $item['title'] ?? '' ) ),
			'url' => $url,
			'published_at' => sanitize_text_field( (string) ( $item['published_at'] ?? '' ) ),
		);
	}
	$safe_analysis = hunt_news_sanitize_daily_analysis( $payload['analysis'] ?? array() );
	if ( empty( $safe_analysis ) ) {
		return new WP_Error( 'invalid_briefing_analysis', '검증된 일일 보고서 분석이 필요합니다.', array( 'status' => 400 ) );
	}
	$safe = array(
		'contract_version'    => 'briefing-manifest.v1',
		'generated_at'        => sanitize_text_field( (string) ( $payload['generated_at'] ?? '' ) ),
		'run_id'              => $run_id,
		'publication_mode'    => $publication_mode,
		'complete'            => true,
		'source_snapshot_hash'=> sanitize_text_field( (string) ( $payload['source_snapshot_hash'] ?? '' ) ),
		'collection'          => array(
			'provider'             => sanitize_key( (string) ( $payload['collection']['provider'] ?? '' ) ),
			'checked_at'           => sanitize_text_field( (string) ( $payload['collection']['checked_at'] ?? '' ) ),
			'status'               => in_array( ( $payload['collection']['status'] ?? '' ), array( 'fresh', 'stale', 'unavailable' ), true ) ? $payload['collection']['status'] : 'unavailable',
			'age_minutes'          => absint( $payload['collection']['age_minutes'] ?? 0 ),
			'retention_hours'      => absint( $payload['collection']['retention_hours'] ?? 0 ),
			'observed_topic_count' => absint( $payload['collection']['observed_topic_count'] ?? 0 ),
			'top_topics'           => $top_topics,
		),
		'editorial_sources'   => array(
			'provider' => sanitize_key( (string) ( $payload['editorial_sources']['provider'] ?? '' ) ),
			'checked_at' => sanitize_text_field( (string) ( $payload['editorial_sources']['checked_at'] ?? '' ) ),
			'successful_source_count' => absint( $payload['editorial_sources']['successful_source_count'] ?? 0 ),
			'source_count' => absint( $payload['editorial_sources']['source_count'] ?? 0 ),
			'items' => $source_items,
		),
		'analysis'            => $safe_analysis,
		'selection'           => array(
			'candidate_count' => absint( $payload['selection']['candidate_count'] ?? 0 ),
			'legacy_top2'     => array_slice( array_map( 'sanitize_text_field', (array) ( $payload['selection']['legacy_top2'] ?? array() ) ), 0, 2 ),
			'shadow_top2'     => array_slice( array_map( 'sanitize_text_field', (array) ( $payload['selection']['shadow_top2'] ?? array() ) ), 0, 2 ),
			'overlap_count'   => min( 2, absint( $payload['selection']['overlap_count'] ?? 0 ) ),
			'shadow_status'   => sanitize_key( (string) ( $payload['selection']['shadow_status'] ?? '' ) ),
			'fallback_used'   => ! empty( $payload['selection']['fallback_used'] ),
		),
		'published'           => $safe_posts,
		'stored_at'           => current_time( 'mysql', true ),
	);
	update_option( 'hunt_news_briefing_manifest', $safe, false );
	$briefing_timestamp = strtotime( $safe['generated_at'] );
	$briefing_date      = wp_date( 'Y-m-d', $briefing_timestamp );
	$existing = get_posts( array( 'post_type' => 'hunt_briefing', 'post_status' => 'any', 'name' => $briefing_date, 'posts_per_page' => 1, 'fields' => 'ids' ) );
	$links = '';
	foreach ( $safe_posts as $safe_post ) {
		$links .= '<li><a href="' . esc_url( $safe_post['url'] ) . '">' . esc_html( $safe_post['title'] ) . '</a></li>';
	}
	$briefing_post = array(
		'ID' => $existing ? absint( $existing[0] ) : 0,
		'post_type' => 'hunt_briefing', 'post_status' => 'publish', 'post_name' => $briefing_date,
		'post_date' => wp_date( 'Y-m-d H:i:s', $briefing_timestamp ),
		'post_date_gmt' => gmdate( 'Y-m-d H:i:s', $briefing_timestamp ),
		'post_title' => 'Hunt News ' . $briefing_date,
		'post_excerpt' => 'AI·개발 기술 변화와 근거, 영향, 지금 할 일을 한 장에 정리한 일일 보고서입니다.',
		'post_content' => '<p>이 날짜의 Hunt News 기술 보고서입니다. 수집 신호, 선정 근거, 영향과 실행 항목을 한 화면에서 확인할 수 있습니다.</p><ul>' . $links . '</ul>',
	);
	$briefing_id = wp_insert_post( wp_slash( $briefing_post ), true );
	if ( ! is_wp_error( $briefing_id ) ) {
		update_post_meta( $briefing_id, '_hunt_news_briefing_manifest', $safe );
	}
	return rest_ensure_response( array( 'stored' => true, 'run_id' => $run_id, 'briefing_id' => is_wp_error( $briefing_id ) ? 0 : $briefing_id, 'briefing_url' => is_wp_error( $briefing_id ) ? '' : get_permalink( $briefing_id ), 'post_ids' => wp_list_pluck( $safe_posts, 'post_id' ) ) );
}

/**
 * Render the briefing-first home and category discovery surfaces.
 */
function hunt_news_home_sections() {
	if ( is_admin() || ! ( is_home() || is_front_page() || is_category() || is_post_type_archive( 'hunt_briefing' ) || is_singular( 'hunt_briefing' ) ) ) {
		return;
	}
	if ( is_home() || is_front_page() ) {
		hunt_news_render_editorial_home();
		return;
	}

	$is_category        = is_category();
	$is_briefing_detail = is_singular( 'hunt_briefing' );

	$brief_posts  = $is_category ? array() : hunt_news_briefing_posts( 12 );
	$manifest     = $is_category ? array() : hunt_news_latest_briefing_manifest();
	if ( is_singular( 'hunt_briefing' ) && $manifest ) {
		$brief_posts = hunt_news_manifest_posts( $manifest );
	}
	$manifest_map = $is_category ? array() : hunt_news_manifest_publications_by_post( $manifest );
	$signal_posts = $is_category ? array() : hunt_news_manifest_signal_posts( $brief_posts, $manifest );
	$keywords     = $is_category ? array() : ( $manifest ? hunt_news_manifest_keywords( $manifest ) : hunt_news_briefing_keywords( $brief_posts, 7 ) );
	$timeline     = $is_category ? array() : hunt_news_briefing_timeline( $brief_posts );
	$analysis     = ( ! $is_category && ! empty( $manifest['analysis'] ) && is_array( $manifest['analysis'] ) ) ? $manifest['analysis'] : array();
	if ( ! empty( $analysis['keywords'] ) ) {
		$keywords = array();
		foreach ( $analysis['keywords'] as $keyword ) {
			$direction = (string) ( $keyword['direction'] ?? 'stable' );
			$keywords[] = array(
				'name' => (string) ( $keyword['keyword'] ?? '' ),
				'label' => (string) absint( $keyword['score'] ?? 0 ) . '/10 ' . ( 'up' === $direction ? '↑' : ( 'down' === $direction ? '↓' : '→' ) ),
				'count' => absint( $keyword['score'] ?? 0 ),
				'percent' => min( 100, absint( $keyword['score'] ?? 0 ) * 10 ),
				'url' => '#hunt-news-source-title',
				'basis' => (string) ( $keyword['basis'] ?? '' ),
			);
		}
	}
	$source_groups = array();
	$must_read_items = array();
	$source_items_by_url = array();
	$source_title_translations = array();
	foreach ( (array) ( $analysis['source_title_translations'] ?? array() ) as $translation ) {
		$translation_url = (string) ( $translation['source_url'] ?? '' );
		if ( $translation_url ) {
			$source_title_translations[ $translation_url ] = (string) ( $translation['korean_title'] ?? '' );
		}
	}
	if ( ! $is_category && $manifest ) {
		foreach ( (array) ( $manifest['editorial_sources']['items'] ?? array() ) as $source_item ) {
			$source_category = (string) ( $source_item['category'] ?? '' );
			$source_url      = (string) ( $source_item['url'] ?? '' );
			if ( $source_url ) {
				$source_items_by_url[ $source_url ] = $source_item;
			}
			if ( in_array( $source_category, array( 'AI/ML 핵심', '개발 트렌드', 'AI 공식 블로그', '국내 IT', '국내 시사' ), true ) ) {
				$source_groups[ $source_category ][] = $source_item;
			}
		}
		if ( ! empty( $analysis['must_read'] ) ) {
			foreach ( $analysis['must_read'] as $item ) {
				$source_url   = (string) ( $item['source_url'] ?? '' );
				$source_match = $source_items_by_url[ $source_url ] ?? array();
				$must_read_items[] = array(
					'category' => (string) ( $source_match['category'] ?? $item['category'] ?? '' ),
					'source' => (string) ( $source_match['source'] ?? $item['source'] ?? '' ),
					'title' => (string) ( $source_match['title'] ?? $item['title'] ?? '' ),
					'korean_title' => (string) ( $item['korean_title'] ?? ( $source_title_translations[ $source_url ] ?? '' ) ),
					'url' => $source_url,
					'published_at' => (string) ( $source_match['published_at'] ?? $analysis['generated_at'] ?? '' ),
					'why_it_matters' => (string) ( $item['why_it_matters'] ?? '' ),
					'action' => (string) ( $item['action'] ?? '' ),
				);
			}
		} else {
			$must_read_categories = array( 'AI/ML 핵심', '개발 트렌드', 'AI 공식 블로그', '국내 IT', '국내 시사' );
			for ( $round = 0; $round < 2; $round++ ) {
				foreach ( $must_read_categories as $must_read_category ) {
					if ( isset( $source_groups[ $must_read_category ][ $round ] ) ) {
						$must_read_items[] = $source_groups[ $must_read_category ][ $round ];
					}
				}
			}
		}
		if ( empty( $analysis['must_read'] ) && count( $must_read_items ) < 10 ) {
			$selected_urls = array_fill_keys( array_filter( array_column( $must_read_items, 'url' ) ), true );
			foreach ( (array) ( $manifest['editorial_sources']['items'] ?? array() ) as $source_item ) {
				$source_url = (string) ( $source_item['url'] ?? '' );
				if ( $source_url && isset( $selected_urls[ $source_url ] ) ) {
					continue;
				}
				$must_read_items[] = $source_item;
				if ( $source_url ) {
					$selected_urls[ $source_url ] = true;
				}
				if ( count( $must_read_items ) >= 10 ) {
					break;
				}
			}
		}
	}
	$briefing_evidence_urls = array();
	foreach ( array( 'core_signals', 'matrix', 'timeline', 'insight_cards', 'themes', 'developer_insights', 'watchlist' ) as $analysis_section ) {
		foreach ( (array) ( $analysis[ $analysis_section ] ?? array() ) as $analysis_row ) {
			foreach ( (array) ( $analysis_row['evidence_urls'] ?? array() ) as $evidence_url ) {
				if ( $evidence_url ) {
					$briefing_evidence_urls[ (string) $evidence_url ] = true;
				}
			}
		}
	}
	foreach ( (array) ( $analysis['must_read'] ?? array() ) as $analysis_row ) {
		$evidence_url = (string) ( $analysis_row['source_url'] ?? '' );
		if ( $evidence_url ) {
			$briefing_evidence_urls[ $evidence_url ] = true;
		}
	}
	if ( ! $briefing_evidence_urls ) {
		foreach ( (array) ( $manifest['editorial_sources']['items'] ?? array() ) as $source_item ) {
			$evidence_url = (string) ( $source_item['url'] ?? '' );
			if ( $evidence_url ) {
				$briefing_evidence_urls[ $evidence_url ] = true;
			}
		}
	}
	$briefing_core_count      = ! empty( $analysis['core_signals'] ) ? count( $analysis['core_signals'] ) : min( 3, count( $signal_posts ) );
	$briefing_timeline_count  = ! empty( $analysis['timeline'] ) ? count( $analysis['timeline'] ) : count( $timeline );
	$briefing_must_read_count = ! empty( $analysis['must_read'] ) ? count( $analysis['must_read'] ) : min( 5, count( $must_read_items ) );
	$must_read_display_count  = min( 5, count( $must_read_items ) );
	$briefing_detail_url      = home_url( '/briefing/' . hunt_news_briefing_display_date( $manifest ) . '/' );
	$latest_explainer         = $is_category ? null : hunt_news_latest_special_post( 'technical-explainer' );
	?>
	<?php if ( ! $is_category && $brief_posts ) : ?>
	<div class="hunt-news-report-shell">
		<?php hunt_news_render_briefing_navigation(); ?>
	<section id="hunt-news-briefing-board" class="hunt-news-briefing-board" aria-labelledby="hunt-news-briefing-title">
		<header class="hunt-news-briefing-board__toolbar">
			<div>
				<p>매일 발행하는 AI·개발 기술 보고서</p>
				<h2 id="hunt-news-briefing-title">Hunt News <?php echo esc_html( hunt_news_briefing_display_date( $manifest ) ); ?></h2>
			</div>
			<div class="hunt-news-briefing-board__date" aria-label="브리핑 기준">
				<strong>DAILY REPORT</strong>
				<span>매일 02시 발행</span>
				<a href="<?php echo esc_url( get_post_type_archive_link( 'hunt_briefing' ) ); ?>">날짜 아카이브</a>
			</div>
		</header>
		<?php if ( $is_briefing_detail && $manifest ) : ?>
		<section id="hunt-news-reader-summary" class="hunt-news-reader-summary" aria-label="오늘 브리핑 구성">
			<div><span>핵심 변화</span><strong><?php echo esc_html( (string) $briefing_core_count ); ?>개</strong><small>오늘 먼저 볼 변화</small></div>
			<div><span>연결된 근거</span><strong><?php echo esc_html( (string) count( $briefing_evidence_urls ) ); ?>개</strong><small>분석에 연결된 원문</small></div>
			<div><span>행동 시점</span><strong><?php echo esc_html( (string) $briefing_timeline_count ); ?>개</strong><small>오늘·이번 주·이번 달·올해 말</small></div>
			<div><span>선별 원문</span><strong><?php echo esc_html( (string) $briefing_must_read_count ); ?>개</strong><small>오늘 읽을 근거</small></div>
		</section>
		<?php endif; ?>

		<div class="hunt-news-briefing-overview<?php echo $is_briefing_detail ? '' : ' hunt-news-briefing-overview--compact'; ?>">
			<section class="hunt-news-signal-panel" aria-labelledby="hunt-news-signal-title">
				<header class="hunt-news-panel-heading">
					<div><span aria-hidden="true">●</span><h3 id="hunt-news-signal-title">핵심 신호</h3></div>
					<p><?php echo $analysis ? '전체 수집원을 종합한 변화와 행동 3개' : '최근 공개 글 중 먼저 읽을 변화 3개'; ?></p>
				</header>
				<div class="hunt-news-signal-list">
					<?php if ( ! empty( $analysis['core_signals'] ) ) : ?>
						<?php foreach ( $analysis['core_signals'] as $signal ) :
							$evidence_url = (string) ( $signal['evidence_urls'][0] ?? '' ); ?>
						<article class="hunt-news-signal-card hunt-news-signal-card--<?php echo esc_attr( (string) $signal['tone'] ); ?>">
							<div class="hunt-news-signal-card__dot" aria-hidden="true"></div>
							<div><p><?php echo esc_html( (string) $signal['metric'] ); ?></p><h4><?php echo esc_html( (string) $signal['label'] ); ?></h4><span><?php echo esc_html( (string) $signal['detail'] ); ?></span></div>
							<a class="hunt-news-signal-card__action" href="<?php echo esc_url( $evidence_url ); ?>" target="_blank" rel="noopener noreferrer"><?php echo esc_html( ! empty( $signal['action'] ) ? (string) $signal['action'] : '근거 원문 보기' ); ?> <b aria-hidden="true">→</b></a>
						</article>
						<?php endforeach; ?>
					<?php else : ?>
					<?php foreach ( $signal_posts as $index => $post ) :
						$category = hunt_news_briefing_category( $post );
						$tones    = array( 'green', 'amber', 'violet' );
						$observed = $manifest_map[ $post->ID ] ?? array();
						$summary  = ! empty( $observed['life_impact'] ) ? $observed['life_impact'] : ( ! empty( $observed['selection_reason'] ) ? $observed['selection_reason'] : hunt_news_briefing_summary( $post ) );
						?>
						<article class="hunt-news-signal-card hunt-news-signal-card--<?php echo esc_attr( $tones[ $index ] ); ?>">
							<div class="hunt-news-signal-card__dot" aria-hidden="true"></div>
							<div>
								<p><a href="<?php echo esc_url( $category['url'] ); ?>"><?php echo esc_html( $category['name'] ); ?></a> · <?php echo esc_html( get_the_date( 'm.d', $post ) ); ?></p>
								<h4><a href="<?php echo esc_url( get_permalink( $post ) ); ?>"><?php echo esc_html( get_the_title( $post ) ); ?></a></h4>
								<span><?php echo esc_html( wp_html_excerpt( $summary, 120, '…' ) ); ?></span>
							</div>
							<a class="hunt-news-signal-card__action" href="<?php echo esc_url( get_permalink( $post ) ); ?>">핵심 확인 <b aria-hidden="true">→</b></a>
						</article>
					<?php endforeach; ?>
					<?php endif; ?>
				</div>
			</section>

			<?php if ( $is_briefing_detail ) : ?>
			<aside class="hunt-news-keyword-panel" aria-labelledby="hunt-news-keyword-title">
				<header class="hunt-news-panel-heading">
					<div><span aria-hidden="true">▥</span><h3 id="hunt-news-keyword-title">오늘의 키워드</h3></div>
					<p><?php echo $manifest ? '브리핑 내 상대 중요도 · 관측 방향' : '최근 글 태그·분야 관측'; ?></p>
				</header>
				<ol class="hunt-news-keyword-list">
					<?php foreach ( $keywords as $index => $keyword ) : ?>
						<li>
							<a href="<?php echo esc_url( $keyword['url'] ); ?>"><span><?php echo esc_html( $keyword['name'] ); ?></span><b><?php echo esc_html( (string) ( $keyword['label'] ?? ( $keyword['count'] . '건' ) ) ); ?></b></a>
							<div aria-hidden="true"><i style="width:<?php echo esc_attr( (string) $keyword['percent'] ); ?>%"></i></div>
						</li>
					<?php endforeach; ?>
				</ol>
			</aside>
			<?php endif; ?>
		</div>

		<?php if ( $is_briefing_detail && 'available' === ( $analysis['retrospective']['status'] ?? '' ) ) :
			$retrospective_counts = array( 'confirmed' => 0, 'changed' => 0, 'unresolved' => 0 );
			$retrospective_change = '';
			foreach ( (array) $analysis['retrospective']['items'] as $review ) {
				$verdict = (string) ( $review['verdict'] ?? 'unresolved' );
				if ( isset( $retrospective_counts[ $verdict ] ) ) {
					$retrospective_counts[ $verdict ]++;
				}
				if ( '' === $retrospective_change && 'changed' === $verdict ) {
					$retrospective_change = (string) ( $review['current_status'] ?? '' );
				}
			}
			$previous_briefing_date = wp_date( 'Y-m-d', strtotime( (string) $analysis['retrospective']['previous_generated_at'] ) );
			$previous_briefing_url  = home_url( '/briefing/' . $previous_briefing_date . '/' ); ?>
		<section class="hunt-news-retrospective" aria-labelledby="hunt-news-retrospective-title">
			<header class="hunt-news-panel-heading">
				<div><span aria-hidden="true">↺</span><h3 id="hunt-news-retrospective-title">어제의 판단 복기</h3></div>
				<p><?php echo esc_html( $previous_briefing_date ); ?> 판단의 변경 여부만 요약합니다</p>
			</header>
			<div class="hunt-news-retrospective__summary">
				<div><strong><?php echo esc_html( (string) $retrospective_counts['confirmed'] ); ?></strong><span>유지</span></div>
				<div><strong><?php echo esc_html( (string) $retrospective_counts['changed'] ); ?></strong><span>변경</span></div>
				<div><strong><?php echo esc_html( (string) $retrospective_counts['unresolved'] ); ?></strong><span>확인 중</span></div>
				<p><?php echo esc_html( $retrospective_change ? wp_html_excerpt( $retrospective_change, 150, '…' ) : '공식 근거가 달라진 판단은 없습니다. 기존 행동 기준을 유지합니다.' ); ?></p>
				<a href="<?php echo esc_url( $previous_briefing_url ); ?>">전날 브리핑과 비교 <b aria-hidden="true">→</b></a>
			</div>
		</section>
		<?php endif; ?>

		<?php if ( $is_briefing_detail ) : ?>
		<section class="hunt-news-action-timeline" aria-labelledby="hunt-news-timeline-title">
			<header class="hunt-news-panel-heading">
				<div><span aria-hidden="true">⚡</span><h3 id="hunt-news-timeline-title">확인 타임라인</h3></div>
				<p>발행 시점에 따라 다시 볼 뉴스를 나눴습니다</p>
			</header>
			<ol>
				<?php if ( ! empty( $analysis['timeline'] ) ) :
					$horizon_labels = array( 'today' => '오늘', 'week' => '이번 주', 'month' => '이번 달', 'year' => '올해 말' ); ?>
					<?php foreach ( $analysis['timeline'] as $row ) : ?>
					<li><span class="hunt-news-action-timeline__marker" aria-hidden="true"></span><strong><?php echo esc_html( $horizon_labels[ $row['horizon'] ] ?? $row['horizon'] ); ?></strong><small><?php echo esc_html( (string) $row['reason'] ); ?></small><?php if ( ! empty( $row['action'] ) ) : ?><span class="hunt-news-action-timeline__action"><?php echo esc_html( (string) $row['action'] ); ?></span><?php endif; ?></li>
					<?php endforeach; ?>
				<?php else : ?>
				<?php foreach ( $timeline as $index => $row ) : ?>
					<li>
						<span class="hunt-news-action-timeline__marker" aria-hidden="true"></span>
						<strong><?php echo esc_html( $row['label'] ); ?></strong>
						<small><?php echo esc_html( $row['description'] ); ?></small>
						<span class="hunt-news-action-timeline__action"><?php echo esc_html( wp_html_excerpt( get_the_title( $row['post'] ), 46, '…' ) ); ?></span>
					</li>
				<?php endforeach; ?>
				<?php endif; ?>
			</ol>
		</section>

		<?php $lead = $brief_posts[0]; ?>
		<section class="hunt-news-focus" aria-labelledby="hunt-news-focus-title">
			<div class="hunt-news-focus__heading">
				<p>Hunt News 한 줄 판단</p>
				<h3 id="hunt-news-focus-title"><?php echo esc_html( $analysis ? (string) $analysis['headline'] : get_the_title( $lead ) ); ?></h3>
				<?php if ( $analysis ) : ?><span><?php echo esc_html( (string) $analysis['summary'] ); ?></span><?php else : ?><a href="<?php echo esc_url( get_permalink( $lead ) ); ?>">전체 내용 읽기 <b aria-hidden="true">→</b></a><?php endif; ?>
			</div>
			<div class="hunt-news-focus__points">
				<?php if ( ! empty( $analysis['insight_cards'] ) ) : ?>
					<?php foreach ( $analysis['insight_cards'] as $point ) : ?>
					<article><span>판단 근거</span><strong><?php echo esc_html( (string) $point['title'] ); ?></strong><p><?php echo esc_html( (string) $point['analysis'] ); ?></p><?php if ( ! empty( $point['action'] ) ) : ?><b class="hunt-news-focus__action"><?php echo esc_html( (string) $point['action'] ); ?></b><?php endif; ?></article>
					<?php endforeach; ?>
				<?php else : ?>
				<?php foreach ( $signal_posts as $index => $post ) :
					$category = hunt_news_briefing_category( $post );
					$observed = $manifest_map[ $post->ID ] ?? array();
					$action   = ! empty( $observed['reader_action'] ) ? $observed['reader_action'] : '지금 확인할 것 보기';
					?>
					<article>
						<span><?php echo esc_html( $category['name'] ); ?></span>
						<strong><?php echo esc_html( wp_html_excerpt( get_the_title( $post ), 44, '…' ) ); ?></strong>
						<b class="hunt-news-focus__action"><?php echo esc_html( wp_html_excerpt( $action, 44, '…' ) ); ?></b>
					</article>
				<?php endforeach; ?>
				<?php endif; ?>
			</div>
		</section>

		<?php if ( ! empty( $analysis['matrix'] ) ) :
			$quadrant_labels = array( 'focus' => '지금 집중', 'future' => '미래 준비', 'apply' => '적용 검토', 'watch' => '계속 관찰' ); ?>
		<section class="hunt-news-decision-matrix" aria-labelledby="hunt-news-decision-matrix-title">
			<header class="hunt-news-panel-heading">
				<div><span aria-hidden="true">⌁</span><h3 id="hunt-news-decision-matrix-title">적용 판단</h3></div>
				<p>무엇을 적용하고 무엇을 더 지켜볼지 나눴습니다</p>
			</header>
			<div class="hunt-news-decision-matrix__grid">
				<?php foreach ( $analysis['matrix'] as $row ) :
					$matrix_evidence_url = (string) ( $row['evidence_urls'][0] ?? '' ); ?>
				<article class="hunt-news-decision-matrix__item hunt-news-decision-matrix__item--<?php echo esc_attr( (string) $row['quadrant'] ); ?>">
					<span><?php echo esc_html( $quadrant_labels[ $row['quadrant'] ] ?? '판단 보류' ); ?></span>
					<h4><?php echo esc_html( (string) $row['label'] ); ?></h4>
					<p><?php echo esc_html( (string) $row['meaning'] ); ?></p>
					<?php if ( ! empty( $row['action'] ) ) : ?><strong><?php echo esc_html( (string) $row['action'] ); ?></strong><?php endif; ?>
					<?php if ( $matrix_evidence_url ) : ?><a href="<?php echo esc_url( $matrix_evidence_url ); ?>" target="_blank" rel="noopener noreferrer">근거 원문 <b aria-hidden="true">→</b></a><?php endif; ?>
				</article>
				<?php endforeach; ?>
			</div>
		</section>
		<?php endif; ?>

		<?php
		$synthesis_rows  = ! empty( $analysis['developer_insights'] ) ? (array) $analysis['developer_insights'] : (array) ( $analysis['themes'] ?? array() );
		$synthesis_title = ! empty( $analysis['developer_insights'] ) ? '개발자 인사이트' : '핵심 테마';
		if ( $synthesis_rows || ! empty( $analysis['watchlist'] ) ) : ?>
		<section class="hunt-news-synthesis" aria-labelledby="hunt-news-synthesis-title">
			<header class="hunt-news-panel-heading">
				<div><span aria-hidden="true">◈</span><h3 id="hunt-news-synthesis-title">판단을 바꾸는 조건</h3></div>
				<p>기사 요약이 아니라 채택 조건과 후속 확인 신호입니다</p>
			</header>
			<div class="hunt-news-synthesis__grid">
				<?php if ( $synthesis_rows ) : ?>
				<section>
					<h4><?php echo esc_html( $synthesis_title ); ?></h4>
					<?php foreach ( $synthesis_rows as $row ) :
						$synthesis_evidence_url = (string) ( $row['evidence_urls'][0] ?? '' ); ?>
					<article>
						<h5><?php echo esc_html( (string) $row['title'] ); ?></h5>
						<p><?php echo esc_html( (string) $row['analysis'] ); ?></p>
						<?php if ( ! empty( $row['action'] ) ) : ?><strong><?php echo esc_html( (string) $row['action'] ); ?></strong><?php endif; ?>
						<?php if ( $synthesis_evidence_url ) : ?><a href="<?php echo esc_url( $synthesis_evidence_url ); ?>" target="_blank" rel="noopener noreferrer">근거 원문 <b aria-hidden="true">→</b></a><?php endif; ?>
					</article>
					<?php endforeach; ?>
				</section>
				<?php endif; ?>
				<?php if ( ! empty( $analysis['watchlist'] ) ) : ?>
				<section class="hunt-news-synthesis__watch">
					<h4>지켜볼 것</h4>
					<?php foreach ( $analysis['watchlist'] as $row ) :
						$watch_evidence_url = (string) ( $row['evidence_urls'][0] ?? '' ); ?>
					<article>
						<h5><?php echo esc_html( (string) $row['title'] ); ?></h5>
						<p><?php echo esc_html( (string) $row['reason'] ); ?></p>
						<strong>다시 판단할 신호 · <?php echo esc_html( (string) $row['trigger'] ); ?></strong>
						<?php if ( $watch_evidence_url ) : ?><a href="<?php echo esc_url( $watch_evidence_url ); ?>" target="_blank" rel="noopener noreferrer">근거 원문 <b aria-hidden="true">→</b></a><?php endif; ?>
					</article>
					<?php endforeach; ?>
				</section>
				<?php endif; ?>
			</div>
		</section>
		<?php endif; ?>
		<?php endif; ?>

		<section class="hunt-news-must-read" aria-labelledby="hunt-news-must-read-title">
			<header class="hunt-news-must-read__header">
				<div><p>Hunt News 선정 오늘의 필독</p><h3 id="hunt-news-must-read-title">지금 놓치면 아쉬운 기술 뉴스</h3></div>
			</header>
			<p class="hunt-news-must-read__status">
				<?php if ( $is_briefing_detail ) : ?>
					공식 원문, 독립 출처와 실무 영향을 대조해 고른 <?php echo esc_html( (string) $must_read_display_count ); ?>개입니다. 전체 수집원은 아래에서 분야별로 확인할 수 있습니다.
				<?php else : ?>
					공식 원문, 독립 출처와 실무 영향을 대조해 고른 <?php echo esc_html( (string) $must_read_display_count ); ?>개입니다. <a href="<?php echo esc_url( $briefing_detail_url ); ?>">전체 보고서와 수집원 보기 <b aria-hidden="true">→</b></a>
				<?php endif; ?>
			</p>
			<div class="hunt-news-must-read__grid" data-brief-view-grid>
				<?php if ( $must_read_items ) : ?>
					<?php foreach ( array_slice( $must_read_items, 0, $must_read_display_count ) as $index => $item ) : ?>
						<article class="hunt-news-brief-card hunt-news-brief-card--source" data-brief-card-kind="must-read">
							<b class="hunt-news-brief-card__rank">#<?php echo esc_html( (string) ( $index + 1 ) ); ?></b>
							<div><span><?php echo esc_html( (string) ( $item['source'] ?? '' ) ); ?></span><time datetime="<?php echo esc_attr( (string) ( $item['published_at'] ?? '' ) ); ?>"><?php echo esc_html( hunt_news_source_time_label( (string) ( $item['published_at'] ?? '' ), (string) ( $analysis['generated_at'] ?? '' ) ) ); ?></time></div>
							<h4><?php echo esc_html( (string) ( $item['title'] ?? '' ) ); ?></h4>
							<?php if ( ! empty( $item['korean_title'] ) && (string) $item['korean_title'] !== (string) ( $item['title'] ?? '' ) ) : ?><p class="hunt-news-source-card__translated">한국어 제목 · <?php echo esc_html( (string) $item['korean_title'] ); ?></p><?php endif; ?>
							<p><?php echo esc_html( ! empty( $item['why_it_matters'] ) ? (string) $item['why_it_matters'] : ( (string) ( $item['category'] ?? '기술 뉴스' ) . ' · 공식 원문과 독립 출처를 확인하세요.' ) ); ?></p>
							<a href="<?php echo esc_url( (string) ( $item['url'] ?? '' ) ); ?>" target="_blank" rel="noopener noreferrer">근거 원문 <b aria-hidden="true">→</b></a>
						</article>
					<?php endforeach; ?>
				<?php else : ?>
					<?php foreach ( array_slice( $brief_posts, 0, 5 ) as $index => $post ) :
						$category = hunt_news_briefing_category( $post );
						?>
						<article class="hunt-news-brief-card">
							<div><span><?php echo esc_html( $category['name'] ); ?></span><time datetime="<?php echo esc_attr( get_the_date( DATE_W3C, $post ) ); ?>"><?php echo esc_html( get_the_date( 'm.d H:i', $post ) ); ?></time></div>
							<h4><a href="<?php echo esc_url( get_permalink( $post ) ); ?>"><?php echo esc_html( get_the_title( $post ) ); ?></a></h4>
							<p><?php echo esc_html( hunt_news_briefing_summary( $post ) ); ?></p>
							<a href="<?php echo esc_url( get_permalink( $post ) ); ?>">브리핑 읽기 <b aria-hidden="true">→</b></a>
						</article>
					<?php endforeach; ?>
				<?php endif; ?>
			</div>
		</section>

		<?php if ( $latest_explainer ) :
			$explainer_category = get_category_by_slug( 'technical-explainer' );
			$explainer_archive  = $explainer_category ? get_category_link( $explainer_category->term_id ) : home_url( '/category/technical-explainer/' );
			?>
		<section class="hunt-news-deep-read" aria-labelledby="hunt-news-deep-read-title">
			<div>
				<p>검색 수요에서 고른 독립 기술 해설</p>
				<h3 id="hunt-news-deep-read-title">이번 주 깊이 읽기</h3>
				<span>뉴스 요약이 아니라 예제, 실패 조건과 적용 판단까지 설명합니다.</span>
			</div>
			<article>
				<time datetime="<?php echo esc_attr( get_the_date( DATE_W3C, $latest_explainer ) ); ?>"><?php echo esc_html( get_the_date( 'Y.m.d', $latest_explainer ) ); ?></time>
				<h4><a href="<?php echo esc_url( get_permalink( $latest_explainer ) ); ?>"><?php echo esc_html( get_the_title( $latest_explainer ) ); ?></a></h4>
				<p><?php echo esc_html( hunt_news_briefing_summary( $latest_explainer ) ); ?></p>
				<div><a href="<?php echo esc_url( get_permalink( $latest_explainer ) ); ?>">해설 읽기 <b aria-hidden="true">→</b></a><a href="<?php echo esc_url( $explainer_archive ); ?>">기술 해설 모아보기</a></div>
			</article>
		</section>
		<?php endif; ?>

		<?php if ( $is_briefing_detail && $source_groups ) : ?>
		<section class="hunt-news-source-board" aria-labelledby="hunt-news-source-title">
			<header class="hunt-news-panel-heading"><div><span aria-hidden="true">▤</span><h3 id="hunt-news-source-title">오늘 수집한 기술 뉴스</h3></div><p>제목은 발견용이며 핵심 사실은 원문에서 확인합니다</p></header>
			<div class="hunt-news-source-board__grid">
				<?php foreach ( array_keys( $source_groups ) as $source_category ) : ?>
				<section class="hunt-news-source-column">
					<h4><?php echo esc_html( $source_category ); ?></h4>
					<?php foreach ( array_slice( $source_groups[ $source_category ], 0, 10 ) as $source_item ) : ?>
					<article><div><span><?php echo esc_html( $source_item['source'] ); ?></span><time datetime="<?php echo esc_attr( (string) $source_item['published_at'] ); ?>"><?php echo esc_html( hunt_news_source_time_label( (string) $source_item['published_at'], (string) ( $analysis['generated_at'] ?? '' ) ) ); ?></time></div><h5><a href="<?php echo esc_url( $source_item['url'] ); ?>" target="_blank" rel="noopener noreferrer"><?php echo esc_html( $source_item['title'] ); ?></a></h5><?php $translated_title = (string) ( $source_title_translations[ (string) $source_item['url'] ] ?? '' ); if ( $translated_title && $translated_title !== (string) $source_item['title'] ) : ?><p class="hunt-news-source-card__translated">한국어 제목 · <?php echo esc_html( $translated_title ); ?></p><?php endif; ?></article>
					<?php endforeach; ?>
				</section>
				<?php endforeach; ?>
			</div>
		</section>
		<?php endif; ?>
	</section>
	</div>
	<?php endif; ?>
	<aside id="hunt-news-home-notices" class="hunt-news-home-notices" aria-label="Hunt News 이용 안내">
		<a class="hunt-news-home-notices__primary" href="<?php echo esc_url( home_url( '/about/' ) ); ?>"><strong>읽는 기준</strong><span>버전·호환성·비용·보안과 지금 할 일부터 확인하세요</span><b aria-hidden="true">→</b></a>
		<a class="hunt-news-home-notices__secondary" href="<?php echo esc_url( home_url( '/editorial-policy/' ) ); ?>"><span>공식 원문, 독립 보도와 직접 검증을 구분합니다</span><b aria-hidden="true">→</b></a>
	</aside>
	<?php if ( $is_category ) { hunt_news_render_popular_news(); } ?>
	<script id="hunt-news-home-sections-position">
	document.addEventListener('DOMContentLoaded',function(){var board=document.getElementById('hunt-news-briefing-board');var notices=document.getElementById('hunt-news-home-notices');var popular=document.getElementById('hunt-news-popular');var main=document.querySelector('#main,main.site-main');if(main&&main.parentNode){var parent=main.parentNode;var heading=document.createElement('div');var shell=document.createElement('div');var primary=document.createElement('div');heading.className='hunt-news-latest-heading';heading.innerHTML='<p>Hunt News Archive</p><h2>분야별 최신 뉴스</h2>';shell.className='hunt-news-content-shell';primary.className='hunt-news-content-shell__primary';if(board){parent.insertBefore(board,main);}if(notices){parent.insertBefore(notices,main);}parent.insertBefore(shell,main);primary.appendChild(heading);primary.appendChild(main);shell.appendChild(primary);if(popular){shell.appendChild(popular);}}if(popular){var toggle=popular.querySelector('.hunt-news-popular__toggle');var desktop=window.matchMedia('(min-width: 1200px)');var tabs=Array.prototype.slice.call(popular.querySelectorAll('[data-popular-tab]'));var panels=Array.prototype.slice.call(popular.querySelectorAll('[data-popular-panel]'));var setTab=function(name,focus){tabs.forEach(function(tab){var active=tab.getAttribute('data-popular-tab')===name;tab.classList.toggle('is-active',active);tab.setAttribute('aria-selected',active?'true':'false');tab.setAttribute('tabindex',active?'0':'-1');if(active&&focus){tab.focus();}});panels.forEach(function(panel){panel.hidden=panel.getAttribute('data-popular-panel')!==name;});};tabs.forEach(function(tab,index){tab.addEventListener('click',function(){setTab(tab.getAttribute('data-popular-tab'),false);});tab.addEventListener('keydown',function(event){var next=index;if(event.key==='ArrowRight'){next=(index+1)%tabs.length;}else if(event.key==='ArrowLeft'){next=(index-1+tabs.length)%tabs.length;}else if(event.key==='Home'){next=0;}else if(event.key==='End'){next=tabs.length-1;}else{return;}event.preventDefault();setTab(tabs[next].getAttribute('data-popular-tab'),true);});});var setOpen=function(open){popular.classList.toggle('is-open',open);toggle.setAttribute('aria-expanded',open?'true':'false');};var syncLayout=function(){popular.classList.remove('is-open');toggle.setAttribute('aria-expanded',desktop.matches?'true':'false');};syncLayout();if(desktop.addEventListener){desktop.addEventListener('change',syncLayout);}toggle.addEventListener('click',function(){if(!desktop.matches){setOpen(!popular.classList.contains('is-open'));}});document.addEventListener('click',function(event){if(!desktop.matches&&popular.classList.contains('is-open')&&!popular.contains(event.target)){setOpen(false);}});document.addEventListener('keydown',function(event){if(event.key==='Escape'&&!desktop.matches&&popular.classList.contains('is-open')){setOpen(false);toggle.focus();}});}});
	</script>
	<script id="hunt-news-report-mode">
	document.addEventListener('DOMContentLoaded',function(){var reportShell=document.querySelector('.hunt-news-report-shell');var board=document.getElementById('hunt-news-briefing-board');var intro=document.getElementById('huntlab-home-intro');var main=document.querySelector('#main,main.site-main');var archiveShell=main?main.closest('.hunt-news-content-shell'):null;if(reportShell&&board&&board.parentNode!==reportShell){reportShell.appendChild(board);}if(reportShell&&intro&&intro.parentNode){intro.insertAdjacentElement('afterend',reportShell);}else if(reportShell&&archiveShell&&archiveShell.parentNode){archiveShell.parentNode.insertBefore(reportShell,archiveShell);}if(document.body.classList.contains('hunt-news-briefing-mode')&&main){main.hidden=true;}var dateNav=document.getElementById('hunt-news-date-nav');var dateToggle=dateNav?dateNav.querySelector('.hunt-news-date-nav__toggle'):null;if(dateNav&&dateToggle){dateToggle.addEventListener('click',function(){var open=dateNav.classList.toggle('is-open');dateToggle.setAttribute('aria-expanded',open?'true':'false');});}});
	</script>
	<?php
}
add_action( 'wp_body_open', 'hunt_news_home_sections', 26 );

/**
 * Add one explicit, measurable share action after article content.
 * The event is recorded only after the native share sheet or link copy succeeds.
 *
 * @param string $content Filtered post content.
 * @return string
 */
function hunt_news_article_share_action( $content ) {
	if ( is_admin() || ! is_singular( 'post' ) || ! in_the_loop() || ! is_main_query() ) {
		return $content;
	}

	$category_action = '';
	$categories      = get_the_category();
	if ( ! empty( $categories ) ) {
		$category_url = get_category_link( $categories[0]->term_id );
		if ( ! is_wp_error( $category_url ) ) {
			$category_action = '<a class="hunt-news-share__category" href="'
				. esc_url( $category_url ) . '">' . esc_html( $categories[0]->name )
				. ' 분야 더 보기</a>';
		}
	}

	return $content . '<aside class="hunt-news-share" aria-labelledby="hunt-news-share-title">'
		. '<div><h2 id="hunt-news-share-title">이 설명이 도움 됐나요?</h2>'
		. '<p>같은 변화가 필요한 사람에게 기사 링크를 전할 수 있습니다.</p></div>'
		. '<div class="hunt-news-share__actions">' . $category_action
		. '<button type="button" class="hunt-news-share__button" data-huntlab-share>기사 공유하기</button></div>'
		. '<p class="hunt-news-share__status" data-huntlab-share-status aria-live="polite"></p>'
		. '</aside>';
}
add_filter( 'the_content', 'hunt_news_article_share_action', 30 );

/**
 * Record a conservative real-reading signal independently of GA4's session
 * classification. The event fires once after 30 visible seconds and 25% depth.
 */
function huntlab_warm_editorial_engaged_read_signal() {
	if ( is_admin() ) {
		return;
	}
	$post_id = is_singular( 'post' ) ? get_queried_object_id() : 0;
	?>
	<script id="huntlab-engaged-read-signal">
	(function(){
		if(window.__huntlabEngagedReadInstalled){return;}
		window.__huntlabEngagedReadInstalled=true;
		var activeMs=0,maxDepth=0,engagedFired=false,completeFired=false;
		var popularPostId=<?php echo wp_json_encode( $post_id ); ?>;
		var popularEndpoint=<?php echo wp_json_encode( rest_url( 'hunt-news/v1/engaged-view' ) ); ?>;
		function tracker(){return window.gtag||window.__gtagTracker;}
		function send(name,params){var track=tracker();if(typeof track==='function'){track('event',name,params||{});return true;}return false;}
		function recordPopularRead(){if(!popularPostId){return;}fetch(popularEndpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:popularPostId}),credentials:'same-origin',keepalive:true}).catch(function(){});}
		function measureDepth(){
			var height=Math.max(document.documentElement.scrollHeight,document.body?document.body.scrollHeight:0,1);
			maxDepth=Math.max(maxDepth,Math.min(100,((window.scrollY+window.innerHeight)/height)*100));
		}
		function articleIsComplete(){
			var article=document.querySelector('main article');
			if(!article){return false;}
			var bottom=article.getBoundingClientRect().bottom+window.scrollY;
			return window.scrollY+window.innerHeight>=bottom-80;
		}
		measureDepth();
		window.addEventListener('scroll',measureDepth,{passive:true});
		document.addEventListener('click',async function(event){
			var shareButton=event.target.closest('[data-huntlab-share]');
			if(shareButton){
				var status=document.querySelector('[data-huntlab-share-status]');
				try{
					if(navigator.share){
						await navigator.share({title:document.title,url:window.location.href});
					}else{
						await navigator.clipboard.writeText(window.location.href);
						if(status){status.textContent='기사 링크를 복사했습니다.';}
					}
					send('huntlab_article_share',{method:navigator.share?'native':'copy',transport_type:'beacon'});
				}catch(error){
					if(error&&error.name!=='AbortError'&&status){status.textContent='공유하지 못했습니다. 주소창의 링크를 복사해 주세요.';}
				}
				return;
			}
			var link=event.target.closest('main a[href],.huntlab-related-articles a[href],.entry-related a[href],.hunt-news-briefing-board a[href],.hunt-news-date-nav a[href]');
			if(!link){return;}
			var destination;
			try{destination=new URL(link.href,window.location.href);}catch(error){return;}
			if(destination.origin!==window.location.origin){
				var briefingArea=link.closest('.hunt-news-must-read')?'must_read':link.closest('.hunt-news-source-board')?'source_board':link.closest('.hunt-news-signal-panel')?'core_signal':'briefing';
				send('huntlab_briefing_source_click',{source_host:destination.hostname,link_area:briefingArea,transport_type:'beacon'});
				return;
			}
			if(destination.pathname===window.location.pathname){return;}
			send('huntlab_internal_click',{
				link_path:destination.pathname,
				link_area:link.closest('.hunt-news-date-nav')?'briefing_archive':link.closest('.huntlab-related-articles,.entry-related')?'related':'content',
				transport_type:'beacon'
			});
		});
		try{
			var visitKey='huntlab_last_visit_at';
			var previous=parseInt(localStorage.getItem(visitKey)||'0',10);
			var now=Date.now();
			localStorage.setItem(visitKey,String(now));
			if(previous&&now-previous>=21600000&&now-previous<=2592000000){
				send('huntlab_return_visit',{days_since_last_visit:Math.max(1,Math.round((now-previous)/86400000)),transport_type:'beacon'});
			}
		}catch(error){}
		window.setInterval(function(){
			if(document.visibilityState!=='visible'){return;}
			activeMs+=1000;
			measureDepth();
			if(!engagedFired&&activeMs>=30000&&maxDepth>=25){
				send('huntlab_engaged_read',{engagement_time_msec:activeMs,read_depth_percent:Math.round(maxDepth),transport_type:'beacon'});
				recordPopularRead();
				engagedFired=true;
			}
			if(!completeFired&&activeMs>=45000&&articleIsComplete()&&send('huntlab_article_complete',{
				engagement_time_msec:activeMs,
				read_depth_percent:Math.round(maxDepth),
				transport_type:'beacon'
			})){completeFired=true;}
		},1000);
	})();
	</script>
	<?php
}
add_action( 'wp_footer', 'huntlab_warm_editorial_engaged_read_signal', 100 );

/**
 * The existing HuntLab navigation and brand plugins print their styles inline.
 * Keep these two brand overrides last without duplicating the full stylesheet.
 */
function huntlab_warm_editorial_late_brand_overrides() {
	?>
	<style id="huntlab-warm-editorial-late-overrides">
		.huntlab-category-tabs{-webkit-backdrop-filter:blur(16px) saturate(120%);backdrop-filter:blur(16px) saturate(120%);background:rgba(255,253,248,.7)!important;border-color:rgba(255,255,255,.72)!important;box-shadow:0 14px 34px rgba(17,25,39,.08)!important}
		.huntlab-category-tabs__link{background:rgba(255,255,255,.58)!important;border-color:rgba(17,25,39,.12)!important;border-radius:2px!important;color:#30343a!important}
		.huntlab-category-tabs__link:hover,.huntlab-category-tabs__link:focus-visible{background:rgba(255,255,255,.9)!important;border-color:#111820!important;color:#111820!important}
		.huntlab-category-tabs__link.is-active{background:#111820!important;border-color:#111820!important;color:#fff!important}
		.site-branding .brand::before{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 96 40'%3E%3Cg fill='%23292621'%3E%3Cpath d='M24 13C34 9 61 9 70 14c4 2 7 1 12-4 1 7-2 11-9 14v6h-7l-1-6H36l-2 7h-7l1-9c-4-2-6-5-6-8l2-1Z'/%3E%3Cpath d='M25 13c-2-7-11-9-17-3l-5 4 6 3c-1 7 5 11 13 8l7-5-4-7Z'/%3E%3Cpath d='M14 8c-6 3-5 12 2 15 3-5 5-11 3-14l-5-1Z' fill='%23a95f49'/%3E%3Ccircle cx='10' cy='13' r='1.4' fill='%23fffaf2'/%3E%3C/g%3E%3C/svg%3E")!important}
	</style>
	<?php
}
add_action( 'wp_head', 'huntlab_warm_editorial_late_brand_overrides', 100 );

/**
 * Keep the editorial byline and AIOSEO knowledge graph on one organization.
 * AIOSEO documents `aioseo_schema_output` as its supported graph filter.
 *
 * @param array $graphs AIOSEO JSON-LD graph nodes.
 * @return array
 */
function hunt_news_editorial_organization_schema( $graphs ) {
	if ( ! is_array( $graphs ) ) {
		return $graphs;
	}

	$organization_id = home_url( '/#organization' );
	$organization     = array(
		'@type'       => 'Organization',
		'@id'         => $organization_id,
		'name'        => 'Hunt News 편집팀',
		'url'         => home_url( '/' ),
		'description' => 'AI와 개발 기술의 변경점을 공식 원문, 비교, 예제와 실패 조건으로 검증해 실제 적용 여부를 판단할 수 있게 설명합니다.',
		'sameAs'      => array( 'https://github.com/sungpyo9053/blog' ),
		'logo'        => array(
			'@type' => 'ImageObject',
			'url'   => plugins_url( 'assets/huntlab-site-icon.png', __FILE__ ),
		),
	);
	$filtered         = array();

	foreach ( $graphs as $graph ) {
		if ( ! is_array( $graph ) ) {
			$filtered[] = $graph;
			continue;
		}
		$type  = isset( $graph['@type'] ) ? (array) $graph['@type'] : array();
		$id    = isset( $graph['@id'] ) ? (string) $graph['@id'] : '';
		$is_old_identity = in_array( 'Person', $type, true ) && false !== strpos( $id, '#person' );
		if ( $is_old_identity ) {
			continue;
		}
		if ( array_intersect( array( 'Article', 'BlogPosting', 'NewsArticle' ), $type ) ) {
			$graph['author']    = array( '@id' => $organization_id );
			$graph['publisher'] = array( '@id' => $organization_id );
		}
		if ( in_array( 'WebSite', $type, true ) ) {
			$graph['publisher'] = array( '@id' => $organization_id );
		}
		$filtered[] = $graph;
	}

	$filtered[] = $organization;
	return $filtered;
}
add_filter( 'aioseo_schema_output', 'hunt_news_editorial_organization_schema', 20 );

/**
 * Link the public editorial byline to the page that explains responsibility,
 * verification and corrections instead of an opaque account archive.
 *
 * @param string $url Existing author URL.
 * @return string
 */
function hunt_news_editorial_author_link( $url ) {
	if ( is_admin() ) {
		return $url;
	}
	return home_url( '/about/' );
}
add_filter( 'author_link', 'hunt_news_editorial_author_link', 20 );
add_filter( 'kadence_author_use_profile_link', '__return_false', 20 );

/**
 * Keep the visible byline aligned with the public organization identity.
 *
 * @param string $name Existing author display name.
 * @return string
 */
function hunt_news_editorial_author_name( $name ) {
	if ( is_admin() ) {
		return $name;
	}
	return 'Hunt News 편집팀';
}
add_filter( 'the_author', 'hunt_news_editorial_author_name', 20 );
add_filter( 'get_the_author_display_name', 'hunt_news_editorial_author_name', 20 );

/**
 * Localize the small set of Kadence archive labels still visible in English.
 *
 * @param string $translated Translated text.
 * @param string $text       Source text.
 * @return string
 */
function hunt_news_translate_archive_labels( $translated, $text ) {
	$labels = array(
		'By'              => '작성자',
		'Read More'       => '더 읽기',
		'Continue'        => '계속 읽기',
		'Page navigation' => '페이지 탐색',
		'Next Page'       => '다음 페이지',
		'Previous Page'   => '이전 페이지',
		'Open menu'       => '메뉴 열기',
		'Previous'        => '이전 글',
		'Next'            => '다음 글',
		'Similar Posts'   => '비슷한 글',
		'Post Tags:'      => '글 태그:',
		'Go to last slide'       => '마지막 슬라이드로 이동',
		'Select a slide to show' => '표시할 슬라이드 선택',
		'Go to slide %d'         => '%d번 슬라이드로 이동',
		'Leave a comment...'     => '댓글을 남겨주세요…',
		'Comment *'              => '댓글 *',
		'Name'                   => '이름',
		'Email'                  => '이메일',
		'Website'                => '웹사이트',
	);

	return isset( $labels[ $text ] ) ? $labels[ $text ] : $translated;
}
add_filter( 'gettext', 'hunt_news_translate_archive_labels', 20, 2 );
