<?php

declare(strict_types=1);

namespace Nous\WpCustomThemeKit;

/**
 * Registers custom post types.
 */
final class PostTypeRegistrar
{
    public function register(): void
    {
        add_action('init', [$this, 'registerPortfolioCpt']);
        add_action('init', [$this, 'registerTestimonialCpt']);
    }

    public function registerPortfolioCpt(): void
    {
        $labels = [
            'name'               => __('Portfolio', 'wp-custom-theme-kit'),
            'singular_name'      => __('Portfolio Item', 'wp-custom-theme-kit'),
            'add_new'            => __('Add New', 'wp-custom-theme-kit'),
            'add_new_item'       => __('Add New Portfolio Item', 'wp-custom-theme-kit'),
            'edit_item'          => __('Edit Portfolio Item', 'wp-custom-theme-kit'),
            'new_item'           => __('New Portfolio Item', 'wp-custom-theme-kit'),
            'view_item'          => __('View Portfolio Item', 'wp-custom-theme-kit'),
            'search_items'       => __('Search Portfolio', 'wp-custom-theme-kit'),
            'not_found'          => __('No portfolio items found', 'wp-custom-theme-kit'),
            'not_found_in_trash' => __('No portfolio items found in Trash', 'wp-custom-theme-kit'),
        ];

        $args = [
            'labels'              => $labels,
            'public'              => true,
            'has_archive'         => true,
            'show_in_rest'        => true,
            'menu_icon'           => 'dashicons-portfolio',
            'supports'            => ['title', 'editor', 'thumbnail', 'excerpt', 'custom-fields'],
            'rewrite'             => ['slug' => 'portfolio'],
            'show_in_graphql'     => true,
            'graphql_single_name' => 'portfolioItem',
            'graphql_plural_name' => 'portfolioItems',
        ];

        register_post_type('portfolio', $args);
    }

    public function registerTestimonialCpt(): void
    {
        $labels = [
            'name'               => __('Testimonials', 'wp-custom-theme-kit'),
            'singular_name'      => __('Testimonial', 'wp-custom-theme-kit'),
            'add_new'            => __('Add New', 'wp-custom-theme-kit'),
            'add_new_item'       => __('Add New Testimonial', 'wp-custom-theme-kit'),
            'edit_item'          => __('Edit Testimonial', 'wp-custom-theme-kit'),
            'new_item'           => __('New Testimonial', 'wp-custom-theme-kit'),
            'view_item'          => __('View Testimonial', 'wp-custom-theme-kit'),
            'search_items'       => __('Search Testimonials', 'wp-custom-theme-kit'),
            'not_found'          => __('No testimonials found', 'wp-custom-theme-kit'),
            'not_found_in_trash' => __('No testimonials found in Trash', 'wp-custom-theme-kit'),
        ];

        $args = [
            'labels'              => $labels,
            'public'              => true,
            'has_archive'         => true,
            'show_in_rest'        => true,
            'menu_icon'           => 'dashicons-testimonial',
            'supports'            => ['title', 'editor', 'thumbnail'],
            'rewrite'             => ['slug' => 'testimonials'],
            'show_in_graphql'     => true,
            'graphql_single_name' => 'testimonial',
            'graphql_plural_name' => 'testimonials',
        ];

        register_post_type('testimonial', $args);
    }
}
