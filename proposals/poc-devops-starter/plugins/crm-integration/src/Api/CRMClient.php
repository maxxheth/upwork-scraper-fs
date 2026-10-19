<?php

declare(strict_types=1);

namespace Upwork\CRMIntegration\Api;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\GuzzleException;
use Psr\Log\LoggerInterface;
use Psr\Log\NullLogger;

class CRMClient
{
    private Client $httpClient;
    private LoggerInterface $logger;
    private string $apiUrl;
    private string $apiKey;

    public function __construct(
        string $apiUrl,
        string $apiKey,
        ?Client $httpClient = null,
        ?LoggerInterface $logger = null
    ) {
        $this->apiUrl = rtrim($apiUrl, '/');
        $this->apiKey = $apiKey;
        $this->httpClient = $httpClient ?? new Client([
            'timeout' => 30,
            'connect_timeout' => 10,
            'headers' => [
                'Authorization' => "Bearer {$apiKey}",
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
                'User-Agent' => 'WordPress-CRM-Integration/1.0',
            ],
        ]);
        $this->logger = $logger ?? new NullLogger();
    }

    /**
     * Create or update a contact in the CRM
     */
    public function upsertContact(array $contactData): array
    {
        return $this->request('POST', '/api/v1/contacts', [
            'json' => $contactData,
        ]);
    }

    /**
     * Create or update a deal in the CRM
     */
    public function upsertDeal(array $dealData): array
    {
        return $this->request('POST', '/api/v1/deals', [
            'json' => $dealData,
        ]);
    }

    /**
     * Get contact by email
     */
    public function getContactByEmail(string $email): ?array
    {
        $result = $this->request('GET', '/api/v1/contacts', [
            'query' => ['email' => $email],
        ]);

        return $result['data'][0] ?? null;
    }

    /**
     * Get all contacts modified since a timestamp
     */
    public function getModifiedContacts(\DateTimeInterface $since): array
    {
        $result = $this->request('GET', '/api/v1/contacts', [
            'query' => [
                'modified_since' => $since->format('c'),
                'limit' => 100,
            ],
        ]);

        return $result['data'] ?? [];
    }

    /**
     * Test API connection
     */
    public function testConnection(): bool
    {
        try {
            $this->request('GET', '/api/v1/health');
            return true;
        } catch (\Exception $e) {
            $this->logger->error('CRM connection test failed', [
                'error' => $e->getMessage(),
            ]);
            return false;
        }
    }

    /**
     * Make an HTTP request to the CRM API
     */
    private function request(string $method, string $endpoint, array $options = []): array
    {
        $url = $this->apiUrl . $endpoint;

        try {
            $this->logger->debug("CRM API request: {$method} {$url}");

            $response = $this->httpClient->request($method, $url, $options);
            $body = (string) $response->getBody();
            $statusCode = $response->getStatusCode();

            $this->logger->debug("CRM API response: {$statusCode}");

            $data = json_decode($body, true);
            if (json_last_error() !== JSON_ERROR_NONE) {
                throw new \RuntimeException('Invalid JSON response from CRM API');
            }

            return $data;
        } catch (GuzzleException $e) {
            $this->logger->error('CRM API request failed', [
                'endpoint' => $endpoint,
                'method' => $method,
                'error' => $e->getMessage(),
            ]);
            throw new \RuntimeException(
                "CRM API request failed: {$e->getMessage()}",
                $e->getCode(),
                $e
            );
        }
    }
}
