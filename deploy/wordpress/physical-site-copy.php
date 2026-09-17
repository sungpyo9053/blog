<?php
/** Run once with wp eval-file after backing up the active UI plugins. */
$release = '/home/admin/huntlab-ui-release-VZUiMJ';
$backup = '/var/backups/huntlab-ui-20260917';
if ( ! is_dir( $backup ) || file_exists( $backup . '/site-copy-before.json' ) ) {
    throw new RuntimeException( 'Missing backup directory or migration already attempted' );
}
$pages = array( 97 => array( 'about', 'site-about.html' ), 100 => array( 'editorial-policy', 'site-editorial-policy.html' ) );
$before = array( 'blogdescription' => get_option( 'blogdescription' ), 'pages' => array() );
$content = array();
foreach ( $pages as $id => $spec ) {
    $post = get_post( $id );
    if ( ! $post || $post->post_name !== $spec[0] || $post->post_status !== 'publish' ) {
        throw new RuntimeException( 'Page identity mismatch' );
    }
    $content[$id] = file_get_contents( $release . '/' . $spec[1] );
    if ( ! $content[$id] || strpos( $content[$id], '피지컬 AI' ) === false ) {
        throw new RuntimeException( 'Missing reviewed site copy' );
    }
    $before['pages'][$id] = $post;
}
file_put_contents( $backup . '/site-copy-before.json', wp_json_encode( $before, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT ), LOCK_EX );
chmod( $backup . '/site-copy-before.json', 0600 );
foreach ( $content as $id => $html ) {
    $result = wp_update_post( wp_slash( array( 'ID' => $id, 'post_content' => $html ) ), true );
    if ( is_wp_error( $result ) || get_post_field( 'post_content', $id, 'raw' ) !== $html ) {
        throw new RuntimeException( 'Page save verification failed; inspect before retry' );
    }
}
update_option( 'blogdescription', '피지컬 AI의 용어와 원리부터 프레임워크와 실습까지, 확인한 근거로 설명합니다.' );
echo "Site copy saved and read back; IDs 97,100. Posts unchanged.\n";
