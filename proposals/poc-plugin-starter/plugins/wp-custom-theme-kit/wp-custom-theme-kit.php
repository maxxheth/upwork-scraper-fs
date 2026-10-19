<?php
/**
 * Plugin Name: WP Custom Theme Kit
 * Description: Custom theme development kit with ACF field groups, CPTs, and form handling.
 * Version: 1.0.0
 * Requires PHP: 8.2
 * Author: Maxx / Nous Research
 * Text Domain: wp-custom-theme-kit
 */

declare(strict_types=1);

namespace Nous\WpCustomThemeKit;

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
