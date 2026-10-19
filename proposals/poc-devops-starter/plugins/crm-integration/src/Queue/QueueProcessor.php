<?php

declare(strict_types=1);

namespace Upwork\CRMIntegration\Queue;

class QueueProcessor
{
    private const BATCH_SIZE = 25;

    /**
     * Enqueue a sync operation
     */
    public static function enqueue(string $entityType, int $entityId, string $action, array $payload = []): void
    {
        global $wpdb;

        // Check if already queued
        $existing = $wpdb->get_var($wpdb->prepare(
            "SELECT id FROM {$wpdb->prefix}crm_sync_queue 
             WHERE entity_type = %s AND entity_id = %d AND action = %s AND status = 'pending'",
            $entityType,
            $entityId,
            $action
        ));

        if ($existing) {
            // Update payload
            $wpdb->update(
                $wpdb->prefix . 'crm_sync_queue',
                ['payload' => wp_json_encode($payload), 'updated_at' => current_time('mysql')],
                ['id' => $existing]
            );
            return;
        }

        $wpdb->insert(
            $wpdb->prefix . 'crm_sync_queue',
            [
                'entity_type' => $entityType,
                'entity_id' => $entityId,
                'action' => $action,
                'payload' => wp_json_encode($payload),
                'status' => 'pending',
                'created_at' => current_time('mysql'),
            ]
        );
    }

    /**
     * Process a batch of queued items
     */
    public function processBatch(): void
    {
        global $wpdb;

        $items = $wpdb->get_results(
            $wpdb->prepare(
                "SELECT * FROM {$wpdb->prefix}crm_sync_queue 
                 WHERE status = 'pending' AND attempts < max_attempts
                 ORDER BY created_at ASC 
                 LIMIT %d",
                self::BATCH_SIZE
            )
        );

        if (empty($items)) {
            update_option('crm_sync_status', 'idle');
            return;
        }

        update_option('crm_sync_status', 'running');

        foreach ($items as $item) {
            try {
                $this->processItem($item);
                $wpdb->update(
                    $wpdb->prefix . 'crm_sync_queue',
                    ['status' => 'completed', 'updated_at' => current_time('mysql')],
                    ['id' => $item->id]
                );

                // Update daily counter
                $count = intval(get_option('crm_daily_processed', 0));
                update_option('crm_daily_processed', $count + 1);
            } catch (\Throwable $e) {
                $attempts = $item->attempts + 1;
                $status = $attempts >= $item->max_attempts ? 'failed' : 'pending';

                $wpdb->update(
                    $wpdb->prefix . 'crm_sync_queue',
                    [
                        'status' => $status,
                        'attempts' => $attempts,
                        'updated_at' => current_time('mysql'),
                    ],
                    ['id' => $item->id]
                );
            }
        }

        update_option('crm_last_sync_time', current_time('mysql'));
    }

    /**
     * Process a single queue item
     */
    private function processItem(object $item): void
    {
        $payload = json_decode($item->payload, true) ?? [];

        // Dispatch to appropriate handler based on entity type
        match ($item->entity_type) {
            'contact' => $this->processContactSync($item->entity_id, $item->action, $payload),
            'order' => $this->processOrderSync($item->entity_id, $item->action, $payload),
            default => throw new \RuntimeException("Unknown entity type: {$item->entity_type}"),
        };
    }

    private function processContactSync(int $entityId, string $action, array $payload): void
    {
        // In production, this would call CRMClient::upsertContact()
        // For PoC, we simulate success
        if (empty($payload['email'])) {
            throw new \RuntimeException('Contact email is required');
        }
    }

    private function processOrderSync(int $entityId, string $action, array $payload): void
    {
        // In production, this would call CRMClient::upsertDeal()
        if (empty($payload['order_id'])) {
            throw new \RuntimeException('Order ID is required');
        }
    }

    /**
     * Get count of pending queue items
     */
    public function getQueueCount(): int
    {
        global $wpdb;
        return (int) $wpdb->get_var(
            "SELECT COUNT(*) FROM {$wpdb->prefix}crm_sync_queue WHERE status = 'pending'"
        );
    }
}
