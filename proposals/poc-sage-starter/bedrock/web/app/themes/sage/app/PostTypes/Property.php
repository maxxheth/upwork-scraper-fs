<?php

namespace App\PostTypes;

use App\Contracts\PostTypeTemplate;

class Property implements PostTypeTemplate
{
    public function register(): void
    {
        register_post_type('property', [
            'labels' => [
                'name' => __('Properties', 'sage'),
                'singular_name' => __('Property', 'sage'),
                'add_new' => __('Add New', 'sage'),
                'add_new_item' => __('Add New Property', 'sage'),
                'edit_item' => __('Edit Property', 'sage'),
                'new_item' => __('New Property', 'sage'),
                'view_item' => __('View Property', 'sage'),
                'search_items' => __('Search Properties', 'sage'),
                'not_found' => __('No properties found', 'sage'),
                'not_found_in_trash' => __('No properties found in Trash', 'sage'),
            ],
            'public' => true,
            'has_archive' => true,
            'rewrite' => ['slug' => 'properties'],
            'supports' => ['title', 'editor', 'thumbnail', 'excerpt', 'custom-fields'],
            'menu_icon' => 'dashicons-admin-home',
            'show_in_rest' => true,
            'publicly_queryable' => true,
            'show_ui' => true,
            'show_in_menu' => true,
        ]);
    }
}
