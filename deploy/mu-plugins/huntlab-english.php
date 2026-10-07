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
        // Home and /en/ pair up too, so crawlers reach the English edition from the indexed home page.
        $pair = ( is_front_page() || is_post_type_archive( 'hunt_en' ) )
            ? [ 'ko' => home_url( '/' ), 'en' => get_post_type_archive_link( 'hunt_en' ) ] : huntlab_en_counterpart();
        foreach ( $pair as $lang => $url ) {
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

// "Keep reading": up to three other English lessons, same symptom group (huntlab-hub) first, then newest.
add_filter(
    'the_content',
    static function ( string $content ): string {
        if ( ! is_singular( 'hunt_en' ) || ! in_the_loop() || ! is_main_query() ) {
            return $content;
        }
        $current = get_post();
        $others  = get_posts( [ 'post_type' => 'hunt_en', 'post_status' => 'publish', 'numberposts' => 50,
            'exclude' => [ $current->ID ] ] );
        $pattern = null;
        foreach ( function_exists( 'huntlab_hub_groups' ) ? huntlab_hub_groups() : [] as $group ) {
            if ( preg_match( $group[2], $current->post_name ) ) {
                $pattern = $group[2];
                break;
            }
        }
        // usort is stable since PHP 8: same-group posts first, newest order kept within each side.
        usort( $others, static fn( $a, $b ) => (int) ( $pattern && preg_match( $pattern, $b->post_name ) )
            - (int) ( $pattern && preg_match( $pattern, $a->post_name ) ) );
        $items = '';
        foreach ( array_slice( $others, 0, 3 ) as $post ) {
            $items .= '<li><a href="' . esc_url( get_permalink( $post ) ) . '">' . esc_html( get_the_title( $post ) ) . '</a></li>';
        }
        return $items ? $content . '<aside class="huntlab-related" aria-label="Keep reading"><h2>Keep reading</h2><ul>'
            . $items . '</ul></aside>' : $content;
    },
    15
);

// English byline for the pen name (Korean pages show 훈트 via huntlab-reader-loop, priority 30).
$huntlab_en_byline = static function ( $name ) {
    return ( ! is_admin() && is_singular( 'hunt_en' ) ) ? 'Hunt' : $name;
};
add_filter( 'the_author', $huntlab_en_byline, 40 );
add_filter( 'get_the_author_display_name', $huntlab_en_byline, 40 );

// Visible site-wide crawl path to the English edition (home is indexed; /en/ was unknown to Google).
add_action(
    'wp_footer',
    static function (): void {
        $english = is_singular( 'hunt_en' ) || is_post_type_archive( 'hunt_en' );
        printf( '<p class="huntlab-lang-switch" style="text-align:center"><a href="%s" hreflang="%s">%s</a></p>' . "\n",
            esc_url( $english ? home_url( '/' ) : get_post_type_archive_link( 'hunt_en' ) ),
            $english ? 'ko' : 'en', $english ? '한국어' : 'English edition' );
    }
);
