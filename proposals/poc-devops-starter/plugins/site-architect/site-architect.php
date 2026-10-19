<?php
/**
 * Plugin Name: Site Architect
 * Description: Architecture audit tool, headless CMS API, and Gutenberg block builder for B2B SaaS sites
 * Version: 1.0.0
 * Requires PHP: 8.1
 * Author: UpWork PoC
 * Text Domain: site-architect
 */

defined('ABSPATH') || exit;

// Autoload via Composer
if (file_exists(__DIR__ . '/vendor/autoload.php')) {
    require_once __DIR__ . '/vendor/autoload.php';
}

use Upwork\SiteArchitect\Plugin;

add_action('plugins_loaded', function () {
    $plugin = new Plugin();
    $plugin->init();
});
