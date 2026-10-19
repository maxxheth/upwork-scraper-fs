<?php

declare(strict_types=1);

namespace Upwork\Diagnostics\Admin;

use Upwork\Diagnostics\Monitors\MemoryMonitor;
use Upwork\Diagnostics\Monitors\ExecutionTimeMonitor;
use Upwork\Diagnostics\Monitors\QueryMonitor;
use Upwork\Diagnostics\Monitors\CrashPatternDetector;

class HealthDashboard
{
    private MemoryMonitor $memoryMonitor;
    private ExecutionTimeMonitor $executionTimeMonitor;
    private QueryMonitor $queryMonitor;
    private CrashPatternDetector $crashDetector;

    public function __construct(
        MemoryMonitor $memoryMonitor,
        ExecutionTimeMonitor $executionTimeMonitor,
        QueryMonitor $queryMonitor,
        CrashPatternDetector $crashDetector
    ) {
        $this->memoryMonitor = $memoryMonitor;
        $this->executionTimeMonitor = $executionTimeMonitor;
        $this->queryMonitor = $queryMonitor;
        $this->crashDetector = $crashDetector;
    }

    /**
     * Render the diagnostics dashboard
     */
    public function render(): void
    {
        $memory = $this->memoryMonitor->getDetailedReport();
        $execution = $this->executionTimeMonitor->getDetailedReport();
        $queries = $this->queryMonitor->getDetailedReport();
        $crashes = $this->crashDetector->getCrashStats();
        $crashHistory = $this->crashDetector->getCrashHistory(10);
        ?>
        <div class="wrap wp-diagnostics-dashboard">
            <h1>🔍 WP Diagnostics Dashboard</h1>
            <p>Real-time health monitoring for your WordPress site. Last updated: <?php echo current_time('mysql'); ?></p>

            <div class="diagnostics-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin:20px 0;">

                <!-- Memory Card -->
                <div class="diagnostics-card" style="background:#fff;padding:20px;border:1px solid #ddd;border-radius:8px;<?php echo $memory['is_critical'] ? 'border-color:#dc3232;' : ''; ?>">
                    <h3>🧠 Memory</h3>
                    <div class="metric">
                        <span class="label">Current:</span>
                        <span class="value"><?php echo $memory['current_usage_mb']; ?> MB</span>
                    </div>
                    <div class="metric">
                        <span class="label">Peak:</span>
                        <span class="value"><?php echo $memory['peak_usage_mb']; ?> MB</span>
                    </div>
                    <div class="metric">
                        <span class="label">Limit:</span>
                        <span class="value"><?php echo $memory['limit_mb']; ?> MB</span>
                    </div>
                    <div class="metric">
                        <span class="label">Usage:</span>
                        <span class="value <?php echo $memory['is_critical'] ? 'critical' : ''; ?>">
                            <?php echo $memory['usage_percent']; ?>%
                        </span>
                    </div>
                    <div class="progress-bar" style="height:8px;background:#f0f0f0;border-radius:4px;margin-top:10px;">
                        <div style="height:100%;width:<?php echo min($memory['usage_percent'], 100); ?>%;background:<?php echo $memory['is_critical'] ? '#dc3232' : '#46b450'; ?>;border-radius:4px;"></div>
                    </div>
                </div>

                <!-- Execution Time Card -->
                <div class="diagnostics-card" style="background:#fff;padding:20px;border:1px solid #ddd;border-radius:8px;<?php echo $execution['is_critical'] ? 'border-color:#dc3232;' : ($execution['is_warning'] ? 'border-color:#f0ad4e;' : ''); ?>">
                    <h3>⏱ Execution Time</h3>
                    <div class="metric">
                        <span class="label">Elapsed:</span>
                        <span class="value"><?php echo $execution['elapsed_seconds']; ?>s</span>
                    </div>
                    <div class="metric">
                        <span class="label">Max:</span>
                        <span class="value"><?php echo $execution['max_execution_time']; ?>s</span>
                    </div>
                    <div class="metric">
                        <span class="label">Usage:</span>
                        <span class="value <?php echo $execution['is_critical'] ? 'critical' : ''; ?>">
                            <?php echo $execution['time_percent']; ?>%
                        </span>
                    </div>
                </div>

                <!-- Database Card -->
                <div class="diagnostics-card" style="background:#fff;padding:20px;border:1px solid #ddd;border-radius:8px;<?php echo $queries['is_high_count'] ? 'border-color:#f0ad4e;' : ''; ?>">
                    <h3>🗄 Database</h3>
                    <div class="metric">
                        <span class="label">Total Queries:</span>
                        <span class="value"><?php echo $queries['total_queries']; ?></span>
                    </div>
                    <div class="metric">
                        <span class="label">Total Time:</span>
                        <span class="value"><?php echo $queries['total_time_seconds']; ?>s</span>
                    </div>
                    <div class="metric">
                        <span class="label">Avg Query:</span>
                        <span class="value"><?php echo $queries['average_time_seconds']; ?>s</span>
                    </div>
                    <div class="metric">
                        <span class="label">Slow Queries:</span>
                        <span class="value"><?php echo $queries['slow_queries_count']; ?></span>
                    </div>
                    <?php if (!$queries['savequeries_enabled']): ?>
                        <p style="color:#f0ad4e;font-size:12px;">⚠ SAVEQUERIES not enabled. Set <code>define('SAVEQUERIES', true);</code> in wp-config.php</p>
                    <?php endif; ?>
                </div>

                <!-- Crash Stats Card -->
                <div class="diagnostics-card" style="background:#fff;padding:20px;border:1px solid #ddd;border-radius:8px;<?php echo $crashes['total_crashes'] > 0 ? 'border-color:#dc3232;' : ''; ?>">
                    <h3>💥 Crash Statistics</h3>
                    <div class="metric">
                        <span class="label">Total Crashes:</span>
                        <span class="value"><?php echo $crashes['total_crashes']; ?></span>
                    </div>
                    <div class="metric">
                        <span class="label">Last 24h:</span>
                        <span class="value"><?php echo $crashes['last_24h']; ?></span>
                    </div>
                    <div class="metric">
                        <span class="label">Last 7d:</span>
                        <span class="value"><?php echo $crashes['last_7d']; ?></span>
                    </div>
                    <div class="metric">
                        <span class="label">Most Common:</span>
                        <span class="value" style="font-size:12px;"><?php echo esc_html($crashes['most_common_error']); ?></span>
                    </div>
                </div>
            </div>

            <!-- Crash History -->
            <?php if (!empty($crashHistory)): ?>
            <div style="background:#fff;padding:20px;border:1px solid #ddd;border-radius:8px;margin-top:20px;">
                <h3>Recent Crash Log</h3>
                <table class="wp-list-table widefat fixed striped">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Type</th>
                            <th>Message</th>
                            <th>File</th>
                            <th>Line</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($crashHistory as $crash): ?>
                        <tr>
                            <td><?php echo esc_html($crash['timestamp'] ?? ''); ?></td>
                            <td><?php echo esc_html($crash['type'] ?? ''); ?></td>
                            <td><?php echo esc_html(substr($crash['message'] ?? '', 0, 100)); ?></td>
                            <td><?php echo esc_html(basename($crash['file'] ?? '')); ?></td>
                            <td><?php echo esc_html($crash['line'] ?? ''); ?></td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
            <?php endif; ?>

            <!-- System Info -->
            <div style="background:#fff;padding:20px;border:1px solid #ddd;border-radius:8px;margin-top:20px;">
                <h3>System Information</h3>
                <table class="wp-list-table widefat fixed">
                    <tbody>
                        <tr><td>PHP Version</td><td><?php echo PHP_VERSION; ?></td></tr>
                        <tr><td>WordPress Version</td><td><?php echo get_bloginfo('version'); ?></td></tr>
                        <tr><td>Server Software</td><td><?php echo $_SERVER['SERVER_SOFTWARE'] ?? 'Unknown'; ?></td></tr>
                        <tr><td>Active Theme</td><td><?php echo wp_get_theme()->get('Name'); ?></td></tr>
                        <tr><td>Debug Mode</td><td><?php echo WP_DEBUG ? 'Enabled' : 'Disabled'; ?></td></tr>
                        <tr><td>Object Cache</td><td><?php echo wp_using_ext_object_cache() ? 'External (Redis)' : 'Disabled'; ?></td></tr>
                        <tr><td>MySQL Version</td><td><?php global $wpdb; echo $wpdb->db_version(); ?></td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        <?php
    }

