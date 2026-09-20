<?php
/** Curated starting points; the latest-post list remains a separate dynamic query. */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function huntlab_physical_starting_posts() {
	$starts = array( 'physical-ai-basics' => 761, 'physical-ai-principles' => 773, 'physical-ai-frameworks' => 768, 'physical-ai-experiments' => 771 );
	$published = array();
	foreach ( $starts as $slug => $id ) {
		$post = get_post( $id );
		if ( $post && $post->post_type === 'post' && $post->post_status === 'publish' && ! $post->post_password && has_category( $slug, $post ) ) {
			$published[ $slug ] = $post;
		}
	}
	return $published;
}

/** Display-only navigation: never change stored article content or briefing output. */
function huntlab_physical_learning_navigation( $content ) {
	if ( ! is_singular( 'post' ) || ! in_the_loop() || ! is_main_query() || is_feed() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ) ) { return $content; }
	$starts = huntlab_physical_starting_posts();
	$slugs = array( 'physical-ai-basics', 'physical-ai-principles', 'physical-ai-frameworks', 'physical-ai-experiments' );
	if ( ! has_category( $slugs, get_the_ID() ) ) { return $content; }
	$posts = array_values( $starts );
	$position = array_search( get_the_ID(), array_map( function ( $post ) { return (int) $post->ID; }, $posts ), true );
	ob_start();
	?>
	<nav class="huntlab-learning-navigation" aria-label="피지컬 AI 학습 안내"><h2>이어서 읽기</h2>
	<p>기초 → 원리 → 도구 → 실습 순서로 시작하거나, 필요한 주제를 골라 읽으세요.</p>
	<div class="huntlab-learning-neighbors">
	<?php if ( false !== $position ) : foreach ( array( -1 => '이전 학습', 1 => '다음 학습' ) as $offset => $label ) : $neighbor = $posts[ $position + $offset ] ?? null; if ( ! $neighbor ) { continue; } ?>
	<a href="<?php echo esc_url( get_permalink( $neighbor ) ); ?>"><span><?php echo esc_html( $label ); ?></span><?php echo esc_html( get_the_title( $neighbor ) ); ?></a>
	<?php endforeach; endif; ?>
	</div><a href="<?php echo esc_url( home_url( '/#learning-path' ) ); ?>">입문 글 4개 주제 살펴보기 →</a>
	</nav>
	<?php
	return $content . ob_get_clean();
}
add_filter( 'the_content', 'huntlab_physical_learning_navigation', 40 );
