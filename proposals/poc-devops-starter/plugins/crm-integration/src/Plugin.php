<?php

declare(strict_types=1);

namespace Upwork\CRMIntegration;

use Upwork\CRMIntegration\Webhook\WebhookReceiver;
use Upwork\CRMIntegration\Api\CRMClient;
use Upwork\CRMIntegration\DataSync\SyncManager;
use Upwork\CRMIntegration\Queue\QueueProcessor;

class Plugin
{
    private WebhookReceiver $webhookReceiver;
    private CRMClient $crmClient;
    private SyncManager $syncManager;
    private QueueProcessor $queueProcessor;

    public function init(): void
    {
        $this->registerDependencies();
        $this->registerHooks();
        $this->registerRestRoutes();
        $this->registerAdminPage();
    }

    private function registerDependencies(): void
    {
        $this->crmClient = new CRMClient(
            defined('CRM_API_URL') ? CRM_API_URL : 'https://api.example.com',
            defined('CRM_API_KEY') ? CRM_API_KEY : ''
        );

        $this->webhookReceiver = new WebhookReceiver($this->crmClient);
        $this->syncManager = new SyncManager($this->crmClient);
        $this->queueProcessor = new QueueProcessor($this->crmClient);
    }

    private function registerHooks(): void
    {
        // Sync WordPress users to CRM on create/update
        add_action('user_register', [$this->syncManager, 'syncUser'], 10, 1);
        add_action('profile_update', [$this->syncManager, 'syncUser'], 10, 1);

        // Sync WooCommerce orders (if available)
        add_action('woocommerce_new_order', [$this->syncManager, 'syncOrder'], 10, 1);
        add_action('woocommerce_update_order', [$this->syncManager, 'syncOrder'], 10, 1);

        // Process sync queue via WP Cron
        add_action('crm_process_sync_queue', [$this->queueProcessor, 'processBatch']);
        if (!wp_next_scheduled('crm_process_sync_queue')) {
            wp_schedule_event(time(), 'every_minute', 'crm_process_sync_queue');
        }

        // Custom cron schedule
        add_filter('cron_schedules', function ($schedules) {
            $schedules['every_minute'] = [
                'interval' => 60,
                'display' => __('Every Minute', 'crm-integration'),
            ];
            return $schedules;
        });
    }

    private function registerRestRoutes(): void
    {
        add_action('rest_api_init', function () {
            // Webhook receiver endpoint
            register_rest_route('crm/v1', '/webhook/(?P<provider>[a-z]+)', [
                'methods' => 'POST',
                'callback' => [$this->webhookReceiver, 'handle'],
                'permission_callback' => [$this->webhookReceiver, 'verifySignature'],
                'args' => [
                    'provider' => [
                        'required' => true,
                        'validate_callback' => fn($p) => in_array($p, ['salesforce', 'hubspot', 'zoho', 'custom']),
                    ],
                ],
            ]);

            // Sync status endpoint
            register_rest_route('crm/v1', '/sync/status', [
                'methods' => 'GET',
                'callback' => [$this->syncManager, 'getStatus'],
                'permission_callback' => fn() => current_user_can('manage_options'),
            ]);

            // Manual sync trigger
            register_rest_route('crm/v1', '/sync/trigger', [
                'methods' => 'POST',
                'callback' => [$this->syncManager, 'triggerSync'],
                'permission_callback' => fn() => current_user_can('manage_options'),
            ]);
        });
    }

    private function registerAdminPage(): void
    {
        add_action('admin_menu', function () {
            add_menu_page(
                'CRM Integration',
                'CRM Integration',
                'manage_options',
                'crm-integration',
                [$this, 'renderAdminPage'],
                'dashicons-rest-api',
                30
            );
        });
    }

    public function renderAdminPage(): void
    {
        $queueCount = $this->queueProcessor->getQueueCount();
        $lastSync = get_option('crm_last_sync_time', 'Never');
        $syncStatus = get_option('crm_sync_status', 'idle');
        ?>
        <div class="wrap">
            <h1>CRM Integration Dashboard</h1>
            <div class="crm-status-cards" style="display:flex;gap:20px;margin:20px 0;">
                <div style="flex:1;background:#fff;padding:20px;border:1px solid #ddd;border-radius:8px;">
                    <h3>Sync Status</h3>
                    <p>Status: <strong><?php echo esc_html($syncStatus); ?></strong></p>
                    <p>Last Sync: <strong><?php echo esc_html($lastSync); ?></strong></p>
                </div>
                <div style="flex:1;background:#fff;padding:20px;border:1px solid #ddd;border-radius:8px;">
                    <h3>Queue</h3>
                    <p>Pending Items: <strong><?php echo intval($queueCount); ?></strong></p>
                    <p>Processed Today: <strong><?php echo intval(get_option('crm_daily_processed', 0)); ?></strong></p>
                </div>
                <div style="flex:1;background:#fff;padding:20px;border:1px solid #ddd;border-radius:8px;">
                    <h3>Webhooks</h3>
                    <p>Received (24h): <strong><?php echo intval(get_option('crm_webhooks_24h', 0)); ?></strong></p>
                    <p>Endpoint: <code>/wp-json/crm/v1/webhook/{provider}</code></p>
                </div>
            </div>
            <form method="post" action="<?php echo admin_url('admin-post.php'); ?>">
                <input type="hidden" name="action" value="crm_manual_sync">
                <?php wp_nonce_field('crm_manual_sync'); ?>
                <button type="submit" class="button button-primary">Trigger Manual Sync</button>
            </form>
        </div>
        <?php
    }
}
