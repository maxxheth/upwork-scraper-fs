<?php

declare(strict_types=1);

namespace Upwork\SiteArchitect;

use Upwork\SiteArchitect\Audit\ThemeAnalyzer;
use Upwork\SiteArchitect\Audit\PluginDependencyGraph;
use Upwork\SiteArchitect\Audit\DatabaseSchemaReviewer;
use Upwork\SiteArchitect\Api\HeadlessCMSController;
use Upwork\SiteArchitect\Blocks\CustomBlockRegistrar;

class Plugin
{
    private ThemeAnalyzer $themeAnalyzer;
    private PluginDependencyGraph $dependencyGraph;
    private DatabaseSchemaReviewer $schemaReviewer;
    private HeadlessCMSController $headlessCMS;
    private CustomBlockRegistrar $blockRegistrar;

    public function init(): void
    {
        $this->registerDependencies();
        $this->registerHooks();
        $this->registerRestRoutes();
        $this->registerAdminPage();
        $this->registerBlocks();
    }

    private function registerDependencies(): void
    {
        $this->themeAnalyzer = new ThemeAnalyzer();
        $this->dependencyGraph = new PluginDependencyGraph();
        $this->schemaReviewer = new DatabaseSchemaReviewer();
        $this->headlessCMS = new HeadlessCMSController();
        $this->blockRegistrar = new CustomBlockRegistrar();
    }

    private function registerHooks(): void
    {
        // Extend WP REST API with headless CMS features
        add_filter('rest_prepare_post', [$this->headlessCMS, 'preparePostResponse'], 10, 3);
        add_filter('rest_prepare_page', [$this->headlessCMS, 'preparePostResponse'], 10, 3);

        // Add custom meta fields to REST API
        add_action('init', [$this->headlessCMS, 'registerCustomMetaFields']);

        // Register custom post types for the architecture audit
        add_action('init', [$this, 'registerAuditPostTypes']);
    }

    private function registerRestRoutes(): void
    {
        add_action('rest_api_init', function () {
            // Headless CMS routes
            $this->headlessCMS->registerRoutes();

            // Audit routes
            register_rest_route('site-architect/v1', '/audit/theme', [
                'methods' => 'GET',
                'callback' => [$this->themeAnalyzer, 'analyze'],
                'permission_callback' => fn() => current_user_can('manage_options'),
            ]);

            register_rest_route('site-architect/v1', '/audit/plugins', [
                'methods' => 'GET',
                'callback' => [$this->dependencyGraph, 'analyze'],
                'permission_callback' => fn() => current_user_can('manage_options'),
            ]);

            register_rest_route('site-architect/v1', '/audit/database', [
                'methods' => 'GET',
                'callback' => [$this->schemaReviewer, 'review'],
                'permission_callback' => fn() => current_user_can('manage_options'),
            ]);

            register_rest_route('site-architect/v1', '/audit/full', [
                'methods' => 'GET',
                'callback' => [$this, 'runFullAudit'],
                'permission_callback' => fn() => current_user_can('manage_options'),
            ]);
        });
    }

    private function registerAdminPage(): void
    {
        add_action('admin_menu', function () {
            add_menu_page(
                'Site Architect',
                'Site Architect',
                'manage_options',
                'site-architect',
                [$this, 'renderAdminPage'],
                'dashicons-building',
                30
            );
        });

        add_action('admin_enqueue_scripts', function ($hook) {
            if (strpos($hook, 'site-architect') !== false) {
                wp_enqueue_style('site-architect', plugin_dir_url(__DIR__) . 'assets/architect.css', [], '1.0.0');
                wp_enqueue_script('site-architect', plugin_dir_url(__DIR__) . 'assets/architect.js', ['jquery', 'wp-api'], '1.0.0', true);
            }
        });
    }

    private function registerBlocks(): void
    {
        add_action('init', [$this->blockRegistrar, 'registerBlocks']);
    }

