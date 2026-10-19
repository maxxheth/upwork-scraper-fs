<?php

declare(strict_types=1);

namespace Upwork\Diagnostics;

use Upwork\Diagnostics\Monitors\MemoryMonitor;
use Upwork\Diagnostics\Monitors\ExecutionTimeMonitor;
use Upwork\Diagnostics\Monitors\QueryMonitor;
use Upwork\Diagnostics\Monitors\CrashPatternDetector;
use Upwork\Diagnostics\Admin\HealthDashboard;
use Upwork\Diagnostics\Logging\DiagnosticsLogger;

class Plugin
{
    private MemoryMonitor $memoryMonitor;
    private ExecutionTimeMonitor $executionTimeMonitor;
    private QueryMonitor $queryMonitor;
    private CrashPatternDetector $crashDetector;
    private HealthDashboard $dashboard;
    private DiagnosticsLogger $logger;

    public function init(): void
    {
        $this->registerDependencies();
        $this->registerHooks();
        $this->registerAdminPage();
        $this->registerRestRoutes();
    }

    private function registerDependencies(): void
    {
        $this->logger = new DiagnosticsLogger();
        $this->memoryMonitor = new MemoryMonitor($this->logger);
        $this->executionTimeMonitor = new ExecutionTimeMonitor($this->logger);
        $this->queryMonitor = new QueryMonitor($this->logger);
        $this->crashDetector = new CrashPatternDetector($this->logger);
        $this->dashboard = new HealthDashboard(
            $this->memoryMonitor,
            $this->executionTimeMonitor,
            $this->queryMonitor,
            $this->crashDetector
        );
    }

    private function registerHooks(): void
    {
        // Start monitoring early
        add_action('muplugins_loaded', [$this->executionTimeMonitor, 'start'], 0);
        add_action('muplugins_loaded', [$this->memoryMonitor, 'recordBaseline'], 0);

        // Monitor shutdown for crashes
        add_action('shutdown', [$this->crashDetector, 'checkForCrash'], 0);

        // Monitor DB queries
        if (defined('SAVEQUERIES') && SAVEQUERIES) {
            add_action('shutdown', [$this->queryMonitor, 'analyzeQueries'], 100);
        }

        // Add diagnostic info to admin bar
        add_action('admin_bar_menu', [$this->dashboard, 'addAdminBarInfo'], 100);

        // Health check endpoint
        add_action('wp_ajax_diagnostics_run_health', [$this->dashboard, 'ajaxRunHealth']);
        add_action('wp_ajax_nopriv_diagnostics_run_health', [$this->dashboard, 'ajaxRunHealth']);
    }

    private function registerAdminPage(): void
    {
        add_action('admin_menu', function () {
            add_menu_page(
                'WP Diagnostics',
                'Diagnostics',
                'manage_options',
                'wp-diagnostics',
                [$this->dashboard, 'render'],
                'dashicons-heartbeat',
                99
            );
        });

        add_action('admin_enqueue_scripts', function ($hook) {
            if (strpos($hook, 'wp-diagnostics') !== false) {
                wp_enqueue_style('wp-diagnostics', plugin_dir_url(__DIR__) . 'assets/diagnostics.css', [], '1.0.0');
                wp_enqueue_script('wp-diagnostics', plugin_dir_url(__DIR__) . 'assets/diagnostics.js', ['jquery'], '1.0.0', true);
                wp_localize_script('wp-diagnostics', 'wpDiagnostics', [
                    'ajaxUrl' => admin_url('admin-ajax.php'),
                    'nonce' => wp_create_nonce('wp_diagnostics'),
                ]);
            }
        });
    }

    private function registerRestRoutes(): void
    {
        add_action('rest_api_init', function () {
            register_rest_route('diagnostics/v1', '/health', [
                'methods' => 'GET',
                'callback' => [$this->dashboard, 'getHealthStatus'],
                'permission_callback' => fn() => current_user_can('manage_options'),
            ]);

            register_rest_route('diagnostics/v1', '/logs', [
                'methods' => 'GET',
                'callback' => [$this->logger, 'getLogs'],
                'permission_callback' => fn() => current_user_can('manage_options'),
            ]);

            register_rest_route('diagnostics/v1', '/crash-report', [
                'methods' => 'POST',
                'callback' => [$this->crashDetector, 'receiveCrashReport'],
                'permission_callback' => '__return_true',
            ]);
        });
    }
}
