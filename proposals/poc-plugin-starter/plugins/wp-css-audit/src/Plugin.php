<?php

declare(strict_types=1);

namespace Nous\WpCssAudit;

/**
 * Main plugin class - bootstraps all components.
 */
final class Plugin
{
    private static ?Plugin $instance = null;

    private AdminPage $adminPage;
    private TemplateScanner $scanner;
    private CssEditor $cssEditor;

    public function __construct()
    {
        $this->scanner   = new TemplateScanner();
        $this->cssEditor = new CssEditor();
        $this->adminPage = new AdminPage($this->scanner, $this->cssEditor);
    }

    public function boot(): void
    {
        $this->adminPage->register();
        $this->cssEditor->register();

        // Enqueue admin assets
        add_action('admin_enqueue_scripts', [$this, 'enqueueAdminAssets']);
    }

    public function enqueueAdminAssets(string $hook): void
    {
        if ($hook !== 'toplevel_page_wp-css-audit') {
            return;
        }

        wp_enqueue_code_editor(['type' => 'text/css']);
        wp_enqueue_script('wp-css-audit-admin', plugin_dir_url(__DIR__ . '/../wp-css-audit.php') . 'assets/admin.js', ['jquery', 'wp-codemirror'], '1.0.0', true);
        wp_enqueue_style('wp-css-audit-admin', plugin_dir_url(__DIR__ . '/../wp-css-audit.php') . 'assets/admin.css', [], '1.0.0');

        wp_localize_script('wp-css-audit-admin', 'wpCssAudit', [
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce'   => wp_create_nonce('wp_css_audit_nonce'),
        ]);
    }

    public static function getInstance(): self
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
}
