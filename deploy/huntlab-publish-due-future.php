<?php
// Publish every future post whose time has passed. Does not rely on the
// publish_future_post cron events, which concurrent cron-option writes can lose.
$ids = get_posts([
    'post_status' => 'future', 'post_type' => 'any', 'numberposts' => -1, 'fields' => 'ids',
    'date_query' => [['column' => 'post_date_gmt', 'before' => gmdate('Y-m-d H:i:s'), 'inclusive' => true]],
]);
foreach ($ids as $id) {
    check_and_publish_future_post($id);
    WP_CLI::log("published $id");
}
