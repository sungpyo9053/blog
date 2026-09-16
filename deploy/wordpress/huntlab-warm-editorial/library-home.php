<?php
/** Custom homepage: no empty theme loop, including when JavaScript is off. */
if ( ! defined( 'ABSPATH' ) ) { exit; }
get_header();
$topics = array( 'rest-api-publishing' => 'REST API 발행', 'automation-testing' => '자동화·테스트', 'wordpress-operations' => 'WordPress 운영' );
$selected = is_category() ? get_queried_object()->slug : '';
$all_posts = hunt_news_verified_posts( 100 );
$counts = array_fill_keys( array_keys( $topics ), 0 );
foreach ( $all_posts as $entry ) {
	foreach ( $topics as $slug => $label ) { if ( has_category( $slug, $entry ) ) { ++$counts[ $slug ]; } }
}
?>
<div id="main" class="huntlab-library-entry">
	<?php if ( ! $selected ) : ?>
	<header class="huntlab-library-intro"><p>HUNTLAB / WORDPRESS 운영 노트</p><h1>자동발행이 멈췄을 때,<br>응답부터 확인하세요.</h1><p>성공처럼 보이는 HTML 응답, 재시도 중복, 목록 누락과 sitemap 충돌. 직접 실행할 수 있는 검사와 코드로 원인을 좁혀갑니다.</p><div class="huntlab-tool-actions"><a class="huntlab-primary-link" href="<?php echo esc_url( home_url( '/wordpress-response-check/' ) ); ?>">내 응답 검사하기</a><a href="#hunt-news-latest-verified">문제 해결 글 읽기 ↓</a></div></header>
	<section class="huntlab-start-here" aria-labelledby="huntlab-start-title"><h2 id="huntlab-start-title">어디서 막혔나요?</h2><div>
		<article><h3>성공 코드인데 글이 없어요</h3><p>HTTP 상태 → Content-Type → JSON 글 ID → 공개 상태 순서로 확인합니다.</p><a href="<?php echo esc_url( home_url( '/wordpress-rest-html-200-validation/' ) ); ?>">응답 판별 순서</a></article>
		<article><h3>다시 보내도 되는지 모르겠어요</h3><p>429의 대기 시간과 이미 저장됐을 수 있는 POST 타임아웃을 구분합니다.</p><a href="<?php echo esc_url( home_url( '/wordpress-rest-api-retry/' ) ); ?>">재시도 판단 기준</a></article>
		<article><h3>전체 글을 가져오지 못해요</h3><p>응답 헤더의 전체 건수와 페이지마다 가져온 고유 ID 수를 대조합니다.</p><a href="<?php echo esc_url( home_url( '/wordpress-rest-api-pagination/' ) ); ?>">목록 누락 찾기</a></article>
		<article><h3>검색 제외 글이 sitemap에 남아요</h3><p>robots 설정과 sitemap의 URL 목록을 같은 배포에서 확인합니다.</p><a href="<?php echo esc_url( home_url( '/wordpress-noindex-sitemap-consistency/' ) ); ?>">배포 상태 대조하기</a></article>
	</div></section>
	<?php else : ?>
	<header class="huntlab-library-intro"><p><a href="<?php echo esc_url( home_url( '/' ) ); ?>">HuntLab 홈</a> / 이전 운영 노트</p><h1><?php echo esc_html( $topics[ $selected ] ); ?></h1><p><?php echo esc_html( wp_strip_all_tags( category_description() ) ); ?></p></header>
	<?php endif; ?>
	<section id="hunt-news-latest-verified" class="huntlab-library-list" aria-labelledby="huntlab-list-heading">
		<header><p class="huntlab-eyebrow">실패 원인부터 적용 한계까지</p><h2 id="huntlab-list-heading"><?php echo $selected ? esc_html( $topics[ $selected ] . ' 기록' ) : '문제 해결 글'; ?></h2></header>
		<nav class="huntlab-topic-tabs" aria-label="글 주제 선택"><a href="<?php echo esc_url( home_url( '/#operations-archive' ) ); ?>">아카이브 안내</a><?php foreach ( $topics as $slug => $label ) : $term = get_category_by_slug( $slug ); if ( ! $term ) { continue; } ?><a href="<?php echo esc_url( get_category_link( $term->term_id ) ); ?>" <?php if ( $selected === $slug ) { echo 'aria-current="page"'; } ?>><?php echo esc_html( $label ); ?> <span><?php echo esc_html( $counts[ $slug ] ); ?></span></a><?php endforeach; ?></nav>
		<div class="huntlab-note-grid"><?php foreach ( $all_posts as $entry ) : if ( $selected && ! has_category( $selected, $entry ) ) { continue; } $meta = hunt_news_case_meta( $entry ); ?>
			<article class="huntlab-note-card"><p class="huntlab-eyebrow"><?php echo esc_html( $meta['problem_group'] ); ?></p><h3><a href="<?php echo esc_url( get_permalink( $entry ) ); ?>"><?php echo esc_html( get_the_title( $entry ) ); ?></a></h3><p><?php echo esc_html( wp_strip_all_tags( get_the_excerpt( $entry ) ) ); ?></p><footer><span><?php echo esc_html( $meta['method'] ); ?></span><small>근거 기준 <?php echo esc_html( $meta['date'] ); ?> · 약 <?php echo esc_html( hunt_news_reading_minutes( $entry ) ); ?>분</small></footer></article>
		<?php endforeach; ?></div>
	</section>
	<section class="huntlab-method"><h2>검증 범위를 읽는 방법</h2><p>통제된 예제로 확인한 결과와 실제 서버에서 관측한 결과는 범위가 다릅니다. 각 글의 실행 조건, 공개 코드와 제한 사항을 먼저 확인하세요. 예제 성공만으로 자신의 운영 서버에서도 해결됐다고 판단하지 않습니다.</p><p><a href="<?php echo esc_url( home_url( '/about/' ) ); ?>">누가 어떻게 만드는지</a> · <a href="<?php echo esc_url( home_url( '/contact/' ) ); ?>">적용 중 발견한 오류 알려주기</a></p></section>
</div>
<?php get_footer(); ?>
