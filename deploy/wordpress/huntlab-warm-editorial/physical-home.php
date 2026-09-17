<?php
/** Physical AI learning entry. Never imply unpublished lessons are available. */
if ( ! defined( 'ABSPATH' ) ) { exit; }
get_header();
$tracks = array(
 'physical-ai-basics' => array( '피지컬 AI 기초', '용어와 큰 그림', '처음 만나는 개념부터, 다음 글을 이해할 바탕까지.' ),
 'physical-ai-principles' => array( '원리·알고리즘', '왜 그렇게 움직일까', '인식, 판단, 행동과 피드백을 예제로 연결합니다.' ),
 'physical-ai-frameworks' => array( '프레임워크·라이브러리', '도구를 이해하고 선택하기', '역할과 구조, 적용 조건을 공식 자료와 대조합니다.' ),
 'physical-ai-experiments' => array( '실습·실험', '작게 실행하고 확인하기', '준비 환경부터 결과와 한계까지 따라갑니다.' ),
);
$selected = is_category() ? get_queried_object()->slug : '';
$terms = array(); $ids = array();
foreach ( $tracks as $slug => $track ) {
 $term = get_category_by_slug( $slug );
 if ( $term ) { $terms[ $slug ] = $term; $ids[] = $term->term_id; }
}
$query_ids = $selected ? ( isset( $terms[ $selected ] ) ? array( $terms[ $selected ]->term_id ) : array() ) : $ids;
// Static front pages may use `page`; category archives use `paged`.
$page = max( 1, (int) get_query_var( 'paged' ), (int) get_query_var( 'page' ) );
$lessons = $query_ids ? new WP_Query( array( 'post_type' => 'post', 'post_status' => 'publish', 'category__in' => $query_ids, 'posts_per_page' => 12, 'paged' => $page, 'ignore_sticky_posts' => true ) ) : null;
?>
<div id="main" class="huntlab-physical-home">
 <?php if ( ! $selected ) : ?>
 <header class="huntlab-physical-hero">
  <div><p class="huntlab-physical-kicker">HUNTLAB / PHYSICAL AI</p><h1>피지컬 AI,<br>기초에서 실습까지.</h1><p class="huntlab-physical-lead">AI가 세상을 이해하고 움직이는 원리.<br>낯선 용어부터 알고리즘과 도구까지, 예제로 연결합니다.</p><div class="huntlab-tool-actions"><a class="huntlab-primary-link" href="#learning-path">처음 시작하기</a><a href="#physical-articles">공개된 글 보기 ↓</a></div></div>
  <figure><img src="<?php echo esc_url( plugins_url( 'assets/physical-ai-hero.png', __FILE__ ) ); ?>" width="1672" height="941" fetchpriority="high" decoding="async" alt="카메라로 블록을 인식하고 이동 경로를 계획하는 로봇 팔의 개념 일러스트"><figcaption>AI 생성 개념 일러스트 · 실제 실험 사진이 아닙니다.</figcaption></figure>
 </header>
 <?php else : ?>
 <header><p><a href="<?php echo esc_url( home_url( '/' ) ); ?>">HuntLab</a> / 학습 주제</p><h1><?php echo esc_html( $tracks[ $selected ][0] ?? single_cat_title( '', false ) ); ?></h1><p><?php echo esc_html( $tracks[ $selected ][2] ?? '' ); ?></p></header>
 <?php endif; ?>
 <section id="learning-path" aria-labelledby="learning-heading"><div class="huntlab-section-heading"><p>LEARNING PATH</p><h2 id="learning-heading">기초부터, 한 단계씩.</h2><p>순서는 학습 안내입니다. 아직 공개되지 않은 과정은 준비 중으로 표시합니다.</p></div><div class="huntlab-learning-grid">
 <?php $step = 0; foreach ( $tracks as $slug => $track ) : ++$step; $term = $terms[ $slug ] ?? null; ?>
  <article><span class="huntlab-step">0<?php echo (int) $step; ?></span><p><?php echo esc_html( $track[0] ); ?></p><h3><?php echo esc_html( $track[1] ); ?></h3><p><?php echo esc_html( $track[2] ); ?></p><?php if ( $term && $term->count > 0 ) : ?><a href="<?php echo esc_url( get_category_link( $term->term_id ) ); ?>"><?php echo (int) $term->count; ?>편 읽기 →</a><?php else : ?><span class="huntlab-track-pending">첫 글 준비 중</span><?php endif; ?></article>
 <?php endforeach; ?></div></section>
 <section id="physical-articles" aria-labelledby="physical-articles-heading"><div class="huntlab-section-heading"><p>READ &amp; BUILD</p><h2 id="physical-articles-heading">이해에서 실습으로</h2></div><div class="huntlab-note-grid">
 <?php if ( $lessons && $lessons->have_posts() ) : foreach ( $lessons->posts as $entry ) : ?>
  <article class="huntlab-note-card"><p class="huntlab-eyebrow"><?php echo esc_html( get_the_date( 'Y.m.d', $entry ) ); ?> · 약 <?php echo (int) hunt_news_reading_minutes( $entry ); ?>분</p><h3><a href="<?php echo esc_url( get_permalink( $entry ) ); ?>"><?php echo esc_html( get_the_title( $entry ) ); ?></a></h3><p><?php echo esc_html( wp_strip_all_tags( get_the_excerpt( $entry ) ) ); ?></p></article>
 <?php endforeach; else : ?>
  <p class="huntlab-content-pending">피지컬 AI 입문 시리즈를 준비하고 있습니다. 출처와 예제를 검토한 글부터 공개합니다. 기존 운영 글은 아래 아카이브에서 읽을 수 있습니다.</p>
 <?php endif; ?></div>
 <?php if ( $lessons && $lessons->max_num_pages > 1 ) : ?><nav aria-label="글 목록 페이지"><?php echo wp_kses_post( paginate_links( array( 'total' => $lessons->max_num_pages, 'current' => $page ) ) ); ?></nav><?php endif; ?>
 </section>
 <section class="huntlab-editorial-promise" aria-labelledby="promise-heading"><h2 id="promise-heading">쉽게 설명하고, 확인한 만큼만 말합니다.</h2><p>기초 용어는 예시와 함께 설명합니다. 공식 자료 해설, 시뮬레이션, 실제 장비 실험을 구분하고, 실행한 예제에는 환경·버전·결과와 한계를 남깁니다.</p><a href="<?php echo esc_url( home_url( '/editorial-policy/' ) ); ?>">현재 공개된 편집·정정 원칙 →</a></section>
 <section id="operations-archive" class="huntlab-operations-archive"><h2>이전 운영 노트</h2><p>WordPress 운영과 자동화 기록은 별도 아카이브로 보존합니다.</p><nav aria-label="기존 운영 글"><a href="<?php echo esc_url( home_url( '/category/rest-api-publishing/' ) ); ?>">REST API 발행</a><a href="<?php echo esc_url( home_url( '/category/automation-testing/' ) ); ?>">자동화·테스트</a><a href="<?php echo esc_url( home_url( '/category/wordpress-operations/' ) ); ?>">WordPress 운영</a><a href="<?php echo esc_url( home_url( '/wordpress-response-check/' ) ); ?>">응답 진단 도구</a></nav></section>
</div>
<?php get_footer(); ?>