    /**
     * Add quick health info to admin bar
     */
    public function addAdminBarInfo(\WP_Admin_Bar $adminBar): void
    {
        if (!current_user_can('manage_options')) {
            return;
        }

        $memory = $this->memoryMonitor->getUsagePercentage();
        $time = $this->executionTimeMonitor->getElapsedTime();
        $queries = $this->queryMonitor->getDetailedReport();

        $color = $memory > 85 ? '#dc3232' : ($memory > 70 ? '#f0ad4e' : '#46b450');

        $adminBar->add_node([
            'id' => 'wp-diagnostics',
            'title' => sprintf(
                '🧠 %d%% | ⏱ %.1fs | 🗄 %d',
                $memory,
                $time,
                $queries['total_queries']
            ),
            'href' => admin_url('admin.php?page=wp-diagnostics'),
            'meta' => ['style' => "background:{$color};color:#fff;padding:0 8px;border-radius:4px;"],
        ]);
    }

    /**
     * AJAX handler for running health check
     */
    public function ajaxRunHealth(): void
    {
        check_ajax_referer('wp_diagnostics');

        $memory = $this->memoryMonitor->getDetailedReport();
        $execution = $this->executionTimeMonitor->getDetailedReport();
        $queries = $this->queryMonitor->getDetailedReport();
        $crashes = $this->crashDetector->getCrashStats();

        wp_send_json_success([
            'memory' => $memory,
            'execution' => $execution,
            'queries' => $queries,
            'crashes' => $crashes,
            'timestamp' => current_time('mysql'),
        ]);
    }

    /**
     * REST endpoint for health status
     */
    public function getHealthStatus(): \WP_REST_Response
    {
        return new \WP_REST_Response([
            'status' => 'ok',
            'memory' => $this->memoryMonitor->getDetailedReport(),
            'execution' => $this->executionTimeMonitor->getDetailedReport(),
            'queries' => $this->queryMonitor->getDetailedReport(),
            'crashes' => $this->crashDetector->getCrashStats(),
            'timestamp' => current_time('mysql'),
        ], 200);
    }
}
