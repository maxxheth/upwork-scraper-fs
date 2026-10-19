<?php
/**
 * API Controller for Property Listings
 *
 * Provides REST API endpoints for property data.
 * Used by frontend JavaScript for dynamic filtering and map markers.
 *
 * @package Sage\Http\Controllers\Api
 */

namespace App\Http\Controllers\Api;

use WP_REST_Request;
use WP_REST_Response;
use WP_Query;

class PropertyController
{
    /**
     * Register REST API routes
     */
    public static function registerRoutes(): void
    {
        add_action('rest_api_init', function () {
            // GET /wp-json/sage/v1/properties
            register_rest_route('sage/v1', '/properties', [
                'methods'             => 'GET',
                'callback'            => [self::class, 'getProperties'],
                'permission_callback' => '__return_true',
                'args'                => [
                    'status'    => ['type' => 'string'],
                    'min_price' => ['type' => 'integer'],
                    'max_price' => ['type' => 'integer'],
                    'beds'      => ['type' => 'integer'],
                    'baths'     => ['type' => 'integer'],
                    'type'      => ['type' => 'string'],
                    'search'    => ['type' => 'string'],
                    'page'      => ['type' => 'integer', 'default' => 1],
                    'per_page'  => ['type' => 'integer', 'default' => 12],
                ],
            ]);

            // GET /wp-json/sage/v1/properties/<id>
            register_rest_route('sage/v1', '/properties/(?P<id>\d+)', [
                'methods'             => 'GET',
                'callback'            => [self::class, 'getProperty'],
                'permission_callback' => '__return_true',
                'args'               => [
                    'id' => ['type' => 'integer', 'required' => true],
                ],
            ]);

            // GET /wp-json/sage/v1/properties/nearby
            register_rest_route('sage/v1', '/properties/nearby', [
                'methods'             => 'GET',
                'callback'            => [self::class, 'getNearbyProperties'],
                'permission_callback' => '__return_true',
                'args'               => [
                    'lat'    => ['type' => 'number', 'required' => true],
                    'lng'    => ['type' => 'number', 'required' => true],
                    'radius' => ['type' => 'number', 'default' => 25],
                ],
            ]);
        });
    }

    /**
     * GET /properties — List properties with filters
     */
    public static function getProperties(WP_REST_Request $request): WP_REST_Response
    {
        $args = [
            'post_type'      => 'property',
            'posts_per_page' => $request->get_param('per_page'),
            'paged'          => $request->get_param('page'),
            'meta_key'       => 'property_price',
            'orderby'        => 'meta_value_num',
            'order'          => 'DESC',
        ];

        // Apply filters
        $filters = [
            'status'    => ['key' => 'property_status', 'compare' => '='],
            'min_price' => ['key' => 'property_price', 'compare' => '>=', 'type' => 'NUMERIC'],
            'max_price' => ['key' => 'property_price', 'compare' => '<=', 'type' => 'NUMERIC'],
            'beds'      => ['key' => 'property_bedrooms', 'compare' => '>=', 'type' => 'NUMERIC'],
            'baths'     => ['key' => 'property_bathrooms', 'compare' => '>=', 'type' => 'NUMERIC'],
        ];

        foreach ($filters as $param => $meta) {
            $value = $request->get_param($param);
            if ($value !== null) {
                $args['meta_query'][] = array_merge($meta, ['value' => $value]);
            }
        }

        // Taxonomy filter
        $type = $request->get_param('type');
        if ($type) {
            $args['tax_query'][] = [
                'taxonomy' => 'property_type',
                'field'    => 'slug',
                'terms'    => $type,
            ];
        }

        // Search
        $search = $request->get_param('search');
        if ($search) {
            $args['s'] = $search;
        }

        $query = new WP_Query($args);
        $properties = [];

        while ($query->have_posts()) {
            $query->the_post();
            $properties[] = self::formatProperty(get_post());
        }

        wp_reset_postdata();

        return new WP_REST_Response([
            'properties'   => $properties,
            'total'        => $query->found_posts,
            'total_pages'  => $query->max_num_pages,
            'current_page' => $request->get_param('page'),
        ]);
    }

    /**
     * GET /properties/<id> — Single property
     */
    public static function getProperty(WP_REST_Request $request): WP_REST_Response
    {
        $post = get_post($request->get_param('id'));

        if (!$post || $post->post_type !== 'property') {
            return new WP_REST_Response([
                'error' => 'Property not found.',
            ], 404);
        }

        return new WP_REST_Response([
            'property' => self::formatProperty($post, true),
        ]);
    }

    /**
     * GET /properties/nearby — Properties within radius
     */
    public static function getNearbyProperties(WP_REST_Request $request): WP_REST_Response
    {
        $mapsService = new \App\Services\GoogleMapsService();
        $properties = $mapsService->findPropertiesNearby(
            $request->get_param('lat'),
            $request->get_param('lng'),
            $request->get_param('radius')
        );

        $formatted = array_map(function ($post) {
            return self::formatProperty($post);
        }, $properties);

        return new WP_REST_Response([
            'properties' => $formatted,
            'count'      => count($formatted),
        ]);
    }

    /**
     * Format a property post for API response
     */
    protected static function formatProperty(\WP_Post $post, bool $includeFull = false): array
    {
        $data = [
            'id'        => $post->ID,
            'title'     => get_the_title($post),
            'slug'      => $post->post_name,
            'url'       => get_permalink($post),
            'thumbnail' => get_the_post_thumbnail_url($post->ID, 'large'),
            'excerpt'   => get_the_excerpt($post),
            'price'     => get_field('property_price', $post->ID),
            'bedrooms'  => get_field('property_bedrooms', $post->ID),
            'bathrooms' => get_field('property_bathrooms', $post->ID),
            'sqft'      => get_field('property_sqft', $post->ID),
            'status'    => get_field('property_status', $post->ID),
            'address'   => get_field('property_address', $post->ID),
            'city'      => get_field('property_city', $post->ID),
            'state'     => get_field('property_state', $post->ID),
            'zip'       => get_field('property_zip', $post->ID),
            'lat'       => get_field('property_lat', $post->ID),
            'lng'       => get_field('property_lng', $post->ID),
            'types'     => wp_get_post_terms($post->ID, 'property_type', ['fields' => 'names']),
        ];

        if ($includeFull) {
            $data['content'] = apply_filters('the_content', $post->post_content);
            $data['gallery'] = get_field('property_gallery', $post->ID);
            $data['lot_size'] = get_field('property_lot_size', $post->ID);
            $data['garage'] = get_field('property_garage', $post->ID);
            $data['year_built'] = get_field('property_year_built', $post->ID);
        }

        return $data;
    }
}
