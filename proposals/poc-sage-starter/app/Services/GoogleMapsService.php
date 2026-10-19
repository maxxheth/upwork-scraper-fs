<?php
/**
 * Google Maps Integration Service
 *
 * Handles geocoding, distance calculations, and map rendering.
 * Used by the Property Listing Map Gutenberg block and property components.
 *
 * @package Sage\Services
 */

namespace App\Services;

class GoogleMapsService
{
    /**
     * Google Maps API key
     *
     * @var string
     */
    protected string $apiKey;

    /**
     * Base URL for Geocoding API
     */
    const GEOCODING_BASE_URL = 'https://maps.googleapis.com/maps/api/geocode/json';

    /**
     * Constructor
     */
    public function __construct()
    {
        $this->apiKey = defined('GOOGLE_MAPS_API_KEY')
            ? GOOGLE_MAPS_API_KEY
            : (getenv('GOOGLE_MAPS_API_KEY') ?: '');
    }

    /**
     * Get the Google Maps API key
     *
     * @return string
     */
    public function getApiKey(): string
    {
        return $this->apiKey;
    }

    /**
     * Check if the API key is configured
     *
     * @return bool
     */
    public function isConfigured(): bool
    {
        return !empty($this->apiKey);
    }

    /**
     * Geocode an address to coordinates
     *
     * @param string $address The address to geocode
     * @return array{lat: float, lng: float}|null Returns lat/lng or null on failure
     */
    public function geocode(string $address): ?array
    {
        if (!$this->isConfigured()) {
            trigger_error('Google Maps API key not configured', E_USER_WARNING);
            return null;
        }

        $url = add_query_arg([
            'address' => urlencode($address),
            'key'     => $this->apiKey,
        ], self::GEOCODING_BASE_URL);

        $response = wp_remote_get($url, [
            'timeout' => 10,
            'headers' => [
                'Accept' => 'application/json',
            ],
        ]);

        if (is_wp_error($response)) {
            trigger_error('Geocoding request failed: ' . $response->get_error_message(), E_USER_WARNING);
            return null;
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        if (empty($data['results'][0]['geometry']['location'])) {
            return null;
        }

        return [
            'lat' => (float) $data['results'][0]['geometry']['location']['lat'],
            'lng' => (float) $data['results'][0]['geometry']['location']['lng'],
        ];
    }

    /**
     * Batch geocode multiple addresses
     *
     * @param array $addresses Array of address strings
     * @return array Array of ['address' => string, 'lat' => float, 'lng' => float] or ['address' => string, 'error' => string]
     */
    public function batchGeocode(array $addresses): array
    {
        $results = [];

        foreach ($addresses as $address) {
            $coords = $this->geocode($address);

            if ($coords) {
                $results[] = [
                    'address' => $address,
                    'lat'     => $coords['lat'],
                    'lng'     => $coords['lng'],
                ];
            } else {
                $results[] = [
                    'address' => $address,
                    'error'   => 'Could not geocode address',
                ];
            }

            // Respect rate limits (2 requests per second for free tier)
            usleep(500000);
        }

        return $results;
    }

    /**
     * Calculate distance between two coordinates using the Haversine formula
     *
     * @param float $lat1 Latitude of point 1
     * @param float $lng1 Longitude of point 1
     * @param float $lat2 Latitude of point 2
     * @param float $lng2 Longitude of point 2
     * @param string $unit 'mi' for miles, 'km' for kilometers
     * @return float Distance in the specified unit
     */
    public function calculateDistance(
        float $lat1,
        float $lng1,
        float $lat2,
        float $lng2,
        string $unit = 'mi'
    ): float {
        $earthRadius = ($unit === 'km') ? 6371 : 3959;

        $dLat = deg2rad($lat2 - $lat1);
        $dLng = deg2rad($lng2 - $lng1);

        $a = sin($dLat / 2) * sin($dLat / 2) +
             cos(deg2rad($lat1)) * cos(deg2rad($lat2)) *
             sin($dLng / 2) * sin($dLng / 2);

        $c = 2 * atan2(sqrt($a), sqrt(1 - $a));

        return round($earthRadius * $c, 2);
    }

    /**
     * Find properties within a radius of a point
     *
     * @param float $centerLat Center latitude
     * @param float $centerLng Center longitude
     * @param float $radius Radius in miles
     * @param array $additionalArgs Additional WP_Query args
     * @return \WP_Post[] Array of property posts within radius
     */
    public function findPropertiesNearby(
        float $centerLat,
        float $centerLng,
        float $radius = 25,
        array $additionalArgs = []
    ): array {
        $args = array_merge([
            'post_type'      => 'property',
            'posts_per_page' => 50,
            'meta_query'     => [
                [
                    'key'     => 'property_lat',
                    'compare' => 'EXISTS',
                ],
                [
                    'key'     => 'property_lng',
                    'compare' => 'EXISTS',
                ],
            ],
        ], $additionalArgs);

        $query = new \WP_Query($args);
        $nearby = [];

        while ($query->have_posts()) {
            $query->the_post();
            $postId = get_the_ID();

            $lat = get_field('property_lat', $postId);
            $lng = get_field('property_lng', $postId);

            if ($lat && $lng) {
                $distance = $this->calculateDistance(
                    $centerLat,
                    $centerLng,
                    (float) $lat,
                    (float) $lng
                );

                if ($distance <= $radius) {
                    $nearby[] = get_post($postId);
                }
            }
        }

        wp_reset_postdata();

        return $nearby;
    }

    /**
     * Render the Google Maps JavaScript API script tag
     *
     * @param array $options Additional map options (libraries, version, etc.)
     * @return string The script tag HTML
     */
    public function renderApiScript(array $options = []): string
    {
        if (!$this->isConfigured()) {
            return '<!-- Google Maps API key not configured -->';
        }

        $queryArgs = [
            'key' => $this->apiKey,
        ];

        if (!empty($options['libraries'])) {
            $queryArgs['libraries'] = is_array($options['libraries'])
                ? implode(',', $options['libraries'])
                : $options['libraries'];
        }

        if (!empty($options['version'])) {
            $queryArgs['v'] = $options['version'];
        }

        $url = add_query_arg($queryArgs, 'https://maps.googleapis.com/maps/api/js');

        return sprintf(
            '<script src="%s" async defer></script>',
            esc_url($url)
        );
    }

    /**
     * Enqueue Google Maps scripts in WordPress
     *
     * @param array $options Additional options passed to renderApiScript
     */
    public function enqueueScripts(array $options = []): void
    {
        if (!$this->isConfigured()) {
            return;
        }

        $queryArgs = [
            'key' => $this->apiKey,
        ];

        if (!empty($options['libraries'])) {
            $queryArgs['libraries'] = is_array($options['libraries'])
                ? implode(',', $options['libraries'])
                : $options['libraries'];
        }

        wp_enqueue_script(
            'google-maps-api',
            add_query_arg($queryArgs, 'https://maps.googleapis.com/maps/api/js'),
            [],
            null,
            true
        );
    }
}
