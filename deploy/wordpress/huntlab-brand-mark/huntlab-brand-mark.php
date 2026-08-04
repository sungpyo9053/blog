<?php
/**
 * Plugin Name: HuntLab Dachshund Brand Mark
 * Description: Adds the HuntLab dachshund mark to the Kadence text wordmark.
 * Version: 1.0.0
 * Author: HuntLab
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Keep the theme's accessible text title and add a decorative, scalable mark.
 */
function huntlab_brand_mark_styles(): void
{
    ?>
    <style id="huntlab-dachshund-brand-mark">
        .site-branding .brand {
            align-items: center;
            display: inline-flex;
            gap: 0.5rem;
        }

        .site-branding .brand::before {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 96 40'%3E%3Cg fill='%231a202c'%3E%3Cpath d='M24 13C34 9 61 9 70 14c4 2 7 1 12-4 1 7-2 11-9 14v6h-7l-1-6H36l-2 7h-7l1-9c-4-2-6-5-6-8l2-1Z'/%3E%3Cpath d='M25 13c-2-7-11-9-17-3l-5 4 6 3c-1 7 5 11 13 8l7-5-4-7Z'/%3E%3Cpath d='M14 8c-6 3-5 12 2 15 3-5 5-11 3-14l-5-1Z' fill='%232b6cb0'/%3E%3Ccircle cx='10' cy='13' r='1.4' fill='%23fff'/%3E%3C/g%3E%3C/svg%3E");
            background-position: center;
            background-repeat: no-repeat;
            background-size: contain;
            content: "";
            display: block;
            flex: 0 0 auto;
            height: 2rem;
            width: 4.8rem;
        }

        @media (max-width: 767px) {
            .site-branding .brand {
                gap: 0.35rem;
            }

            .site-branding .brand::before {
                height: 1.65rem;
                width: 3.95rem;
            }
        }
    </style>
    <?php
}
add_action('wp_head', 'huntlab_brand_mark_styles', 20);
