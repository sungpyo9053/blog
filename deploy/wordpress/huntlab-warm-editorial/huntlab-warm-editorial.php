<?php
/**
 * Plugin Name: Hunt News Warm Editorial Theme
 * Description: Applies Hunt News's approachable editorial layout without replacing the active WordPress theme.
 * Version: 2.8.1
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
 * Return category-specific editorial context for the archive hero.
 *
 * @return array<string, array{label:string,title:string,description:string,promises:array<int,string>,image:string,alt:string}>
 */
function huntlab_warm_editorial_category_intros() {
	return array(
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
	if ( is_admin() || ! ( is_home() || is_front_page() || is_category() ) ) {
		return;
	}

	$is_category = is_category();
	$intro       = null;

	if ( $is_category ) {
		$category = get_queried_object();
		$intros   = huntlab_warm_editorial_category_intros();
		$slug     = isset( $category->slug ) ? (string) $category->slug : '';
		$intro    = isset( $intros[ $slug ] ) ? $intros[ $slug ] : null;
		if ( ! $intro ) {
			return;
		}
	}
	?>
	<section id="huntlab-home-intro" class="huntlab-home-intro<?php echo $is_category ? ' huntlab-home-intro--category' : ''; ?>" aria-labelledby="huntlab-home-intro-title">
		<div class="huntlab-home-intro__copy">
			<p class="huntlab-home-intro__eyebrow"><?php echo $is_category ? esc_html( 'Hunt News · ' . $intro['label'] ) : 'Hunt News · 생활 변화 설명서'; ?></p>
			<h1 id="huntlab-home-intro-title"><?php echo $is_category ? wp_kses( $intro['title'], array( 'br' => array() ) ) : '복잡한 변화가,<br>내 생활에 닿는 순간.'; ?></h1>
			<p class="huntlab-home-intro__description"><?php echo $is_category ? esc_html( $intro['description'] ) : '정책, 경제, 부동산, 사회, 정치, 문화·엔터와 IT의 변화를 어려운 말 대신 실제 대상·금액·시점·내가 할 일로 설명합니다.'; ?></p>
			<ul class="huntlab-home-intro__promises" aria-label="<?php echo esc_attr( $is_category ? $intro['label'] . ' 콘텐츠 원칙' : 'Hunt News 콘텐츠 원칙' ); ?>">
				<?php foreach ( $is_category ? $intro['promises'] : array( '얼마나 달라지나', '언제부터 적용되나', '나는 무엇을 하나' ) as $promise ) : ?>
					<li><?php echo esc_html( $promise ); ?></li>
				<?php endforeach; ?>
			</ul>
		</div>
		<?php if ( $is_category ) : ?>
			<figure class="huntlab-home-intro__visual">
				<img src="<?php echo esc_url( plugins_url( 'assets/categories/' . $intro['image'], __FILE__ ) ); ?>" width="1000" height="563" alt="<?php echo esc_attr( $intro['alt'] ); ?>" loading="eager" decoding="async" fetchpriority="high">
			</figure>
		<?php else : ?>
			<figure class="huntlab-home-intro__visual huntlab-home-intro__visual--home">
				<img src="<?php echo esc_url( plugins_url( 'assets/hunt-news-life-impact-hero.webp', __FILE__ ) ); ?>" width="1600" height="900" alt="정책과 경제 변화가 휴대전화, 달력, 지갑, 교통과 주유 같은 일상으로 이어지는 미니어처" loading="eager" decoding="async" fetchpriority="high">
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
 * @param int $limit Maximum number of rows.
 * @return array<int, array{post:WP_Post,count:int}>
 */
function hunt_news_popular_rows( $limit = 10 ) {
	$stats  = get_option( 'hunt_news_popular_reads', array() );
	$days   = isset( $stats['days'] ) && is_array( $stats['days'] ) ? $stats['days'] : array();
	$totals = array();
	$today  = current_time( 'timestamp', true );
	$today_key = gmdate( 'Y-m-d', $today );
	$yesterday_key = gmdate( 'Y-m-d', $today - DAY_IN_SECONDS );

	for ( $offset = 0; $offset < 7; $offset++ ) {
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
	$rows  = hunt_news_popular_rows();
	$stats = get_option( 'hunt_news_popular_reads', array() );
	?>
	<section id="hunt-news-popular" class="hunt-news-popular" aria-labelledby="hunt-news-popular-title">
		<header class="hunt-news-popular__header">
			<h2 id="hunt-news-popular-title" class="screen-reader-text">우리 인기뉴스</h2>
			<div class="hunt-news-popular__tabs" aria-hidden="true"><strong>실시간 인기</strong><span>최근 7일</span></div>
		</header>
		<?php if ( $rows ) : ?>
			<ol class="hunt-news-popular__list">
				<?php foreach ( $rows as $index => $row ) : ?>
					<?php $short_title = wp_html_excerpt( wp_strip_all_tags( get_the_title( $row['post'] ) ), 34, '…' ); ?>
					<?php $trend_label = 'up' === $row['trend'] ? '상승' : ( 'down' === $row['trend'] ? '하락' : '변동 없음' ); ?>
					<?php $trend_arrow = 'up' === $row['trend'] ? '↑' : ( 'down' === $row['trend'] ? '↓' : '→' ); ?>
					<li><a href="<?php echo esc_url( get_permalink( $row['post'] ) ); ?>" aria-label="<?php echo esc_attr( get_the_title( $row['post'] ) . ', ' . $trend_label ); ?>"><strong><?php echo esc_html( (string) ( $index + 1 ) ); ?></strong><span><?php echo esc_html( $short_title ); ?></span><em class="hunt-news-popular__trend hunt-news-popular__trend--<?php echo esc_attr( $row['trend'] ); ?>" aria-hidden="true"><?php echo esc_html( $trend_arrow ); ?></em></a></li>
				<?php endforeach; ?>
			</ol>
		<?php else : ?>
			<p class="hunt-news-popular__empty">실제 읽기 데이터를 집계하고 있습니다.</p>
		<?php endif; ?>
		<p class="hunt-news-popular__updated">GA4 조회와 30초 이상·25% 이상 읽은 신호 반영<?php echo ! empty( $stats['updated_at'] ) ? ' · ' . esc_html( wp_date( 'm월 d일 H:i', strtotime( $stats['updated_at'] ) ) ) . ' 갱신' : ''; ?></p>
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
}
add_action( 'rest_api_init', 'hunt_news_register_popular_read_route' );

/**
 * Explain the editorial promise and offer category-first discovery on home.
 */
function hunt_news_home_sections() {
	if ( is_admin() || ! ( is_home() || is_front_page() || is_category() ) ) {
		return;
	}

	$is_category = is_category();

	$categories = array(
		'life'                  => array( '생활', '교통·주거·건강·교육·소비' ),
		'economy'               => array( '경제', '금리·물가·세금·보험료' ),
		'real-estate'           => array( '부동산', '전월세·청약·대출·세금' ),
		'society'               => array( '사회', '노동·복지·안전·제도' ),
		'politics'              => array( '정치', '법안·정책·찬반 쟁점' ),
		'culture-entertainment' => array( '문화·엔터', '콘텐츠·공연·플랫폼·계약' ),
		'it'                    => array( 'IT', 'AI·앱·플랫폼·작동 원리' ),
	);
	?>
	<aside id="hunt-news-home-notices" class="hunt-news-home-notices" aria-label="Hunt News 이용 안내">
		<a class="hunt-news-home-notices__primary" href="<?php echo esc_url( home_url( '/about/' ) ); ?>"><strong>오늘의 변화</strong><span>대상·금액·시점·내가 할 일부터 빠르게 확인하세요</span><b aria-hidden="true">→</b></a>
		<a class="hunt-news-home-notices__secondary" href="<?php echo esc_url( home_url( '/editorial-policy/' ) ); ?>"><span>공식 원문과 실제 적용 단계를 나눠 설명합니다</span><b aria-hidden="true">→</b></a>
	</aside>
	<?php
	if ( ! $is_category ) {
		hunt_news_render_popular_news();
	}
	?>
	<?php if ( ! $is_category ) : ?>
	<section id="hunt-news-reading-guide" class="hunt-news-reading-guide" aria-labelledby="hunt-news-reading-guide-title">
		<h2 id="hunt-news-reading-guide-title">뉴스를 읽고도 남는 세 가지</h2>
		<div class="hunt-news-reading-guide__steps">
			<article><span>1</span><h3>무엇이 바뀌었나</h3><p>발표 제목이 아니라 실제 변경점과 현재 단계를 확인합니다.</p></article>
			<article><span>2</span><h3>나에게 무엇이 달라지나</h3><p>대상, 금액, 시점과 예외를 내 생활 조건에 맞춰 설명합니다.</p></article>
			<article><span>3</span><h3>지금 무엇을 하면 되나</h3><p>확인할 문서, 신청·선택 시점과 아직 기다려야 할 부분을 나눕니다.</p></article>
		</div>
		<h2 class="hunt-news-reading-guide__categories-title">분야별로 보기</h2>
		<nav class="hunt-news-category-grid" aria-label="Hunt News 분야별 글">
			<?php foreach ( $categories as $slug => $data ) :
				$category = get_category_by_slug( $slug );
				if ( ! $category ) {
					continue;
				}
				$url = get_category_link( $category->term_id );
				if ( is_wp_error( $url ) ) {
					continue;
				}
				?>
				<a href="<?php echo esc_url( $url ); ?>"><strong><?php echo esc_html( $data[0] ); ?></strong><span><?php echo esc_html( $data[1] ); ?></span><em><?php echo esc_html( (string) $category->count ); ?>개</em></a>
			<?php endforeach; ?>
		</nav>
	</section>
	<?php endif; ?>
	<script id="hunt-news-home-sections-position">
	document.addEventListener('DOMContentLoaded',function(){var notices=document.getElementById('hunt-news-home-notices');var popular=document.getElementById('hunt-news-popular');var section=document.getElementById('hunt-news-reading-guide');var main=document.querySelector('#main,main.site-main');if(main&&main.parentNode){var heading=document.createElement('div');heading.className='hunt-news-latest-heading';heading.innerHTML='<p>Hunt News</p><h2>최신 뉴스</h2>';if(notices){main.parentNode.insertBefore(notices,main);}if(popular){main.parentNode.insertBefore(popular,main);}main.parentNode.insertBefore(heading,main);if(section){main.insertAdjacentElement('afterend',section);}}});
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
			var link=event.target.closest('main a[href],.huntlab-related-articles a[href],.entry-related a[href]');
			if(!link){return;}
			var destination;
			try{destination=new URL(link.href,window.location.href);}catch(error){return;}
			if(destination.origin!==window.location.origin||destination.pathname===window.location.pathname){return;}
			send('huntlab_internal_click',{
				link_path:destination.pathname,
				link_area:link.closest('.huntlab-related-articles,.entry-related')?'related':'content',
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
		.huntlab-category-tabs{background:#fff!important;border-color:#dfe2e5!important;box-shadow:none!important}
		.huntlab-category-tabs__link{background:#fff!important;border-color:#d9dde1!important;border-radius:2px!important;color:#30343a!important}
		.huntlab-category-tabs__link:hover,.huntlab-category-tabs__link:focus-visible{background:#f3f5f6!important;border-color:#111820!important;color:#111820!important}
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
		'description' => '복잡한 변화가 내 생활에 어떤 영향을 주는지 쉽게 설명합니다.',
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
