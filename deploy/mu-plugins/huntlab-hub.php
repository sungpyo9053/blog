<?php
/**
 * Plugin Name: HuntLab Hub
 * Description: [huntlab_hub lang="ko|en"] lists every live Physical AI lesson grouped by the reader's symptom,
 * so new posts join the hub the moment they go public. A footer link on every page gives crawlers a path
 * from the indexed pages to the hub. (/measured-notes/ lists only posts with a measured section.)
 */

const HUNTLAB_HUB_SLUG = [ 'ko' => 'ros2-troubleshooting', 'en' => 'ros-2-troubleshooting-guide' ];

function huntlab_hub_groups(): array {
    // First match wins; slugs are written from the reader's question, so they carry the symptom.
    return [
        [ '설치·빌드', 'Install and build', '/colcon|setup-bash|local-setup|install|apt-|distro/' ],
        [ '토픽·QoS 통신', 'Topics and QoS', '/qos|liveliness|deadline|transient|message-filter|topic|wifi|discovery/' ],
        [ '시간·시뮬레이션', 'Time and simulation', '/sim-time|clock|time|timer|timestep|stamp|drift|simulation/' ],
        [ '좌표계·tf', 'Frames and tf', '/tf|frame|yaw|covariance|optical|coordinate|bearing|float32/' ],
        [ '제어·학습', 'Control and learning', '/control|rl-|policy|velocity|termination|moving-average/' ],
    ];
}

add_shortcode(
    'huntlab_hub',
    static function ( $atts ): string {
        $english = 'en' === ( $atts['lang'] ?? 'ko' );
        $posts   = $english
            ? get_posts( [ 'post_type' => 'hunt_en', 'post_status' => 'publish', 'numberposts' => -1 ] )
            : get_posts( [ 'post_type' => 'post', 'post_status' => 'publish', 'numberposts' => -1,
                'category_name' => 'physical-ai-basics,physical-ai-principles,physical-ai-frameworks,physical-ai-experiments' ] );
        $count  = count( huntlab_hub_groups() );
        $groups = array_fill( 0, $count + 1, [] );
        foreach ( $posts as $post ) {
            $index = $count;
            foreach ( huntlab_hub_groups() as $i => $group ) {
                if ( preg_match( $group[2], $post->post_name ) ) {
                    $index = $i;
                    break;
                }
            }
            $groups[ $index ][] = $post;
        }
        $html = '';
        foreach ( $groups as $i => $items ) {
            if ( ! $items ) {
                continue;
            }
            $label = huntlab_hub_groups()[ $i ] ?? [ '기초 개념', 'Basics' ];
            $html .= '<h2>' . esc_html( $english ? $label[1] : $label[0] ) . '</h2><ul>';
            foreach ( $items as $post ) {
                $html .= '<li><a href="' . esc_url( get_permalink( $post ) ) . '">' . esc_html( get_the_title( $post ) ) . '</a>';
                if ( ! $english ) {
                    // ponytail: one lookup per post; fine for a few hundred lessons, cache if the hub slows down.
                    $pair = get_posts( [ 'post_type' => 'hunt_en', 'post_status' => 'publish', 'numberposts' => 1,
                        'meta_key' => 'ko_post_id', 'meta_value' => $post->ID, 'fields' => 'ids' ] );
                    if ( $pair ) {
                        $html .= ' <a href="' . esc_url( get_permalink( $pair[0] ) ) . '" hreflang="en">(English)</a>';
                    }
                }
                $summary = wp_trim_words( get_the_excerpt( $post ), $english ? 28 : 60, '…' );
                if ( $summary ) {
                    $html .= '<br>' . esc_html( $summary );
                }
                $html .= '</li>';
            }
            $html .= '</ul>';
        }
        return $html;
    }
);

function huntlab_hub_page( string $lang ): ?WP_Post {
    $page = get_page_by_path( HUNTLAB_HUB_SLUG[ $lang ] );
    return ( $page && 'publish' === $page->post_status ) ? $page : null;
}

add_action(
    'wp_head',
    static function (): void {
        $ko = huntlab_hub_page( 'ko' );
        $en = huntlab_hub_page( 'en' );
        if ( $ko && $en && is_page( [ $ko->ID, $en->ID ] ) ) {
            printf( '<link rel="alternate" hreflang="ko" href="%s">' . "\n", esc_url( get_permalink( $ko ) ) );
            printf( '<link rel="alternate" hreflang="en" href="%s">' . "\n", esc_url( get_permalink( $en ) ) );
        }
    },
    2
);

add_filter(
    'language_attributes',
    static function ( string $output ): string {
        $en = huntlab_hub_page( 'en' );
        return ( $en && is_page( $en->ID ) ) ? preg_replace( '/lang="[^"]*"/', 'lang="en-US"', $output ) : $output;
    }
);

add_action(
    'wp_footer',
    static function (): void {
        $en_page = huntlab_hub_page( 'en' );
        $english = is_singular( 'hunt_en' ) || is_post_type_archive( 'hunt_en' ) || ( $en_page && is_page( $en_page->ID ) );
        $hub     = huntlab_hub_page( $english ? 'en' : 'ko' );
        if ( $hub ) {
            // Transparency page (how AI-written, measured articles are made) sits next to the hub link.
            $how = get_page_by_path( $english ? 'how-these-articles-are-made' : 'how-articles-are-made' );
            printf( '<p class="huntlab-hub-link" style="text-align:center"><a href="%s">%s</a>%s</p>' . "\n",
                esc_url( get_permalink( $hub ) ), $english ? 'ROS 2 troubleshooting guide' : 'ROS 2 문제 해결 모음',
                ( $how && 'publish' === $how->post_status ) ? ' · <a href="' . esc_url( get_permalink( $how ) ) . '">'
                    . ( $english ? 'How these articles are made' : '글을 만드는 방식' ) . '</a>' : '' );
        }
    },
    5
);
