<?php

declare(strict_types=1);

namespace Upwork\Diagnostics\Monitors;

use Upwork\Diagnostics\Logging\DiagnosticsLogger;

class MemoryMonitor
{
    private DiagnosticsLogger $logger;
    private float $baselineMemory = 0;

    public function __construct(DiagnosticsLogger $logger)
    {
        $this->logger = $logger;
    }

    /**
     * Record baseline memory usage at plugin load
     */
    public function recordBaseline(): void
    {
        $this->baselineMemory = memory_get_usage(true);
    }

    /**
     * Get current memory usage in MB
     */
    public function getCurrentUsage(): float
    {
        return round(memory_get_usage(true) / 1024 / 1024, 2);
    }

    /**
     * Get peak memory usage in MB
     */
    public function getPeakUsage(): float
    {
        return round(memory_get_peak_usage(true) / 1024 / 1024, 2);
    }

    /**
     * Get memory limit in MB
     */
    public function getMemoryLimit(): float
    {
        $limit = ini_get('memory_limit');
        return $this->convertToMegabytes($limit);
    }

    /**
     * Get memory usage as percentage of limit
     */
    public function getUsagePercentage(): float
    {
        $limit = $this->getMemoryLimit();
        if ($limit <= 0) {
            return 0;
        }
        return round(($this->getPeakUsage() / $limit) * 100, 1);
    }

    /**
     * Check if memory usage is critical (>85%)
     */
    public function isCritical(): bool
    {
        return $this->getUsagePercentage() > 85;
    }

    /**
     * Get detailed memory breakdown
     */
    public function getDetailedReport(): array
    {
        return [
            'current_usage_mb' => $this->getCurrentUsage(),
            'peak_usage_mb' => $this->getPeakUsage(),
            'limit_mb' => $this->getMemoryLimit(),
            'usage_percent' => $this->getUsagePercentage(),
            'is_critical' => $this->isCritical(),
            'baseline_mb' => round($this->baselineMemory / 1024 / 1024, 2),
            'wp_memory_limit' => defined('WP_MEMORY_LIMIT') ? WP_MEMORY_LIMIT : 'N/A',
            'wp_max_memory_limit' => defined('WP_MAX_MEMORY_LIMIT') ? WP_MAX_MEMORY_LIMIT : 'N/A',
        ];
    }

    /**
     * Convert PHP ini memory value to megabytes
     */
    private function convertToMegabytes(string $value): float
    {
        $value = trim($value);
        $unit = strtolower(substr($value, -1));
        $number = (float) substr($value, 0, -1);

        return match ($unit) {
            'g' => $number * 1024,
            'm' => $number,
            'k' => $number / 1024,
            default => (float) $value / 1024 / 1024,
        };
    }
}
