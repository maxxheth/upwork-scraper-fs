<?php

namespace App\Services;

/**
 * Property Search Service
 *
 * Handles property listing queries, filtering, and search functionality.
 * Supports status, type, price range, and location filters.
 *
 * @package App\Services
 */
class PropertySearchService
{
    /**
     * Search properties with filters
     *
     * @param array $filters
     * @param int $perPage
     * @return \WP_Query
     */
    public function search(array $filters = [], int $perPage = 12): \WP_Query
    {
        $args = [
            'post_type' => 'property',
            'posts_per_page' => $perPage,
            'paged' => get_query_var('paged', 1),
            'meta_query' => [],
            'tax_query' => [],
        ];

        // Status filter
        if (!empty($filters['status'])) {
            $args['meta_query'][] = [
                'key' => 'property_status',
                'value' => $filters['status'],
                'compare' => '=',
            ];
        }

        // Property type filter
        if (!empty($filters['type'])) {
            $args['meta_query'][] = [
                'key' => 'property_type',
                'value' => $filters['type'],
                'compare' => '=',
            ];
        }

        // Price range filter
        if (!empty($filters['min_price'])) {
            $args['meta_query'][] = [
                'key' => 'property_price',
                'value' => $this->normalizePrice($filters['min_price']),
                'type' => 'DECIMAL',
                'compare' => '>=',
            ];
        }

        if (!empty($filters['max_price'])) {
            $args['meta_query'][] = [
                'key' => 'property_price',
                'value' => $this->normalizePrice($filters['max_price']),
                'type' => 'DECIMAL',
                'compare' => '<=',
            ];
        }

        // Bedrooms filter
        if (!empty($filters['bedrooms'])) {
            $args['meta_query'][] = [
                'key' => 'property_bedrooms',
                'value' => (int) $filters['bedrooms'],
                'type' => 'NUMERIC',
                'compare' => '>=',
            ];
        }

        // Location search (city or state)
        if (!empty($filters['location'])) {
            $meta_query = [
                'relation' => 'OR',
                [
                    'key' => 'property_city',
                    'value' => $filters['location'],
                    'compare' => 'LIKE',
                ],
                [
                    'key' => 'property_state',
                    'value' => $filters['location'],
                    'compare' => 'LIKE',
                ],
                [
                    'key' => 'property_address',
                    'value' => $filters['location'],
                    'compare' => 'LIKE',
                ],
            ];
            $args['meta_query'][] = $meta_query;
        }

        // Keyword search
        if (!empty($filters['keyword'])) {
            $args['s'] = sanitize_text_field($filters['keyword']);
        }

        // Sort
        $args['orderby'] = $filters['orderby'] ?? 'date';
        $args['order'] = $filters['order'] ?? 'DESC';

        return new \WP_Query($args);
    }

    /**
     * Get available filter options
     *
     * @return array
     */
    public function getFilterOptions(): array
    {
        return [
            'statuses' => [
                'for-sale' => __('For Sale', 'sage'),
                'for-lease' => __('For Lease', 'sage'),
                'sold' => __('Sold', 'sage'),
                'coming-soon' => __('Coming Soon', 'sage'),
            ],
            'types' => [
                'residential' => __('Residential', 'sage'),
                'commercial' => __('Commercial', 'sage'),
                'mixed-use' => __('Mixed-Use', 'sage'),
                'land' => __('Land', 'sage'),
            ],
            'bedrooms' => [1, 2, 3, 4, 5],
            'price_ranges' => [
                ['min' => 0, 'max' => 250000, 'label' => 'Under $250K'],
                ['min' => 250000, 'max' => 500000, 'label' => '$250K - $500K'],
                ['min' => 500000, 'max' => 1000000, 'label' => '$500K - $1M'],
                ['min' => 1000000, 'max' => 2000000, 'label' => '$1M - $2M'],
                ['min' => 2000000, 'max' => 5000000, 'label' => '$2M - $5M'],
                ['min' => 5000000, 'max' => null, 'label' => '$5M+'],
            ],
        ];
    }

    /**
     * Normalize price string to numeric value
     *
     * @param string $price
     * @return float
     */
    protected function normalizePrice(string $price): float
    {
        return (float) preg_replace('/[^0-9.]/', '', $price);
    }
}
