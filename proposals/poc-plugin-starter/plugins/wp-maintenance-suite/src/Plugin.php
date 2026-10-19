<?php

declare(strict_types=1);

namespace Nous\WpMaintenanceSuite;

/**
 * Main plugin class for Maintenance Suite.
 */
final class Plugin
{
    private static ?Plugin $instance = null;

    private SecurityAuditor $securityAuditor;
    private PerformanceMonitor $performanceMonitor;
    private WooCommerceSeeder $wooCommerceSeeder;
    private AdminDashboard $adminDashboard;

    public function __construct()
    {
        $this->securityAuditor    = new SecurityAuditor();
        $this->performanceMonitor = new PerformanceMonitor();
        $this->wooCommerceSeeder  = new WooCommerceSeeder();
        $this->adminDashboard     = new AdminDashboard(
            $this->securityAuditor,
            $this->performanceMonitor,
            $this->wooCommerceSeeder
        );
    }

    public function boot(): void
    {
        $this->adminDashboard->register();
        $this->wooCommerceSeeder->register();

        // Schedule maintenance tasks
        add_action('wp', [$this, 'scheduleMaintenanceTasks']);
        add_action('wp_maintenance_daily_check', [$this, 'runDailyMaintenance']);
    }

    public function scheduleMaintenanceTasks(): void
    {
        if (!wp_next_scheduled('wp_maintenance_daily_check')) {
            wp_schedule_event(time(), 'daily', 'wp_maintenance_daily_check');
        }
    }

    public function runDailyMaintenance(): void
    {
        $this->securityAuditor->runSecurityCheck();
        $this->performanceMonitor->logPerformanceSnapshot();
    }

    public static function getInstance(): self
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
}
