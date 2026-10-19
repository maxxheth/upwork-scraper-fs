<?php

declare(strict_types=1);

namespace Upwork\Diagnostics\Logging;

class DiagnosticsLogger
{
    private const LOG_KEY = 'wp_diagnostics_log';
    private const MAX_LOG_ENTRIES = 500;

    /**
     * Log a critical event
     */
    public function critical(string $message, array $context = []): void
    {
        $this->log('critical', $message, $context);
    }

    /**
     * Log a warning
     */
    public function warning(string $message, array $context = []): void
    {
        $this->log('warning', $message, $context);
    }

    /**
     * Log an info event
     */
    public function info(string $message, array $context = []): void
    {
        $this->log('info', $message, $context);
    }

    /**
     * Log a debug event
     */
    public function debug(string $message, array $context = []): void
    {
        if (defined('WP_DEBUG') && WP_DEBUG) {
            $this->log('debug', $message, $context);
        }
    }

    /**
     * Write a log entry
     */
    private function log(string $level, string $message, array $context): void
    {
        $entry = [
            'level' => $level,
            'message' => $message,
            'context' => $context,
            'timestamp' => current_time('mysql'),
            'memory' => round(memory_get_usage(true) / 1024 / 1024, 2) . ' MB',
            'request_uri' => $_SERVER['REQUEST_URI'] ?? 'CLI',
        ];

        $logs = get_option(self::LOG_KEY, []);
        array_unshift($logs, $entry);

        // Trim to max entries
        if (count($logs) > self::MAX_LOG_ENTRIES) {
            $logs = array_slice($logs, 0, self::MAX_LOG_ENTRIES);
        }

        update_option(self::LOG_KEY, $logs);

        // Also write to WP debug log if enabled
        if (defined('WP_DEBUG_LOG') && WP_DEBUG_LOG) {
            error_log(sprintf(
                '[WP Diagnostics] [%s] %s %s',
                strtoupper($level),
                $message,
                !empty($context) ? wp_json_encode($context) : ''
            ));
        }
    }

    /**
     * Get log entries
     */
    public function getLogs(\WP_REST_Request $request): \WP_REST_Response
    {
        $level = $request->get_param('level');
        $limit = min((int) $request->get_param('limit'), 100) ?: 50;

        $logs = get_option(self::LOG_KEY, []);

        if ($level) {
            $logs = array_filter($logs, fn($log) => $log['level'] === $level);
        }

        return new \WP_REST_Response([
            'success' => true,
            'data' => array_slice(array_values($logs), 0, $limit),
            'total' => count($logs),
        ], 200);
    }

    /**
     * Clear all logs
     */
    public function clearLogs(): void
    {
        delete_option(self::LOG_KEY);
    }
}
