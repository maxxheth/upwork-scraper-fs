<?php

namespace App\Services;

/**
 * Landing Page Service
 *
 * Provides data and configuration for landing page components.
 * Handles CTA optimization, form integration, and A/B test variants.
 *
 * @package App\Services
 */
class LandingPageService
{
    /**
     * Get hero section data
     *
     * @param int $pageId
     * @return array
     */
    public function getHeroData(int $pageId = 0): array
    {
        if (!$pageId) {
            $pageId = get_the_ID();
        }

        return [
            'title' => get_post_meta($pageId, 'hero_title', true) ?: get_the_title($pageId),
            'subtitle' => get_post_meta($pageId, 'hero_subtitle', true),
            'description' => get_post_meta($pageId, 'hero_description', true),
            'cta_text' => get_post_meta($pageId, 'hero_cta_text', true) ?: 'Get Started',
            'cta_url' => get_post_meta($pageId, 'hero_cta_url', true) ?: '#contact',
            'secondary_cta_text' => get_post_meta($pageId, 'hero_secondary_cta_text', true),
            'secondary_cta_url' => get_post_meta($pageId, 'hero_secondary_cta_url', true),
            'background_image' => get_post_meta($pageId, 'hero_background_image', true),
            'background_video' => get_post_meta($pageId, 'hero_background_video', true),
            'overlay_opacity' => get_post_meta($pageId, 'hero_overlay_opacity', true) ?: 0.5,
        ];
    }

    /**
     * Get feature sections for landing page
     *
     * @param int $pageId
     * @return array
     */
    public function getFeatures(int $pageId = 0): array
    {
        if (!$pageId) {
            $pageId = get_the_ID();
        }

        $features = get_post_meta($pageId, 'landing_features', true);
        if (!is_array($features)) {
            return [];
        }

        return array_map(function ($feature) {
            return [
                'icon' => $feature['icon'] ?? 'star',
                'title' => $feature['title'] ?? '',
                'description' => $feature['description'] ?? '',
                'image' => $feature['image'] ?? '',
            ];
        }, $features);
    }

    /**
     * Get conversion tracking configuration
     *
     * @param int $pageId
     * @return array
     */
    public function getConversionConfig(int $pageId = 0): array
    {
        if (!$pageId) {
            $pageId = get_the_ID();
        }

        return [
            'form_id' => get_post_meta($pageId, 'conversion_form_id', true) ?: 'landing-form',
            'thank_you_url' => get_post_meta($pageId, 'thank_you_url', true) ?: '/thank-you',
            'gtag_event' => get_post_meta($pageId, 'gtag_conversion_event', true) ?: 'conversion',
            'gtag_value' => (float) get_post_meta($pageId, 'gtag_conversion_value', true) ?: 0,
        ];
    }

    /**
     * Get SEO metadata for landing page
     *
     * @param int $pageId
     * @return array
     */
    public function getSeoData(int $pageId = 0): array
    {
        if (!$pageId) {
            $pageId = get_the_ID();
        }

        return [
            'title' => get_post_meta($pageId, '_yoast_wpseo_title', true) ?: get_the_title($pageId),
            'description' => get_post_meta($pageId, '_yoast_wpseo_metadesc', true),
            'og_image' => get_the_post_thumbnail_url($pageId, 'full'),
            'schema' => $this->getSchemaMarkup($pageId),
        ];
    }

    /**
     * Generate schema markup for landing page
     *
     * @param int $pageId
     * @return array
     */
    protected function getSchemaMarkup(int $pageId): array
    {
        return [
            '@context' => 'https://schema.org',
            '@type' => 'WebPage',
            'name' => get_the_title($pageId),
            'description' => get_post_meta($pageId, '_yoast_wpseo_metadesc', true),
            'url' => get_permalink($pageId),
            'mainEntity' => [
                '@type' => 'Organization',
                'name' => get_bloginfo('name'),
                'url' => home_url(),
            ],
        ];
    }
}
