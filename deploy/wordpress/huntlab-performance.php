<?php
/**
 * Plugin Name: HuntLab Performance Defaults
 * Description: Keep only the first content image eager and lazy-load later images.
 */

if (!defined('ABSPATH')) {
    exit;
}

add_filter('wp_omit_loading_attr_threshold', static function (): int {
    return 1;
});
