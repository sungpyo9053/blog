<?php
/**
 * Plugin Name: HuntLab AI Reads
 * Description: Counts page renders requested by AI assistants. "user" agents fetch a page because a person
 * asked the assistant right now; "crawl" agents index pages for AI search. GA4 sees neither (no JS).
 * GET /huntlab/v1/ai-reads?day=YYYY-MM-DD (editors only) returns that KST day's counts.
 */

function huntlab_ai_reads_kind( string $agent ): ?string {
    if ( preg_match( '/ChatGPT-User|Claude-User|Perplexity-User|MistralAI-User/i', $agent ) ) {
        return 'user';
    }
    if ( preg_match( '/OAI-SearchBot|Claude-SearchBot|PerplexityBot|GPTBot|ClaudeBot/i', $agent ) ) {
        return 'crawl';
    }
    return null;
}

add_action(
    'template_redirect',
    static function (): void {
        $kind = huntlab_ai_reads_kind( (string) ( $_SERVER['HTTP_USER_AGENT'] ?? '' ) );
        if ( ! $kind ) {
            return;
        }
        $day    = wp_date( 'Y-m-d', null, new DateTimeZone( 'Asia/Seoul' ) );
        $counts = get_option( 'huntlab_ai_reads', [] );
        // ponytail: read-modify-write can lose a count under concurrent bot hits; fine for a daily trend line.
        $counts[ $day ][ $kind ] = ( $counts[ $day ][ $kind ] ?? 0 ) + 1;
        update_option( 'huntlab_ai_reads', array_slice( $counts, -14, null, true ), false );
    }
);

add_action(
    'rest_api_init',
    static function (): void {
        register_rest_route( 'huntlab/v1', '/ai-reads', [
            'methods'             => 'GET',
            'permission_callback' => static fn() => current_user_can( 'edit_posts' ),
            'callback'            => static function ( WP_REST_Request $request ): array {
                $counts = get_option( 'huntlab_ai_reads', [] )[ (string) $request->get_param( 'day' ) ] ?? [];
                return [ 'user' => (int) ( $counts['user'] ?? 0 ), 'crawl' => (int) ( $counts['crawl'] ?? 0 ) ];
            },
        ] );
    }
);
