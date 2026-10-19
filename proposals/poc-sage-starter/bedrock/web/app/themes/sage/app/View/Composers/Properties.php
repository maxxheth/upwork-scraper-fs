<?php

namespace App\View\Composers;

use Roots\Acorn\View\Composer;

class Properties extends Composer
{
    /**
     * List of views served by this composer.
     *
     * @var array
     */
    protected static $views = [
        'template-properties',
        'partials.property-card',
    ];

    /**
     * Get all properties with their meta data.
     */
    public function properties(): array
    {
        $query = new \WP_Query([
            'post_type' => 'property',
            'posts_per_page' => 12,
            'paged' => get_query_var('paged', 1),
        ]);

        return array_map(function ($post) {
            return $this->enrichProperty($post);
        }, $query->posts ?: []);
    }

    /**
     * Enrich a property post with its meta fields.
     */
    protected function enrichProperty($post): array
    {
        return [
            'id' => $post->ID,
            'title' => get_the_title($post),
            'permalink' => get_permalink($post),
            'thumbnail' => get_the_post_thumbnail_url($post->ID, 'medium_large'),
            'price' => get_post_meta($post->ID, 'property_price', true),
            'bedrooms' => get_post_meta($post->ID, 'property_bedrooms', true),
            'bathrooms' => get_post_meta($post->ID, 'property_bathrooms', true),
            'sqft' => get_post_meta($post->ID, 'property_sqft', true),
            'address' => get_post_meta($post->ID, 'property_address', true),
            'city' => get_post_meta($post->ID, 'property_city', true),
            'state' => get_post_meta($post->ID, 'property_state', true),
            'status' => get_post_meta($post->ID, 'property_status', true),
            'type' => get_post_meta($post->ID, 'property_type', true),
            'description' => get_post_meta($post->ID, 'property_description', true),
            'amenities' => get_post_meta($post->ID, 'property_amenities', true) ?: [],
            'features' => get_post_meta($post->ID, 'property_features', true) ?: [],
        ];
    }
}
