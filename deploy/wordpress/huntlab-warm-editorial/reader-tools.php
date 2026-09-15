<?php
/** Reader-facing diagnostics and a server-rendered library entry point. */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function huntlab_library_template( $template ) {
	if ( ( is_front_page() && ! is_paged() ) || is_category( array( 'rest-api-publishing', 'automation-testing', 'wordpress-operations' ) ) ) {
		remove_action( 'wp_body_open', 'huntlab_warm_editorial_home_intro', 25 );
		remove_action( 'wp_body_open', 'hunt_news_home_sections', 26 );
		// The legacy positioning script hides the theme loop. Our template is
		// the real main content, so it must never receive that script.
		return __DIR__ . '/library-home.php';
	}
	return $template;
}
add_filter( 'template_include', 'huntlab_library_template', 99 );

function huntlab_reader_tools_assets() {
	wp_enqueue_style( 'huntlab-reader-tools', plugins_url( 'assets/reader-tools.css', __FILE__ ), array(), (string) filemtime( __DIR__ . '/assets/reader-tools.css' ) );
	if ( is_page( 'wordpress-response-check' ) ) {
		wp_enqueue_script( 'huntlab-reader-tools', plugins_url( 'assets/reader-tools.js', __FILE__ ), array(), (string) filemtime( __DIR__ . '/assets/reader-tools.js' ), true );
	}
}
add_action( 'wp_enqueue_scripts', 'huntlab_reader_tools_assets', 110 );

function huntlab_reader_footer() {
	?>
	<footer class="huntlab-reader-footer" aria-label="사이트 운영 안내"><strong>HuntLab · WordPress 운영 노트</strong><p>코드로 재현한 문제, 실제 운영에서 확인한 결과와 아직 확인하지 못한 한계를 함께 기록합니다.</p><nav aria-label="운영 정보"><a href="<?php echo esc_url( home_url( '/about/' ) ); ?>">운영자와 작성 방식</a><a href="<?php echo esc_url( home_url( '/editorial-policy/' ) ); ?>">검증·정정 원칙</a><a href="<?php echo esc_url( home_url( '/contact/' ) ); ?>">오류 제보</a><a href="<?php echo esc_url( home_url( '/privacy-policy/' ) ); ?>">개인정보처리방침</a></nav></footer>
	<?php
}
add_action( 'wp_footer', 'huntlab_reader_footer', 30 );

function huntlab_diagnostics_shortcode() {
	ob_start();
	?>
	<div class="huntlab-diagnostics" data-huntlab-diagnostics>
		<nav class="huntlab-tool-jumps" aria-label="진단 항목"><a href="#rest-check-title">응답 검사</a><a href="#retry-check-title">대기 시간</a><a href="#inventory-check-title">목록 누락</a></nav>
		<p class="huntlab-tool-note">입력 내용은 이 브라우저에서만 처리합니다. 전송·저장하지 않습니다. 비밀번호와 인증 헤더를 제외한 응답만 넣으세요. 아래 검사는 실제 발행 여부를 보장하지 않으며 사이트에 요청을 보내지 않습니다.</p>
		<noscript><p>입력 검사는 JavaScript가 필요합니다. 아래 사용법과 <a href="https://github.com/sungpyo9053/blog/blob/main/scripts/huntlab_wp_diagnostics.py">오프라인 Python 도구</a>를 이용할 수도 있습니다.</p></noscript>
		<section aria-labelledby="rest-check-title"><h2 id="rest-check-title">1. 글 생성·수정 응답 검사</h2><p>HTTP 성공 코드와 실제 글 객체를 구분합니다. 목록 조회·미디어 업로드 응답용 검사는 아닙니다.</p>
		<form data-check="rest"><div class="huntlab-tool-fields"><label>HTTP 상태<input name="status" type="number" min="100" max="599" required value="201"></label><label>Content-Type<input name="type" required value="application/json"></label><label>예상 글 ID (수정할 때만)<input name="expected" type="number" min="1"></label></div><label>응답 본문<textarea name="body" rows="6" maxlength="100000" required spellcheck="false" placeholder='{"id": 123, "status": "publish"}'></textarea></label><div class="huntlab-tool-actions"><button type="submit">응답 검사</button><button type="button" data-example="html">실패 예제: HTML 200</button><button type="button" data-example="post">성공 예제: JSON 201</button></div><p class="huntlab-tool-result" role="status" aria-live="polite"></p></form>
		<p><a href="<?php echo esc_url( home_url( '/wordpress-rest-html-200-validation/' ) ); ?>">왜 HTTP 200만 보면 실패를 놓치는가 →</a></p></section>
		<section aria-labelledby="retry-check-title"><h2 id="retry-check-title">2. Retry-After 대기 시간 계산</h2><p>초 단위 값과 HTTP 날짜를 구분합니다. 브라우저 시계 기준이며 서버 시계가 다르면 실제 대기 시간도 달라집니다.</p><form data-check="retry"><label>Retry-After 값<input name="retry" required placeholder="120 또는 Wed, 16 Sep 2026 00:00:00 GMT" maxlength="150"></label><label>현재 시각 (ISO 8601, 시간대 포함)<input name="now" required></label><button type="submit">대기 시간 계산</button><p class="huntlab-tool-result" role="status" aria-live="polite"></p></form><p>글 생성 POST는 타임아웃 뒤 무조건 재전송하지 마세요. 서버에서 이미 저장됐을 수 있으므로 기존 글 ID·slug를 조회한 뒤 결정해야 합니다.</p><p><a href="<?php echo esc_url( home_url( '/wordpress-rest-api-retry/' ) ); ?>">재시도 파서와 중복 생성 경계 읽기 →</a></p></section>
		<section aria-labelledby="inventory-check-title"><h2 id="inventory-check-title">3. 전체 목록 누락 검사</h2><p>같은 조건으로 조회한 X-WP-Total과 모든 페이지에서 모은 글 ID를 비교합니다. 공개 글과 초안은 각각 검사하세요.</p><form data-check="inventory"><div class="huntlab-tool-fields"><label>X-WP-Total<input name="total" type="number" min="0" required></label><label>페이지당 항목 수<input name="perPage" type="number" min="1" max="100" value="100" required></label></div><label>모은 글 ID (쉼표·공백·줄바꿈으로 구분)<textarea name="ids" rows="5" maxlength="100000" placeholder="101, 102, 103"></textarea></label><button type="submit">수집 건수 검사</button><p class="huntlab-tool-result" role="status" aria-live="polite"></p></form><p><a href="<?php echo esc_url( home_url( '/wordpress-rest-api-pagination/' ) ); ?>">첫 100개만 확인하면 누락되는 이유 →</a></p></section>
		<button type="button" data-clear>입력과 결과 모두 지우기</button>
	</div>
	<?php
	return ob_get_clean();
}
add_shortcode( 'huntlab_diagnostics', 'huntlab_diagnostics_shortcode' );
