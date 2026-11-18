<?php
/**
 * Plugin Name: HuntLab No Texturize
 * Description: Turn off wptexturize so CLI options written in prose (colcon --executor, --ros-args) are not rendered as en dashes that break copy-paste.
 */

add_filter( 'run_wptexturize', '__return_false' );
