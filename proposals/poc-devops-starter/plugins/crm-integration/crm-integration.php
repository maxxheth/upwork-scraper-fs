<?php
/**
 * Plugin Name: CRM Integration
 * Description: Enterprise CRM integration with webhook receiver, API client, and data sync
 * Version: 1.0.0
 * Requires PHP: 8.1
 * Author: UpWork PoC
 * Text Domain: crm-integration
 */

defined('ABSPATH') || exit;

// Autoload via Composer
if (file_exists(__DIR__ . '/vendor/autoload.php')) {
    require_once __DIR__ . '/vendor/autoload.php';
}

use Upwork\CRMIntegration\Plugin;

// Initialize plugin
add_action('plugins_loaded', function () {
    $plugin = new Plugin();
    $plugin->init();
});

// Activation hook
register_activation_hook(__FILE__, function () {
    // Create database tables for sync queue
    global $wpdb;
    $charset_collate = $wpdb->get_charset_collate();

    $sql = "CREATE TABLE IF NOT EXISTS {$wpdb->prefix}crm_sync_queue (
        id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        entity_type VARCHAR(50) NOT NULL,
        entity_id BIGINT UNSIGNED NOT NULL,
        action VARCHAR(20) NOT NULL,
        payload LONGTEXT,
        status VARCHAR(20) DEFAULT 'pending',
        attempts INT DEFAULT 0,
        max_attempts INT DEFAULT 3,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_status (status),
        INDEX idx_entity (entity_type, entity_id)
    ) $charset_collate;";

    $sql2 = "CREATE TABLE IF NOT EXISTS {$wpdb->prefix}crm_webhook_log (
        id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        provider VARCHAR(50) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        payload LONGTEXT,
        response_code INT,
        response_body LONGTEXT,
        processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_provider (provider),
        INDEX idx_event (event_type)
    ) $charset_collate;";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta($sql);
    dbDelta($sql2);
});
