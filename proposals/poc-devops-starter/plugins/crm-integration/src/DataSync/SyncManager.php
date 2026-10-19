<?php

declare(strict_types=1);

namespace Upwork\CRMIntegration\DataSync;

use Upwork\CRMIntegration\Api\CRMClient;
use Upwork\CRMIntegration\Queue\QueueProcessor;
use WP_REST_Response;

class SyncManager
{
    private CRMClient $crmClient;

    public function __construct(CRMClient $crmClient)
    {
        $this->crmClient = $crmClient;
    }

    /**
     * Sync a WordPress user to the CRM
     */
    public function syncUser(int $userId): void
    {
        $user = get_userdata($userId);
        if (!$user) {
            return;
        }

        $contactData = [
            'email' => $user->user_email,
            'first_name' => $user->first_name,
            'last_name' => $user->last_name,
            'username' => $user->user_login,
            'roles' => $user->roles,
            'registered_at' => $user->user_registered,
            'source' => 'wordpress',
            'source_url' => home_url(),
        ];

        // Queue the sync operation
        QueueProcessor::enqueue('contact', $userId, 'upsert', $contactData);
    }

    /**
     * Sync a WooCommerce order to the CRM
     */
    public function syncOrder(int $orderId): void
    {
        if (!function_exists('wc_get_order')) {
            return;
        }

        $order = wc_get_order($orderId);
        if (!$order) {
            return;
        }

        $orderData = [
            'order_id' => $orderId,
            'order_number' => $order->get_order_number(),
            'status' => $order->get_status(),
            'total' => $order->get_total(),
            'currency' => $order->get_currency(),
            'customer_email' => $order->get_billing_email(),
            'customer_name' => $order->get_billing_first_name() . ' ' . $order->get_billing_last_name(),
            'items' => [],
            'source' => 'woocommerce',
            'source_url' => $order->get_view_order_url(),
        ];

        foreach ($order->get_items() as $item) {
            $orderData['items'][] = [
                'product_id' => $item->get_product_id(),
                'name' => $item->get_name(),
                'quantity' => $item->get_quantity(),
                'total' => $item->get_total(),
            ];
        }

        QueueProcessor::enqueue('order', $orderId, 'upsert', $orderData);
    }

    /**
     * Get sync status
     */
    public function getStatus(): WP_REST_Response
    {
        global $wpdb;

        $queueCount = (int) $wpdb->get_var(
            "SELECT COUNT(*) FROM {$wpdb->prefix}crm_sync_queue WHERE status = 'pending'"
        );

        $failedCount = (int) $wpdb->get_var(
            "SELECT COUNT(*) FROM {$wpdb->prefix}crm_sync_queue WHERE status = 'failed'"
        );

        $processedToday = (int) $wpdb->get_var(
            $wpdb->prepare(
                "SELECT COUNT(*) FROM {$wpdb->prefix}crm_sync_queue WHERE status = 'completed' AND DATE(updated_at) = %s",
                current_time('Y-m-d')
            )
        );

        return new WP_REST_Response([
            'success' => true,
            'data' => [
                'queue_pending' => $queueCount,
                'queue_failed' => $failedCount,
                'processed_today' => $processedToday,
                'last_sync' => get_option('crm_last_sync_time', null),
                'sync_status' => get_option('crm_sync_status', 'idle'),
                'crm_connected' => $this->crmClient->testConnection(),
            ],
        ], 200);
    }

    /**
     * Trigger a manual sync
     */
    public function triggerSync(): WP_REST_Response
    {
        update_option('crm_sync_status', 'running');
        update_option('crm_last_sync_time', current_time('mysql'));

        // Trigger the queue processor
        do_action('crm_process_sync_queue');

        return new WP_REST_Response([
            'success' => true,
            'message' => 'Sync triggered successfully',
        ], 200);
    }
}
