<?php

declare(strict_types=1);

namespace Nous\WpCssAudit;

/**
 * Handles the live CSS editor functionality.
 */
final class CssEditor
{
    private const OPTION_KEY = 'wp_css_audit_custom_css';

    public function register(): void
    {
        // AJAX handler for saving CSS
        add_action('wp_ajax_wp_css_audit_save_css', [$this, 'handleSaveCss']);
        add_action('wp_ajax_wp_css_audit_preview_css', [$this, 'handlePreviewCss']);

        // Frontend preview output
        add_action('wp_head', [$this, 'outputPreviewCss'], 999);
    }

    /**
     * Get saved custom CSS.
     */
    public function getCustomCss(): string
    {
        return (string) get_option(self::OPTION_KEY, '');
    }

    /**
     * AJAX handler: Save custom CSS.
     */
    public function handleSaveCss(): void
    {
        if (!current_user_can('manage_options')) {
            wp_die('Unauthorized', 403);
        }

        check_ajax_referer('wp_css_audit_nonce', 'nonce');

        $css = wp_unslash($_POST['css'] ?? '');
        $css = sanitize_textarea_field($css);

        update_option(self::OPTION_KEY, $css);

        wp_send_json_success(['message' => 'CSS saved successfully.']);
    }

    /**
     * AJAX handler: Preview CSS (returns rendered preview).
     */
    public function handlePreviewCss(): void
    {
        if (!current_user_can('manage_options')) {
            wp_die('Unauthorized', 403);
        }

        check_ajax_referer('wp_css_audit_nonce', 'nonce');

        $css = wp_unslash($_POST['css'] ?? '');
        $css = sanitize_textarea_field($css);

        // Store in session for frontend output
        set_transient('wp_css_audit_preview_' . get_current_user_id(), $css, HOUR_IN_SECONDS);

        wp_send_json_success(['message' => 'Preview updated. Refresh the frontend to see changes.']);
    }

    /**
     * Output preview CSS on frontend.
     */
    public function outputPreviewCss(): void
    {
        if (!is_user_logged_in() || !current_user_can('manage_options')) {
            return;
        }

        $previewCss = get_transient('wp_css_audit_preview_' . get_current_user_id());
        if (!empty($previewCss)) {
            echo "\n<!-- WP CSS Audit Preview -->\n<style id=\"wp-css-audit-preview\">\n";
            echo wp_kses_post($previewCss);
            echo "\n</style>\n<!-- /WP CSS Audit Preview -->\n";
        }

        // Also output saved custom CSS
        $savedCss = $this->getCustomCss();
        if (!empty($savedCss)) {
            echo "\n<!-- WP CSS Audit Custom CSS -->\n<style id=\"wp-css-audit-custom\">\n";
            echo wp_kses_post($savedCss);
            echo "\n</style>\n<!-- /WP CSS Audit Custom CSS -->\n";
        }
    }
}
