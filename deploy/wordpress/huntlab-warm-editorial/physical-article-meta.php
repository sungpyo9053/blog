<?php
/** Display-only editorial context. Publication dates are not verification dates. */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function huntlab_physical_article_meta_eligible() {
	if ( is_admin() || is_feed() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ) || ! is_singular( 'post' ) ) { return false; }
	$post = get_post();
	if ( ! $post || 'post' !== $post->post_type || 'publish' !== $post->post_status || $post->post_password ) { return false; }
	if ( ! has_category( array( 'physical-ai-basics', 'physical-ai-principles', 'physical-ai-frameworks', 'physical-ai-experiments' ), $post ) ) { return false; }
	// The legacy verified-case header already provides an editorial context panel.
	return ! ( function_exists( 'hunt_news_is_verified_case' ) && hunt_news_is_verified_case( $post ) );
}

function huntlab_physical_article_meta_assets() {
	if ( ! huntlab_physical_article_meta_eligible() ) { return; }
	wp_enqueue_style( 'huntlab-physical-article-meta', plugins_url( 'assets/physical-article-meta.css', __FILE__ ), array(), (string) filemtime( __DIR__ . '/assets/physical-article-meta.css' ) );
}
add_action( 'wp_enqueue_scripts', 'huntlab_physical_article_meta_assets', 120 );

function huntlab_physical_article_meta( $content ) {
	if ( ! huntlab_physical_article_meta_eligible() || ! in_the_loop() || ! is_main_query() || strpos( $content, 'class="huntlab-physical-article-meta"' ) !== false ) { return $content; }
	$post = get_post();
	$published = get_post_datetime( $post, 'date' );
	$modified = get_post_datetime( $post, 'modified' );
	ob_start();
	?>
	<aside class="huntlab-physical-article-meta" aria-label="글 작성과 수정 안내">
		<div class="huntlab-physical-article-meta__dates">
		<?php if ( $published ) : ?><span>게시 <time datetime="<?php echo esc_attr( $published->format( DATE_W3C ) ); ?>"><?php echo esc_html( $published->format( 'Y.m.d H:i T' ) ); ?></time></span><?php endif; ?>
		<?php if ( $published && $modified && $modified->getTimestamp() > $published->getTimestamp() ) : ?><span>수정 <time datetime="<?php echo esc_attr( $modified->format( DATE_W3C ) ); ?>"><?php echo esc_html( $modified->format( 'Y.m.d H:i T' ) ); ?></time></span><?php endif; ?>
		</div>
		<p>날짜는 게시·수정 시점이다. 자료 확인일과 실행 환경은 본문에서 구분해 확인한다.</p>
		<nav aria-label="작성 방식과 정정 안내"><a href="<?php echo esc_url( home_url( '/about/' ) ); ?>">운영자·AI 활용과 작성 방식</a><a href="<?php echo esc_url( home_url( '/editorial-policy/' ) ); ?>">근거 확인·정정 원칙</a><a href="<?php echo esc_url( home_url( '/contact/' ) ); ?>">오류 제보</a></nav>
	</aside>
	<?php
	return ob_get_clean() . $content;
}
add_filter( 'the_content', 'huntlab_physical_article_meta', 9 );
