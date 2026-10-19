<?php

declare(strict_types=1);

namespace Upwork\Diagnostics\Monitors;

use Upwork\Diagnostics\Logging\DiagnosticsLogger;

class CrashPatternDetector
{
    private DiagnosticsLogger $logger;
    private const CRASH_LOG_KEY = 'wp_diagnostics_crash_log';
    private const MAX_CRASH_ENTRIES = 100;

    public function __construct(DiagnosticsLogger $logger)
    {
        $this->logger = $logger;
    }

    /**
     * Check for crash patterns on shutdown
     */
    public function checkForCrash(): void
    {
        $error = error_get_last();

        if ($error === null) {
            return;
        }

        // Only catch fatal errors
        if (!in_array($error['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR, E_USER_ERROR])) {
            return;
        }

        $crashData = [
            'type' => $this->getErrorTypeName($error['type']),
            'message' => $error['message'],
            'file' => $error['file'],
            'line' => $error['line'],
            'memory_at_crash' => $this->getMemoryAtCrash(),
            'request_uri' => $_SERVER['REQUEST_URI'] ?? 'CLI',
            'request_method' => $_SERVER['REQUEST_METHOD'] ?? 'CLI',
            'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? 'Unknown',
            'timestamp' => current_time('mysql'),
            'active_plugins' => $this->getActivePlugins(),
            'theme' => wp_get_theme()->get('Name'),
        ];

        $this->logCrash($crashData);
        $this->logger->critical("WordPress crash detected", $crashData);
    }

    /**
     * Receive crash report from frontend JS
     */
    public function receiveCrashReport(\WP_REST_Request $request): \WP_REST_Response
    {
        $data = $request->get_json_params();

        $crashData = [
            'type' => 'js_error',
            'message' => $data['message'] ?? 'Unknown JS error',
            'file' => $data['file'] ?? '',
            'line' => $data['line'] ?? 0,
            'stack' => $data['stack'] ?? '',
            'url' => $data['url'] ?? '',
            'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? 'Unknown',
            'timestamp' => current_time('mysql'),
        ];

        $this->logCrash($crashData);
        $this->logger->warning("Frontend JS error reported", $crashData);

        return new \WP_REST_Response(['success' => true], 200);
    }

    /**
     * Get crash history
     */
    public function getCrashHistory(int $limit = 20): array
    {
        $crashes = get_option(self::CRASH_LOG_KEY, []);
        return array_slice($crashes, 0, $limit);
    }

    /**
     * Get crash statistics
     */
    public function getCrashStats(): array
    {
        $crashes = get_option(self::CRASH_LOG_KEY, []);
        $total = count($crashes);

        // Count by type
        $byType = [];
        $last24h = 0;
        $last7d = 0;
        $now = current_time('timestamp');

        foreach ($crashes as $crash) {
            $type = $crash['type'] ?? 'unknown';
            $byType[$type] = ($byType[$type] ?? 0) + 1;

            $crashTime = strtotime($crash['timestamp'] ?? 'now');
            $diff = $now - $crashTime;

            if ($diff < 86400) {
                $last24h++;
            }
            if ($diff < 604800) {
                $last7d++;
            }
        }

        return [
            'total_crashes' => $total,
            'last_24h' => $last24h,
            'last_7d' => $last7d,
            'by_type' => $byType,
            'most_common_error' => $this->getMostCommonError($crashes),
        ];
    }

    /**
     * Get memory usage at time of crash
     */
    private function getMemoryAtCrash(): array
    {
        return [
            'memory_usage' => round(memory_get_usage(true) / 1024 / 1024, 2) . ' MB',
            'memory_peak' => round(memory_get_peak_usage(true) / 1024 / 1024, 2) . ' MB',
            'memory_limit' => ini_get('memory_limit'),
        ];
    }

    /**
     * Get list of active plugins
     */
    private function getActivePlugins(): array
    {
        if (!function_exists('get_option')) {
            return [];
        }
        $plugins = get_option('active_plugins', []);
        $result = [];
        foreach ($plugins as $plugin) {
            $result[] = basename(dirname($plugin)) . '/' . basename($plugin);
        }
        return $result;
    }

    /**
     * Log a crash entry
     */
    private function logCrash(array $crashData): void
    {
        $crashes = get_option(self::CRASH_LOG_KEY, []);
        array_unshift($crashes, $crashData);

        // Keep only the latest entries
        if (count($crashes) > self::MAX_CRASH_ENTRIES) {
            $crashes = array_slice($crashes, 0, self::MAX_CRASH_ENTRIES);
        }

        update_option(self::CRASH_LOG_KEY, $crashes);
    }

    /**
     * Find the most common error message
     */
    private function getMostCommonError(array $crashes): string
    {
        $messages = array_count_values(
            array_column($crashes, 'message')
        );
        arsort($messages);
        $top = array_keys($messages);
        return $top[0] ?? 'None';
    }

    /**
     * Convert PHP error constant to readable name
     */
    private function getErrorTypeName(int $type): string
    {
        return match ($type) {
            E_ERROR => 'Fatal Error',
            E_PARSE => 'Parse Error',
            E_CORE_ERROR => 'Core Error',
            E_COMPILE_ERROR => 'Compile Error',
            E_USER_ERROR => 'User Error',
            default => 'Unknown Error',
        };
    }
}
