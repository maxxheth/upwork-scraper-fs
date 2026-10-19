<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;

class GutenbergServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    public function boot(): void
    {
        add_action('init', [$this, 'registerGutenbergBlocks']);
        add_action('acf/init', [$this, 'registerAcfBlocks']);
    }

    public function registerGutenbergBlocks(): void
    {
        if (!function_exists('register_block_type')) {
            return;
        }

        // Register custom Gutenberg blocks via ACF
        // Blocks are registered in the ACF UI or via acf_register_block_type
    }

    public function registerAcfBlocks(): void
    {
        if (!function_exists('acf_register_block_type')) {
            return;
        }

        // Property Listing Block
        acf_register_block_type([
            'name' => 'property-listing',
            'title' => __('Property Listing', 'sage'),
            'description' => __('A single property listing card', 'sage'),
            'render_template' => 'resources/views/blocks/property-listing.blade.php',
            'category' => 'sage-blocks',
            'icon' => 'admin-home',
            'keywords' => ['property', 'real estate', 'listing'],
            'mode' => 'edit',
            'supports' => [
                'align' => ['wide', 'full'],
                'jsx' => true,
            ],
        ]);

        // Google Maps Block
        acf_register_block_type([
            'name' => 'google-maps-portfolio',
            'title' => __('Google Maps Portfolio', 'sage'),
            'description' => __('Interactive map with project markers', 'sage'),
            'render_template' => 'resources/views/blocks/google-maps-portfolio.blade.php',
            'category' => 'sage-blocks',
            'icon' => 'location-alt',
            'keywords' => ['map', 'google maps', 'portfolio'],
            'mode' => 'edit',
            'supports' => [
                'align' => ['wide', 'full'],
                'jsx' => true,
            ],
        ]);

        // Landing Page Hero Block
        acf_register_block_type([
            'name' => 'landing-hero',
            'title' => __('Landing Page Hero', 'sage'),
            'description' => __('Hero section for landing pages', 'sage'),
            'render_template' => 'resources/views/blocks/landing-hero.blade.php',
            'category' => 'sage-blocks',
            'icon' => 'welcome-widgets-menus',
            'keywords' => ['hero', 'landing', 'cta'],
            'mode' => 'edit',
            'supports' => [
                'align' => ['full'],
                'jsx' => true,
            ],
        ]);
    }
}
