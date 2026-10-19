<?php

declare(strict_types=1);

namespace Upwork\Diagnostics\Monitors;

use Upwork\Diagnostics\Logging\DiagnosticsLogger;

class ExecutionTimeMonitor
{
    private DiagnosticsLogger $logger;
    private float $startTime = 0;
    private const WARNING_THRESHOLD = 5.0; // seconds
    private const CRITICAL_THRESHOLD = 10.0; // seconds

    public function __construct(DiagnosticsLogger $logger)
    {
        $this->logger = $logger;
    }

    /**
     * Start timing execution
     */
    public function start(): void
    {
        $this->startTime = microtime(true);
    }

    /**
     * Get elapsed time in seconds
     */
    public function getElapsedTime(): float
    {
        return round(microtime(true) - $this->startTime, 4);
    }

    /**
     * Get max execution time from PHP config
     */
    public function getMaxExecutionTime(): int
    {
        return (int) ini_get('max_execution_time');
    }

    /**
     * Get execution time as percentage of limit
     */
    public function getTimePercentage(): float
    {
        $max = $this->getMaxExecutionTime();
        if ($max <= 0) {
            return 0;
        }
        return round(($this->getElapsedTime() / $max) * 100, 1);
    }

    /**
     * Check if execution time is approaching limit
     */
    public function isWarning(): bool
    {
        return $this->getElapsedTime() > self::WARNING_THRESHOLD;
    }

    /**
     * Check if execution time is critical
     */
    public function isCritical(): bool
    {
        return $this->getElapsedTime() > self::CRITICAL_THRESHOLD;
    }

    /**
     * Get detailed execution time report
     */
    public function getDetailedReport(): array
    {
        return [
            'elapsed_seconds' => $this->getElapsedTime(),
            'max_execution_time' => $this->getMaxExecutionTime(),
            'time_percent' => $this->getTimePercentage(),
            'is_warning' => $this->isWarning(),
            'is_critical' => $this->isCritical(),
            'start_time' => date('Y-m-d H:i:s', (int) $this->startTime),
            'server_time' => date('Y-m-d H:i:s'),
        ];
    }
}
