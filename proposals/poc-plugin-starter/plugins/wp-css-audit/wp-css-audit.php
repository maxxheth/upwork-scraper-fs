<?php
/**
 * Plugin Name: WP CSS Audit
 * Description: Scans theme templates for hard-coded HTML elements and provides a live CSS editor admin page.
 * Version: 1.0.0
 * Requires PHP: 8.2
 * Author: Maxx / Nous Research
 * Text Domain: wp-css-audit
 */

declare(strict_types=1);

namespace Nous\WpCssAudit;

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Autoload via Composer
$autoload = __DIR__ . '/vendor/autoload.php';
if (file_exists($autoload)) {
    require_once $autoload;
}

/**
 * Initialize the plugin.
 */
function init(): void {
    static $initialized = false;
    if ($initialized) {
        return;
    }
    $initialized = true;

    // Bootstrap the plugin
    $plugin = new Plugin();
    $plugin->boot();
}

add_action('plugins_loaded', __NAMESPACE__ . '\\init');