    public function registerAuditPostTypes(): void
    {
        register_post_type('audit_report', [
            'labels' => [
                'name' => 'Audit Reports',
                'singular_name' => 'Audit Report',
            ],
            'public' => false,
            'show_ui' => true,
            'show_in_menu' => 'site-architect',
            'supports' => ['title', 'editor', 'custom-fields'],
            'show_in_rest' => true,
        ]);
    }

    public function runFullAudit(): \WP_REST_Response
    {
        $theme = $this->themeAnalyzer->analyze();
        $plugins = $this->dependencyGraph->analyze();
        $database = $this->schemaReviewer->review();

        $report = [
            'theme' => $theme->data,
            'plugins' => $plugins->data,
            'database' => $database->data,
            'summary' => $this->generateSummary($theme->data, $plugins->data, $database->data),
            'generated_at' => current_time('mysql'),
        ];

        // Save report as a post
        $reportId = wp_insert_post([
            'post_title' => sprintf('Full Audit Report - %s', current_time('Y-m-d H:i')),
            'post_type' => 'audit_report',
            'post_status' => 'publish',
            'meta_input' => ['audit_data' => wp_json_encode($report)],
        ]);

        return new \WP_REST_Response([
            'success' => true,
            'report_id' => $reportId,
            'data' => $report,
        ], 200);
    }

    private function generateSummary(array $theme, array $plugins, array $database): array
    {
        $issues = 0;
        $warnings = 0;

        // Theme issues
        if (!empty($theme['warnings'])) {
            $warnings += count($theme['warnings']);
        }
        if (!empty($theme['issues'])) {
            $issues += count($theme['issues']);
        }

        // Plugin issues
        if (!empty($plugins['conflicts'])) {
            $issues += count($plugins['conflicts']);
        }
        if (!empty($plugins['inactive_dependencies'])) {
            $warnings += count($plugins['inactive_dependencies']);
        }

        // Database issues
        if (!empty($database['missing_indexes'])) {
            $issues += count($database['missing_indexes']);
        }
        if (!empty($database['orphaned_tables'])) {
            $warnings += count($database['orphaned_tables']);
        }

        $healthScore = max(0, 100 - ($issues * 10) - ($warnings * 3));

        return [
            'health_score' => $healthScore,
            'total_issues' => $issues,
            'total_warnings' => $warnings,
            'recommendations' => $this->generateRecommendations($theme, $plugins, $database),
        ];
    }

    private function generateRecommendations(array $theme, array $plugins, array $database): array
    {
        $recommendations = [];

        if (!empty($theme['warnings'])) {
            $recommendations[] = 'Address theme warnings to improve performance and security';
        }

        if (!empty($plugins['conflicts'])) {
            $recommendations[] = 'Resolve plugin conflicts to prevent functionality issues';
        }

        if (!empty($database['missing_indexes'])) {
            $recommendations[] = 'Add missing database indexes to improve query performance';
        }

        if (!empty($database['orphaned_tables'])) {
            $recommendations[] = 'Clean up orphaned database tables from deactivated plugins';
        }

        if (empty($recommendations)) {
            $recommendations[] = 'Site architecture looks healthy. Continue monitoring.';
        }

        return $recommendations;
    }

    public function renderAdminPage(): void
    {
        ?>
        <div class="wrap site-architect-dashboard">
            <h1>🏗 Site Architect</h1>
            <p>Comprehensive architecture audit and headless CMS management for your B2B SaaS site.</p>

            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin:20px 0;">
                <a href="<?php echo admin_url('admin.php?page=site-architect&tab=audit'); ?>" class="button button-primary" style="padding:20px;text-align:center;font-size:16px;">
                    🔍 Run Full Audit
                </a>
                <a href="<?php echo admin_url('admin.php?page=site-architect&tab=headless'); ?>" class="button button-secondary" style="padding:20px;text-align:center;font-size:16px;">
                    🌐 Headless CMS Settings
                </a>
                <a href="<?php echo admin_url('admin.php?page=site-architect&tab=blocks'); ?>" class="button button-secondary" style="padding:20px;text-align:center;font-size:16px;">
                    🧱 Block Builder
                </a>
            </div>

            <div id="site-architect-app">
                <p>Loading audit dashboard...</p>
            </div>
        </div>
        <?php
    }
}
