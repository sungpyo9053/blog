<?php
/**
 * Plugin Name: HuntLab Warm Editorial Theme
 * Description: Applies HuntLab's warm editorial palette without replacing the active WordPress theme.
 * Version: 1.2.0
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
 * Return category-specific editorial context for the archive hero.
 *
 * @return array<string, array{label:string,title:string,description:string,promises:array<int,string>,image:string,alt:string}>
 */
function huntlab_warm_editorial_category_intros() {
	return array(
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
			'label'       => 'Economy',
			'title'       => '숫자보다,<br>생활에 닿는 의미를.',
			'description' => '공식 통계의 기준과 맥락을 확인하고, 숫자의 변화가 가계와 기업의 선택에 미치는 영향을 설명합니다.',
			'promises'    => array( '공식 통계', '맥락', '생활 영향' ),
			'image'       => 'economy.webp',
			'alt'         => '경제 데이터 토큰이 가계와 기업, 공공 부문을 거쳐 측정 계기로 흐르는 도자기 미니어처',
		),
		'society'             => array(
			'label'       => 'Society',
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
			<p class="huntlab-home-intro__eyebrow"><?php echo $is_category ? esc_html( 'HuntLab · ' . $intro['label'] ) : 'HuntLab · 직접 해보고 기록하는 기술 블로그'; ?></p>
			<h1 id="huntlab-home-intro-title"><?php echo $is_category ? wp_kses( $intro['title'], array( 'br' => array() ) ) : '복잡한 기술을,<br>오래 써먹을 수 있게.'; ?></h1>
			<p class="huntlab-home-intro__description"><?php echo $is_category ? esc_html( $intro['description'] ) : '실행 결과와 실패 기록을 바탕으로 AI, 개발, 클라우드 운영에서 실제로 필요한 판단을 정리합니다.'; ?></p>
			<ul class="huntlab-home-intro__promises" aria-label="<?php echo esc_attr( $is_category ? $intro['label'] . ' 콘텐츠 원칙' : 'HuntLab 콘텐츠 원칙' ); ?>">
				<?php foreach ( $is_category ? $intro['promises'] : array( '직접 실행', '실패도 기록', '운영 판단까지' ) as $promise ) : ?>
					<li><?php echo esc_html( $promise ); ?></li>
				<?php endforeach; ?>
			</ul>
		</div>
		<?php if ( $is_category ) : ?>
			<figure class="huntlab-home-intro__visual">
				<img src="<?php echo esc_url( plugins_url( 'assets/categories/' . $intro['image'], __FILE__ ) ); ?>" width="1000" height="563" alt="<?php echo esc_attr( $intro['alt'] ); ?>" loading="eager" decoding="async" fetchpriority="high">
			</figure>
		<?php else : ?>
			<div class="huntlab-home-intro__dog" aria-hidden="true">
				<span class="huntlab-home-intro__dog-body"></span>
				<span class="huntlab-home-intro__dog-head"></span>
				<span class="huntlab-home-intro__dog-ear"></span>
				<span class="huntlab-home-intro__dog-tail"></span>
			</div>
		<?php endif; ?>
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
