<?php

namespace App\Services;

/**
 * Google Maps Integration Service
 *
 * Handles Maps API key management, marker data preparation,
 * and clustering configuration for interactive portfolio maps.
 *
 * @package App\Services
 */
class GoogleMapsService
{
    /**
     * Google Maps API key
     *
     * @var string
     */
    protected string $apiKey;

    /**
     * Default map center coordinates
     *
     * @var array
     */
    protected array $defaultCenter;

    /**
     * Default zoom level
     *
     * @var int
     */
    protected int $defaultZoom;

    public function __construct()
    {
        $this->apiKey = defined('GOOGLE_MAPS_API_KEY')
            ? GOOGLE_MAPS_API_KEY
            : (getenv('GOOGLE_MAPS_API_KEY') ?: '');

        $this->defaultCenter = [
            'lat' => 39.8283,
            'lng' => -98.5795,
        ];

        $this->defaultZoom = 4;
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
    public function hasApiKey(): bool
    {
        return !empty($this->apiKey);
    }

    /**
     * Get default map center
     *
     * @return array
     */
    public function getDefaultCenter(): array
    {
        return $this->defaultCenter;
    }

    /**
     * Get default zoom level
     *
     * @return int
     */
    public function getDefaultZoom(): int
    {
        return $this->defaultZoom;
    }

    /**
     * Prepare markers from a collection of posts with location data
     *
     * @param array $posts Array of WP_Post objects or arrays with lat/lng
     * @return array
     */
    public function prepareMarkers(array $posts): array
    {
        $markers = [];

        foreach ($posts as $post) {
            $lat = get_post_meta($post->ID, 'property_lat', true);
            $lng = get_post_meta($post->ID, 'property_lng', true);

            if (empty($lat) || empty($lng)) {
                continue;
            }

            $markers[] = [
                'id' => $post->ID,
                'title' => get_the_title($post),
                'lat' => (float) $lat,
                'lng' => (float) $lng,
                'permalink' => get_permalink($post),
                'thumbnail' => get_the_post_thumbnail_url($post, 'thumbnail'),
                'price' => get_post_meta($post->ID, 'property_price', true),
                'status' => get_post_meta($post->ID, 'property_status', true),
                'type' => get_post_meta($post->ID, 'property_type', true),
            ];
        }

        return $markers;
    }

    /**
     * Get markers grouped by state for state-level shading
     *
     * @param array $posts
     * @return array
     */
    public function getMarkersByState(array $posts): array
    {
        $byState = [];

        foreach ($posts as $post) {
            $state = get_post_meta($post->ID, 'property_state', true);
            if (empty($state)) {
                continue;
            }

            if (!isset($byState[$state])) {
                $byState[$state] = [
                    'state' => $state,
                    'count' => 0,
                    'markers' => [],
                ];
            }

            $lat = get_post_meta($post->ID, 'property_lat', true);
            $lng = get_post_meta($post->ID, 'property_lng', true);

            if (!empty($lat) && !empty($lng)) {
                $byState[$state]['markers'][] = [
                    'id' => $post->ID,
                    'title' => get_the_title($post),
                    'lat' => (float) $lat,
                    'lng' => (float) $lng,
                    'permalink' => get_permalink($post),
                ];
            }

            $byState[$state]['count']++;
        }

        return array_values($byState);
    }

    /**
     * Get map configuration for JavaScript initialization
     *
     * @param array $markers
     * @param array $options
     * @return array
     */
    public function getMapConfig(array $markers = [], array $options = []): array
    {
        return [
            'apiKey' => $this->apiKey,
            'center' => $options['center'] ?? $this->defaultCenter,
            'zoom' => $options['zoom'] ?? $this->defaultZoom,
            'markers' => $markers,
            'cluster' => $options['cluster'] ?? true,
            'clusterMaxZoom' => $options['clusterMaxZoom'] ?? 12,
            'clusterGridSize' => $options['clusterGridSize'] ?? 50,
            'styles' => $options['styles'] ?? $this->getDefaultMapStyles(),
            'filterPanel' => $options['filterPanel'] ?? true,
        ];
    }

    /**
     * Get default map styles (clean, modern look)
     *
     * @return array
     */
    protected function getDefaultMapStyles(): array
    {
        return [
            [
                'featureType' => 'poi',
                'elementType' => 'labels',
                'stylers' => [['visibility' => 'off']],
            ],
            [
                'featureType' => 'transit',
                'stylers' => [['visibility' => 'off']],
            ],
            [
                'featureType' => 'administrative',
                'elementType' => 'labels.text.fill',
                'stylers' => [['color' => '#444444']],
            ],
            [
                'featureType' => 'landscape',
                'elementType' => 'all',
                'stylers' => [['color' => '#f2f2f2']],
            ],
            [
                'featureType' => 'water',
                'elementType' => 'all',
                'stylers' => [['color' => '#e0e0e0']],
            ],
        ];
    }
}
