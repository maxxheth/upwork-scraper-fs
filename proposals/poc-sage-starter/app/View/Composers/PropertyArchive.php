<?php
/**
 * View Composer for Property Archive
 *
 * Injects data into the property archive template.
 * Registered in app/Providers/ViewComposerServiceProvider.php
 *
 * @package Sage\View\Composers
 */

namespace App\View\Composers;

use Roots\Acorn\View\Composer;

class PropertyArchive extends Composer
{
    /**
     * List of views served by this composer.
     *
     * @var string[]
     */
    protected static $views = [
        'template-property-archive',
        'partials.property-loop',
    ];

    /**
     * Data to be passed to view.
     *
     * @return array
     */
    public function with()
    {
        return [
            'properties' => $this->getProperties(),
            'filters'    => $this->getFilters(),
            'stats'      => $this->getStats(),
        ];
    }

    /**
     * Query properties with optional filters
     *
     * @return \WP_Query
     */
    protected function getProperties(): \WP_Query
    {
        $paged = get_query_var('paged') ?: 1;
        $args = [
            'post_type'      => 'property',
            'posts_per_page' => 12,
            'paged'          => $paged,
            'meta_key'       => 'property_price',
            'orderby'        => 'meta_value_num',
            'order'          => 'DESC',
        ];

        // Apply filters from URL params
        $filters = ['status', 'min_price', 'max_price', 'beds', 'baths', 'property_type'];
        foreach ($filters as $filter) {
            $value = $_GET[$filter] ?? null;
            if ($value) {
                switch ($filter) {
                    case 'status':
                        $args['meta_query'][] = [
                            'key'   => 'property_status',
                            'value' => sanitize_text_field($value),
                        ];
                        break;
                    case 'min_price':
                        $args['meta_query'][] = [
                            'key'     => 'property_price',
                            'value'   => intval($value),
                            'type'    => 'NUMERIC',
                            'compare' => '>=',
                        ];
                        break;
                    case 'max_price':
                        $args['meta_query'][] = [
                            'key'     => 'property_price',
                            'value'   => intval($value),
                            'type'    => 'NUMERIC',
                            'compare' => '<=',
                        ];
                        break;
                    case 'beds':
                        $args['meta_query'][] = [
                            'key'     => 'property_bedrooms',
                            'value'   => intval($value),
                            'type'    => 'NUMERIC',
                            'compare' => '>=',
                        ];
                        break;
                    case 'baths':
                        $args['meta_query'][] = [
                            'key'     => 'property_bathrooms',
                            'value'   => intval($value),
                            'type'    => 'NUMERIC',
                            'compare' => '>=',
                        ];
                        break;
                    case 'property_type':
                        $args['tax_query'][] = [
                            'taxonomy' => 'property_type',
                            'field'    => 'slug',
                            'terms'    => sanitize_text_field($value),
                        ];
                        break;
                }
            }
        }

        return new \WP_Query($args);
    }

    /**
     * Get available filter options
     *
     * @return array
     */
    protected function getFilters(): array
    {
        return [
            'statuses' => [
                'for-sale' => 'For Sale',
                'pending'  => 'Pending',
                'sold'     => 'Sold',
                'for-rent' => 'For Rent',
            ],
            'types' => get_terms([
                'taxonomy'   => 'property_type',
                'hide_empty' => true,
            ]),
            'price_ranges' => [
                ['min' => 0,       'max' => 100000,   'label' => 'Under $100K'],
                ['min' => 100000,  'max' => 250000,   'label' => '$100K - $250K'],
                ['min' => 250000,  'max' => 500000,   'label' => '$250K - $500K'],
                ['min' => 500000,  'max' => 1000000,  'label' => '$500K - $1M'],
                ['min' => 1000000, 'max' => 999999999,'label' => '$1M+'],
            ],
        ];
    }

    /**
     * Get aggregate stats for the property listing
     *
     * @return array
     */
    protected function getStats(): array
    {
        global $wpdb;

        $stats = $wpdb->get_row("
            SELECT
                COUNT(*) as total,
                AVG(CAST(pm_price.meta_value AS DECIMAL(12,2))) as avg_price,
                AVG(CAST(pm_beds.meta_value AS UNSIGNED)) as avg_beds,
                AVG(CAST(pm_baths.meta_value AS UNSIGNED)) as avg_baths
            FROM {$wpdb->posts} p
            LEFT JOIN {$wpdb->postmeta} pm_price
                ON p.ID = pm_price.post_id AND pm_price.meta_key = 'property_price'
            LEFT JOIN {$wpdb->postmeta} pm_beds
                ON p.ID = pm_beds.post_id AND pm_beds.meta_key = 'property_bedrooms'
            LEFT JOIN {$wpdb->postmeta} pm_baths
                ON p.ID = pm_baths.post_id AND pm_baths.meta_key = 'property_bathrooms'
            WHERE p.post_type = 'property'
                AND p.post_status = 'publish'
        ");

        return [
            'total'    => (int) ($stats->total ?? 0),
            'avg_price' => round($stats->avg_price ?? 0),
            'avg_beds'  => round($stats->avg_beds ?? 0),
            'avg_baths' => round($stats->avg_baths ?? 0),
        ];
    }
}
