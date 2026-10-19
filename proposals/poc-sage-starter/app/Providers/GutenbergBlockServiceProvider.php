<?php
/**
 * ACF Gutenberg Block Registration
 *
 * Registers custom Gutenberg blocks using ACF.
 * Blocks are rendered with Sage Blade templates.
 *
 * @package Sage\Providers
 */

namespace App\Providers;

use App\Services\GoogleMapsService;
use Roots\Acorn\ServiceProvider;

class GutenbergBlockServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        add_action('acf/init', [$this, 'registerBlocks']);
        add_filter('block_categories_all', [$this, 'registerBlockCategory'], 10, 2);
    }

    /**
     * Register a custom block category
     */
    public function registerBlockCategory(array $categories, \WP_Post $post): array
    {
        return array_merge([
            [
                'slug'  => 'sage-blocks',
                'title' => __('Sage Blocks', 'sage'),
                'icon'  => 'layout',
            ],
        ], $categories);
    }

    /**
     * Register ACF Gutenberg blocks
     */
    public function registerBlocks(): void
    {
        if (!function_exists('acf_register_block_type')) {
            return;
        }

        // Property Listing Map Block
        acf_register_block_type([
            'name'            => 'property-listing-map',
            'title'           => __('Property Listing Map'),
            'description'     => __('Interactive Google Map with property markers and search.'),
            'render_callback' => [$this, 'renderPropertyListingMap'],
            'category'        => 'sage-blocks',
            'icon'            => 'location-alt',
            'keywords'        => ['map', 'property', 'real estate', 'location'],
            'post_types'      => ['page'],
            'mode'            => 'edit',
            'supports'        => [
                'align'  => ['wide', 'full'],
                'anchor' => true,
            ],
        ]);

        // Testimonial Carousel Block
        acf_register_block_type([
            'name'            => 'testimonial-carousel',
            'title'           => __('Testimonial Carousel'),
            'description'     => __('A carousel of client testimonials.'),
            'render_callback' => [$this, 'renderTestimonialCarousel'],
            'category'        => 'sage-blocks',
            'icon'            => 'testimonial',
            'keywords'        => ['testimonial', 'review', 'carousel', 'slider'],
            'post_types'      => ['page'],
            'mode'            => 'preview',
            'supports'        => [
                'align'  => ['wide', 'full'],
                'anchor' => true,
            ],
        ]);

        // Hero Block
        acf_register_block_type([
            'name'            => 'hero-section',
            'title'           => __('Hero Section'),
            'description'     => __('Full-width hero section with background, title, and CTA.'),
            'render_callback' => [$this, 'renderHeroSection'],
            'category'        => 'sage-blocks',
            'icon'            => 'welcome-widgets-menus',
            'keywords'        => ['hero', 'banner', 'header', 'cta'],
            'post_types'      => ['page'],
            'mode'            => 'preview',
            'supports'        => [
                'align'  => ['full'],
                'anchor' => true,
            ],
        ]);
    }

    /**
     * Render the Property Listing Map block
     */
    public function renderPropertyListingMap(array $block, string $content = '', bool $isPreview = false, int $postId = 0): void
    {
        // Enqueue Google Maps scripts
        $mapsService = new GoogleMapsService();
        $mapsService->enqueueScripts(['libraries' => 'places']);

        // Render the Blade component
        echo \Roots\view('components.property-listing-map', [
            'block'      => $block,
            'is_preview' => $isPreview,
        ])->render();
    }

    /**
     * Render the Testimonial Carousel block
     */
    public function renderTestimonialCarousel(array $block, string $content = '', bool $isPreview = false, int $postId = 0): void
    {
        $testimonials = get_field('testimonials') ?: [];

        echo \Roots\view('components.testimonial-carousel', [
            'block'        => $block,
            'testimonials' => $testimonials,
            'is_preview'   => $isPreview,
        ])->render();
    }

    /**
     * Render the Hero Section block
     */
    public function renderHeroSection(array $block, string $content = '', bool $isPreview = false, int $postId = 0): void
    {
        echo \Roots\view('components.hero', [
            'block'             => $block,
            'title'             => get_field('hero_title'),
            'subtitle'          => get_field('hero_subtitle'),
            'background_image'  => wp_get_attachment_image_url(get_field('hero_background'), 'full'),
            'cta_text'          => get_field('hero_cta_text'),
            'cta_url'           => get_field('hero_cta_url'),
            'overlay_opacity'   => get_field('hero_overlay_opacity') ?: 0.5,
            'is_preview'        => $isPreview,
        ])->render();
    }
}
