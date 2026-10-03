<?php
/**
 * Plugin Name: HuntLab English
 * Description: English edition at /en/ (post type hunt_en). Each English post stores its Korean
 * counterpart in meta ko_post_id; both pages emit hreflang alternates. Written for English readers
 * from the same measured experiment data, never machine-translated.
 */

add_action(
    'init',
    static function (): void {
        register_post_type( 'hunt_en', [
            'label'        => 'English',
            'public'       => true,
            'has_archive'  => 'en',
            'rewrite'      => [ 'slug' => 'en', 'with_front' => false ],
            'show_in_rest' => true,
            'rest_base'    => 'hunt_en',
            'supports'     => [ 'title', 'editor', 'excerpt', 'thumbnail', 'custom-fields', 'author' ],
        ] );
        register_post_meta( 'hunt_en', 'ko_post_id', [ 'type' => 'integer', 'single' => true, 'show_in_rest' => true ] );
        if ( 'v1' !== get_option( 'huntlab_en_rewrite_version' ) ) {
            flush_rewrite_rules( false );
            update_option( 'huntlab_en_rewrite_version', 'v1' );
        }
    }
);

function huntlab_en_counterpart(): array {
    if ( is_singular( 'hunt_en' ) ) {
        $ko = (int) get_post_meta( get_the_ID(), 'ko_post_id', true );
        return $ko ? [ 'ko' => get_permalink( $ko ), 'en' => get_permalink() ] : [];
    }
    if ( is_singular( 'post' ) ) {
        $en = get_posts( [ 'post_type' => 'hunt_en', 'post_status' => 'publish', 'numberposts' => 1,
            'meta_key' => 'ko_post_id', 'meta_value' => get_the_ID(), 'fields' => 'ids' ] );
        return $en ? [ 'ko' => get_permalink(), 'en' => get_permalink( $en[0] ) ] : [];
    }
    return [];
}

add_action(
    'wp_head',
    static function (): void {
        foreach ( huntlab_en_counterpart() as $lang => $url ) {
            printf( '<link rel="alternate" hreflang="%s" href="%s">' . "\n", esc_attr( $lang ), esc_url( $url ) );
        }
    },
    2
);

add_filter(
    'language_attributes',
    static function ( string $output ): string {
        return ( is_singular( 'hunt_en' ) || is_post_type_archive( 'hunt_en' ) )
            ? preg_replace( '/lang="[^"]*"/', 'lang="en-US"', $output ) : $output;
    }
);

add_filter(
    'the_content',
    static function ( string $content ): string {
        $pair = huntlab_en_counterpart();
        if ( ! $pair || ! in_the_loop() || ! is_main_query() ) {
            return $content;
        }
        $note = is_singular( 'hunt_en' )
            ? '<p class="huntlab-lang-switch"><a href="' . esc_url( $pair['ko'] ) . '" hreflang="ko">한국어로 읽기</a></p>'
            : '<p class="huntlab-lang-switch"><a href="' . esc_url( $pair['en'] ) . '" hreflang="en">Read in English</a></p>';
        return $note . $content;
    },
    5
);

// English byline for the pen name (Korean pages show 훈트 via huntlab-reader-loop, priority 30).
$huntlab_en_byline = static function ( $name ) {
    return ( ! is_admin() && is_singular( 'hunt_en' ) ) ? 'Hunt' : $name;
};
add_filter( 'the_author', $huntlab_en_byline, 40 );
add_filter( 'get_the_author_display_name', $huntlab_en_byline, 40 );
