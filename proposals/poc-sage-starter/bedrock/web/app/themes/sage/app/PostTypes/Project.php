<?php

namespace App\PostTypes;

use App\Contracts\PostTypeTemplate;

class Project implements PostTypeTemplate
{
    public function register(): void
    {
        register_post_type('project', [
            'labels' => [
                'name' => __('Projects', 'sage'),
                'singular_name' => __('Project', 'sage'),
                'add_new' => __('Add New', 'sage'),
                'add_new_item' => __('Add New Project', 'sage'),
                'edit_item' => __('Edit Project', 'sage'),
                'new_item' => __('New Project', 'sage'),
                'view_item' => __('View Project', 'sage'),
                'search_items' => __('Search Projects', 'sage'),
                'not_found' => __('No projects found', 'sage'),
                'not_found_in_trash' => __('No projects found in Trash', 'sage'),
            ],
            'public' => true,
            'has_archive' => true,
            'rewrite' => ['slug' => 'projects'],
            'supports' => ['title', 'editor', 'thumbnail', 'excerpt', 'custom-fields'],
            'menu_icon' => 'dashicons-portfolio',
            'show_in_rest' => true,
            'publicly_queryable' => true,
            'show_ui' => true,
            'show_in_menu' => true,
        ]);
    }
}
