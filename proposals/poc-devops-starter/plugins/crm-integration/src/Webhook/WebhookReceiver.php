<?php

declare(strict_types=1);

namespace Upwork\CRMIntegration\Webhook;

use Upwork\CRMIntegration\Api\CRMClient;
use WP_REST_Request;
use WP_REST_Response;

class WebhookReceiver
{
    private CRMClient $crmClient;

    public function __construct(CRMClient $crmClient)
    {
        $this->crmClient = $crmClient;
    }

    /**
     * Handle incoming webhook from CRM provider
     */
    public function handle(WP_REST_Request $request): WP_REST_Response
    {
        $provider = $request->get_param('provider');
        $eventType = $request->get_header('X-Event-Type') ?? 'unknown';
        $payload = $request->get_json_params();

        // Log the webhook
        $this->logWebhook($provider, $eventType, $payload);

        // Process based on event type
        $result = match ($eventType) {
            'contact.created', 'contact.updated' => $this->handleContactEvent($payload),
            'deal.created', 'deal.updated' => $this->handleDealEvent($payload),
            'lead.created' => $this->handleLeadEvent($payload),
            default => ['status' => 'ignored', 'message' => "Unhandled event type: {$eventType}"],
        };

        return new WP_REST_Response([
            'success' => true,
            'provider' => $provider,
            'event' => $eventType,
            'result' => $result,
        ], 200);
    }

    /**
     * Verify webhook signature
     */
    public function verifySignature(WP_REST_Request $request): bool
    {
        $provider = $request->get_param('provider');
        $signature = $request->get_header('X-Signature') ?? $request->get_header('X-Hub-Signature-256') ?? '';

        if (empty($signature)) {
            return false;
        }

        $secret = defined('CRM_WEBHOOK_SECRET') ? CRM_WEBHOOK_SECRET : '';
        $payload = $request->get_body();

        return match ($provider) {
            'salesforce' => $this->verifySalesforceSignature($signature, $payload, $secret),
            'hubspot' => $this->verifyHubspotSignature($signature, $payload, $secret),
            'zoho' => $this->verifyZohoSignature($signature, $payload, $secret),
            default => true, // Custom providers can implement their own
        };
    }

    private function verifySalesforceSignature(string $signature, string $payload, string $secret): bool
    {
        $expected = 'sha256=' . hash_hmac('sha256', $payload, $secret);
        return hash_equals($expected, $signature);
    }

    private function verifyHubspotSignature(string $signature, string $payload, string $secret): bool
    {
        $expected = 'sha256=' . hash_hmac('sha256', $payload, $secret);
        return hash_equals($expected, $signature);
    }

    private function verifyZohoSignature(string $signature, string $payload, string $secret): bool
    {
        return hash_equals(hash_hmac('sha256', $payload, $secret), $signature);
    }

    private function handleContactEvent(array $payload): array
    {
        // Map CRM contact to WordPress user
        $email = $payload['email'] ?? $payload['Email'] ?? '';
        if (empty($email)) {
            return ['status' => 'error', 'message' => 'No email provided'];
        }

        $user = get_user_by('email', $email);
        if (!$user) {
            // Create new user
            $userId = wp_create_user(
                sanitize_user($email),
                wp_generate_password(),
                $email
            );
            if (is_wp_error($userId)) {
                return ['status' => 'error', 'message' => $userId->get_error_message()];
            }
            update_user_meta($userId, 'crm_contact_id', $payload['id'] ?? '');
            return ['status' => 'created', 'user_id' => $userId];
        }

        // Update existing user
        update_user_meta($user->ID, 'crm_contact_id', $payload['id'] ?? '');
        return ['status' => 'updated', 'user_id' => $user->ID];
    }

    private function handleDealEvent(array $payload): array
    {
        // Create/update a deal as a custom post type entry
        $dealId = $payload['id'] ?? '';
        $dealTitle = $payload['name'] ?? $payload['Deal_Name'] ?? 'Unnamed Deal';

        $existing = get_posts([
            'post_type' => 'crm_deal',
            'meta_key' => 'crm_deal_id',
            'meta_value' => $dealId,
            'posts_per_page' => 1,
        ]);

        if (!empty($existing)) {
            $postId = wp_update_post([
                'ID' => $existing[0]->ID,
                'post_title' => $dealTitle,
                'post_status' => 'publish',
            ]);
            return ['status' => 'updated', 'post_id' => $postId];
        }

        $postId = wp_insert_post([
            'post_title' => $dealTitle,
            'post_type' => 'crm_deal',
            'post_status' => 'publish',
            'meta_input' => ['crm_deal_id' => $dealId],
        ]);

        return ['status' => 'created', 'post_id' => $postId];
    }

    private function handleLeadEvent(array $payload): array
    {
        // Create lead as a contact form entry
        $email = $payload['email'] ?? $payload['Email'] ?? '';
        if (empty($email)) {
            return ['status' => 'error', 'message' => 'No email provided'];
        }

        $postId = wp_insert_post([
            'post_title' => sprintf('Lead: %s', $email),
            'post_type' => 'crm_lead',
            'post_status' => 'publish',
            'meta_input' => [
                'crm_lead_id' => $payload['id'] ?? '',
                'lead_email' => $email,
                'lead_name' => $payload['name'] ?? $payload['First_Name'] ?? '',
                'lead_source' => $payload['source'] ?? 'webhook',
            ],
        ]);

        return ['status' => 'created', 'post_id' => $postId];
    }

    private function logWebhook(string $provider, string $eventType, array $payload): void
    {
        global $wpdb;
        $wpdb->insert(
            $wpdb->prefix . 'crm_webhook_log',
            [
                'provider' => $provider,
                'event_type' => $eventType,
                'payload' => wp_json_encode($payload),
            ]
        );

        // Update 24h counter
        $count = intval(get_option('crm_webhooks_24h', 0));
        update_option('crm_webhooks_24h', $count + 1);
    }
}
