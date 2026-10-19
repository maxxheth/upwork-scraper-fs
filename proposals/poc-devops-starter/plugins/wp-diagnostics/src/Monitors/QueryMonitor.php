<?php

declare(strict_types=1);

namespace Upwork\Diagnostics\Monitors;

use Upwork\Diagnostics\Logging\DiagnosticsLogger;

class QueryMonitor
{
    private DiagnosticsLogger $logger;
    private const SLOW_QUERY_THRESHOLD = 0.5; // seconds
    private const HIGH_QUERY_COUNT = 100;

    public function __construct(DiagnosticsLogger $logger)
    {
        $this->logger = $logger;
    }

    /**
     * Analyze database queries from SAVEQUERIES
     */
    public function analyzeQueries(): void
    {
        global $wpdb;

        if (!isset($wpdb->queries) || !is_array($wpdb->queries)) {
            return;
        }

        $totalTime = 0;
        $slowQueries = [];
        $queryCount = count($wpdb->queries);

        foreach ($wpdb->queries as $query) {
            // $query = [sql, duration, caller, ...]
            $sql = $query[0] ?? '';
            $duration = (float) ($query[1] ?? 0);
            $caller = $query[2] ?? '';

            $totalTime += $duration;

            if ($duration > self::SLOW_QUERY_THRESHOLD) {
                $slowQueries[] = [
                    'sql' => $this->sanitizeSql($sql),
                    'duration' => round($duration, 4),
                    'caller' => $caller,
                ];
            }
        }

        // Log if too many queries or slow queries found
        if ($queryCount > self::HIGH_QUERY_COUNT) {
            $this->logger->warning("High query count detected", [
                'count' => $queryCount,
                'total_time' => round($totalTime, 4),
            ]);
        }

        if (!empty($slowQueries)) {
            $this->logger->warning("Slow queries detected", [
                'count' => count($slowQueries),
                'queries' => $slowQueries,
            ]);
        }

        // Store for dashboard
        update_option('wp_diagnostics_last_query_analysis', [
            'total_queries' => $queryCount,
            'total_time' => round($totalTime, 4),
            'slow_queries' => $slowQueries,
            'avg_time' => $queryCount > 0 ? round($totalTime / $queryCount, 4) : 0,
            'analyzed_at' => current_time('mysql'),
        ]);
    }

    /**
     * Get query analysis report
     */
    public function getDetailedReport(): array
    {
        $analysis = get_option('wp_diagnostics_last_query_analysis', [
            'total_queries' => 0,
            'total_time' => 0,
            'slow_queries' => [],
            'avg_time' => 0,
            'analyzed_at' => 'Never',
        ]);

        return [
            'total_queries' => $analysis['total_queries'],
            'total_time_seconds' => $analysis['total_time'],
            'average_time_seconds' => $analysis['avg_time'],
            'slow_queries_count' => count($analysis['slow_queries']),
            'slow_queries' => $analysis['slow_queries'],
            'is_high_count' => $analysis['total_queries'] > self::HIGH_QUERY_COUNT,
            'analyzed_at' => $analysis['analyzed_at'],
            'savequeries_enabled' => defined('SAVEQUERIES') && SAVEQUERIES,
        ];
    }

    /**
     * Sanitize SQL for display (remove sensitive data)
     */
    private function sanitizeSql(string $sql): string
    {
        // Remove string literals
        $sql = preg_replace("/'[^']*'/", "'***'", $sql);
        // Truncate long queries
        if (strlen($sql) > 200) {
            $sql = substr($sql, 0, 200) . '...';
        }
        return $sql;
    }
}
