<?php
/**
 * Plugin Name: WP Diagnostics
 * Description: Advanced diagnostics for WordPress - monitors PHP memory, execution time, DB queries, and crash patterns
 * Version: 1.0.0
 * Requires PHP: 8.1
 * Author: UpWork PoC
 * Text Domain: wp-diagnostics
 */

defined('ABSPATH') || exit;

// Autoload via Composer
if (file_exists(__DIR__ . '/vendor/autoload.php')) {
    require_once __DIR__ . '/vendor/autoload.php';
}

use Upwork\Diagnostics\Plugin;

// Initialize immediately (mu-plugin compatible)
$diagnostics = new Plugin();
$diagnostics->init();
