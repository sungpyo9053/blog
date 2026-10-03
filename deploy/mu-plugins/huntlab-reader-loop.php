<?php
/**
 * Plugin Name: HuntLab Reader Loop
 * Description: "도움이 됐나요?" feedback (GA4 events feedback_up/feedback_down) and the
 * [huntlab_measured_notes] hub listing posts that carry a measured (실측) section.
 */

function huntlab_has_measured( string $content ): bool {
    return false !== strpos( $content, 'measured:start' ) || false !== strpos( $content, 'id="measured-' );
}

add_filter(
    'the_content',
    static function ( string $content ): string {
        if ( ! is_singular( 'post' ) || ! in_the_loop() || ! is_main_query() ) {
            return $content;
        }
        $hub  = huntlab_has_measured( $content ) ? ' <a href="/measured-notes/">실측 노트 전체 보기 →</a>' : '';
        $form = '<aside class="huntlab-feedback" aria-label="글 평가"><p><strong>이 글이 도움이 됐나요?</strong> '
            . '<button type="button" data-v="up">👍 도움됨</button> <button type="button" data-v="down">👎 아쉬움</button>'
            . '<span class="huntlab-feedback-done" hidden> 고맙습니다.</span>' . $hub . '</p></aside>';
        return $content . $form;
    },
    20
);

add_action(
    'wp_footer',
    static function (): void {
        if ( ! is_singular( 'post' ) ) {
            return;
        }
        ?>
<script>
document.querySelectorAll('.huntlab-feedback button').forEach(function (b) {
  b.addEventListener('click', function () {
    if (typeof gtag === 'function') gtag('event', 'feedback_' + b.dataset.v, {page_path: location.pathname});
    var box = b.closest('.huntlab-feedback');
    box.querySelectorAll('button').forEach(function (x) { x.disabled = true; });
    box.querySelector('.huntlab-feedback-done').hidden = false;
  });
});
</script>
        <?php
    }
);

add_shortcode(
    'huntlab_measured_notes',
    static function (): string {
        $items = '';
        foreach ( get_posts( [ 'post_type' => 'post', 'post_status' => 'publish', 'numberposts' => 200 ] ) as $post ) {
            if ( huntlab_has_measured( $post->post_content ) ) {
                $items .= sprintf( '<li><a href="%s">%s</a> <small>%s</small></li>', esc_url( get_permalink( $post ) ),
                    esc_html( get_the_title( $post ) ), esc_html( get_the_date( 'Y-m-d', $post ) ) );
            }
        }
        return $items ? "<ul class=\"huntlab-measured-notes\">$items</ul>" : '<p>아직 실측 노트가 없습니다.</p>';
    }
);

// Pen name byline; overrides huntlab-warm-editorial's fixed "HuntLab 운영자" (priority 20).
$huntlab_pen_name = static function ( $name ) {
    return is_admin() ? $name : '훈트';
};
add_filter( 'the_author', $huntlab_pen_name, 30 );
add_filter( 'get_the_author_display_name', $huntlab_pen_name, 30 );
