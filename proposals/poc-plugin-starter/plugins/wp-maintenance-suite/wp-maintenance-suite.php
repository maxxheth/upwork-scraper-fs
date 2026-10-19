<?php
/**
 * Plugin Name: WP Maintenance Suite
 * Description: Security audit dashboard, performance reports, WooCommerce test data seeder, and update testing.
 * Version: 1.0.0
 * Requires PHP: 8.2
 * Author: Maxx / Nous Research
 * Text Domain: wp-maintenance-suite
 */

declare(strict_types=1);

namespace Nous\WpMaintenanceSuite;

if (!defined('ABSPATH')) {
    exit;
}

$autoload = __DIR__ . '/vendor/autoload.php';
if (file_exists($autoload)) {
    require_once $autoload;
}

function init(): void {
    static $initialized = false;
    if ($initialized) {
        return;
    }
    $initialized = true;

    $plugin = new Plugin();
    $plugin->boot();
}

add_action('plugins_loaded', __NAMESPACE__ . '\\init');
