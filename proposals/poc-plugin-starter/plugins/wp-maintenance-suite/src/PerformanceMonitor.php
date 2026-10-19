<?php

declare(strict_types=1);

namespace Nous\WpMaintenanceSuite;

/**
 * Performance monitor - tracks DB query count, page load time, cache status.
 */
final class PerformanceMonitor
{
    private const SNAPSHOT_OPTION = 'wp_maintenance_perf_snapshots';

    /**
     * Log a performance snapshot.
     *
     * @return array<string, mixed>
     */
    public function logPerformanceSnapshot(): array
    {
        $snapshot = $this->measureCurrentPerformance();
        $this->storeSnapshot($snapshot);
        return $snapshot;
    }

    /**
     * Get recent performance snapshots.
     *
     * @return array<int, array<string, mixed>>
     */
    public function getRecentSnapshots(int $count = 10): array
    {
        $snapshots = get_option(self::SNAPSHOT_OPTION, []);
        return array_slice($snapshots, -$count);
    }

    /**
     * Get current performance report.
     *
     * @return array<string, mixed>
     */
    public function getCurrentReport(): array
    {
        return $this->measureCurrentPerformance();
    }

    /**
     * Measure current site performance.
     *
     * @return array<string, mixed>
     */
    private function measureCurrentPerformance(): array
    {
        global $wpdb;

        // Measure page load time (approximate)
        $startTime = microtime(true);

        // Count DB queries
        $queryCount = $wpdb->num_queries;

        // Check cache status
        $cacheStatus = $this->checkCacheStatus();

        // Check object cache
        $objectCache = wp_using_ext_object_cache();

        // Check database size
        $dbSize = $this->getDatabaseSize();

        $loadTime = microtime(true) - $startTime;

        return [
            'timestamp'          => current_time('mysql'),
            'page_load_time_ms'  => round($loadTime * 1000, 2),
            'db_query_count'     => $queryCount,
            'db_size_mb'         => $dbSize,
            'object_cache'       => $objectCache,
            'page_cache'         => $cacheStatus['page_cache'],
            'cache_plugins'      => $cacheStatus['plugins'],
            'php_memory_mb'      => round(memory_get_peak_usage(true) / 1024 / 1024, 2),
            'php_version'        => PHP_VERSION,
        ];
    }

    /**
     * Check cache status.
     *
     * @return array<string, mixed>
     */
    private function checkCacheStatus(): array
    {
        $cachePlugins = [];

        // Check for common caching plugins
        $knownCachePlugins = [
            'wp-super-cache/wp-cache.php'       => 'WP Super Cache',
            'w3-total-cache/w3-total-cache.php' => 'W3 Total Cache',
            'wp-rocket/wp-rocket.php'           => 'WP Rocket',
            'litespeed-cache/litespeed-cache.php' => 'LiteSpeed Cache',
            'wp-fastest-cache/wpFastestCache.php' => 'WP Fastest Cache',
            'cache-enabler/cache-enabler.php'    => 'Cache Enabler',
            'hummingbird-performance/wp-hummingbird.php' => 'Hummingbird',
        ];

        foreach ($knownCachePlugins as $pluginFile => $pluginName) {
            if (is_plugin_active($pluginFile)) {
                $cachePlugins[] = $pluginName;
            }
        }

        return [
            'page_cache' => !empty($cachePlugins),
            'plugins'    => $cachePlugins,
        ];
    }

    /**
     * Get approximate database size.
     */
    private function getDatabaseSize(): float
    {
        global $wpdb;

        $size = $wpdb->get_var(
            $wpdb->prepare(
                "SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2)
                 FROM information_schema.tables
                 WHERE table_schema = %s",
                DB_NAME
            )
        );

        return (float) ($size ?? 0);
    }

    /**
     * Store a snapshot in options.
     */
    private function storeSnapshot(array $snapshot): void
    {
        $snapshots   = get_option(self::SNAPSHOT_OPTION, []);
        $snapshots[] = $snapshot;

        // Keep only last 100 snapshots
        if (count($snapshots) > 100) {
            $snapshots = array_slice($snapshots, -100);
        }

        update_option(self::SNAPSHOT_OPTION, $snapshots, false);
    }
}
