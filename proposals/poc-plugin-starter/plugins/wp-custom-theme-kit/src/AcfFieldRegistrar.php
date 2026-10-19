<?php

declare(strict_types=1);

namespace Nous\WpCustomThemeKit;

/**
 * Registers ACF field groups programmatically (no UI dependency).
 * Uses ACF's built-in API: acf_add_local_field_group().
 */
final class AcfFieldRegistrar
{
    public function register(): void
    {
        add_action('acf/init', [$this, 'registerPortfolioFields']);
        add_action('acf/init', [$this, 'registerTestimonialFields']);
        add_action('acf/init', [$this, 'registerSiteSettingsFields']);
    }

    public function registerPortfolioFields(): void
    {
        if (!function_exists('acf_add_local_field_group')) {
            return; // ACF not active
        }

        acf_add_local_field_group([
            'key'      => 'group_portfolio_details',
            'title'    => __('Portfolio Details', 'wp-custom-theme-kit'),
            'fields'   => [
                [
                    'key'           => 'field_portfolio_client',
                    'label'         => __('Client Name', 'wp-custom-theme-kit'),
                    'name'          => 'client_name',
                    'type'          => 'text',
                    'instructions'  => __('Name of the client for this project.', 'wp-custom-theme-kit'),
                    'required'      => 1,
                    'placeholder'   => 'e.g., Acme Corp',
                ],
                [
                    'key'           => 'field_portfolio_url',
                    'label'         => __('Project URL', 'wp-custom-theme-kit'),
                    'name'          => 'project_url',
                    'type'          => 'url',
                    'instructions'  => __('URL of the live project.', 'wp-custom-theme-kit'),
                    'placeholder'   => 'https://example.com',
                ],
                [
                    'key'           => 'field_portfolio_date',
                    'label'         => __('Completion Date', 'wp-custom-theme-kit'),
                    'name'          => 'completion_date',
                    'type'          => 'date_picker',
                    'instructions'  => __('When was this project completed?', 'wp-custom-theme-kit'),
                    'required'      => 1,
                    'display_format' => 'F j, Y',
                    'return_format'  => 'Y-m-d',
                ],
                [
                    'key'           => 'field_portfolio_technologies',
                    'label'         => __('Technologies Used', 'wp-custom-theme-kit'),
                    'name'          => 'technologies',
                    'type'          => 'repeater',
                    'instructions'  => __('Technologies and tools used in this project.', 'wp-custom-theme-kit'),
                    'min'           => 1,
                    'layout'        => 'table',
                    'sub_fields'    => [
                        [
                            'key'   => 'field_tech_name',
                            'label' => __('Technology', 'wp-custom-theme-kit'),
                            'name'  => 'technology',
                            'type'  => 'text',
                        ],
                        [
                            'key'   => 'field_tech_version',
                            'label' => __('Version', 'wp-custom-theme-kit'),
                            'name'  => 'version',
                            'type'  => 'text',
                        ],
                    ],
                ],
                [
                    'key'           => 'field_portfolio_gallery',
                    'label'         => __('Project Gallery', 'wp-custom-theme-kit'),
                    'name'          => 'project_gallery',
                    'type'          => 'gallery',
                    'instructions'  => __('Screenshots or images of the project.', 'wp-custom-theme-kit'),
                    'min'           => 1,
                    'max'           => 10,
                    'return_format' => 'array',
                ],
                [
                    'key'           => 'field_portfolio_featured',
                    'label'         => __('Featured Project', 'wp-custom-theme-kit'),
                    'name'          => 'featured_project',
                    'type'          => 'true_false',
                    'instructions'  => __('Show this project in the featured section.', 'wp-custom-theme-kit'),
                    'ui'            => 1,
                    'default_value' => 0,
                ],
            ],
            'location' => [
                [
                    [
                        'param'    => 'post_type',
                        'operator' => '==',
                        'value'    => 'portfolio',
                    ],
                ],
            ],
            'menu_order'            => 0,
            'position'              => 'normal',
            'style'                 => 'default',
            'label_placement'       => 'top',
            'instruction_placement' => 'label',
            'hide_on_screen'        => '',
            'active'               => true,
            'show_in_rest'         => true,
        ]);
    }

    public function registerTestimonialFields(): void
    {
        if (!function_exists('acf_add_local_field_group')) {
            return;
        }

        acf_add_local_field_group([
            'key'      => 'group_testimonial_details',
            'title'    => __('Testimonial Details', 'wp-custom-theme-kit'),
            'fields'   => [
                [
                    'key'           => 'field_testimonial_author',
                    'label'         => __('Author Name', 'wp-custom-theme-kit'),
                    'name'          => 'author_name',
                    'type'          => 'text',
                    'required'      => 1,
                ],
                [
                    'key'           => 'field_testimonial_position',
                    'label'         => __('Position / Title', 'wp-custom-theme-kit'),
                    'name'          => 'author_position',
                    'type'          => 'text',
                ],
                [
                    'key'           => 'field_testimonial_company',
                    'label'         => __('Company', 'wp-custom-theme-kit'),
                    'name'          => 'author_company',
                    'type'          => 'text',
                ],
                [
                    'key'           => 'field_testimonial_rating',
                    'label'         => __('Rating', 'wp-custom-theme-kit'),
                    'name'          => 'rating',
                    'type'          => 'select',
                    'choices'       => [
                        1 => '★',
                        2 => '★★',
                        3 => '★★★',
                        4 => '★★★★',
                        5 => '★★★★★',
                    ],
                    'default_value' => 5,
                    'required'      => 1,
                ],
            ],
            'location' => [
                [
                    [
                        'param'    => 'post_type',
                        'operator' => '==',
                        'value'    => 'testimonial',
                    ],
                ],
            ],
            'active' => true,
        ]);
    }

    public function registerSiteSettingsFields(): void
    {
        if (!function_exists('acf_add_local_field_group')) {
            return;
        }

        acf_add_local_field_group([
            'key'      => 'group_site_settings',
            'title'    => __('Site Settings', 'wp-custom-theme-kit'),
            'fields'   => [
                [
                    'key'           => 'field_site_logo_alt',
                    'label'         => __('Alternate Logo', 'wp-custom-theme-kit'),
                    'name'          => 'alternate_logo',
                    'type'          => 'image',
                    'instructions'  => __('Upload an alternate logo (e.g., for dark mode or footer).', 'wp-custom-theme-kit'),
                    'return_format' => 'array',
                    'preview_size'  => 'medium',
                ],
                [
                    'key'           => 'field_site_contact_email',
                    'label'         => __('Contact Email', 'wp-custom-theme-kit'),
                    'name'          => 'contact_email',
                    'type'          => 'email',
                    'instructions'  => __('Primary contact email address.', 'wp-custom-theme-kit'),
                ],
                [
                    'key'           => 'field_site_social_links',
                    'label'         => __('Social Links', 'wp-custom-theme-kit'),
                    'name'          => 'social_links',
                    'type'          => 'repeater',
                    'layout'        => 'table',
                    'sub_fields'    => [
                        [
                            'key'   => 'field_social_platform',
                            'label' => __('Platform', 'wp-custom-theme-kit'),
                            'name'  => 'platform',
                            'type'  => 'select',
                            'choices' => [
                                'facebook'  => 'Facebook',
                                'twitter'   => 'Twitter / X',
                                'instagram' => 'Instagram',
                                'linkedin'  => 'LinkedIn',
                                'github'    => 'GitHub',
                                'youtube'   => 'YouTube',
                            ],
                        ],
                        [
                            'key'   => 'field_social_url',
                            'label' => __('URL', 'wp-custom-theme-kit'),
                            'name'  => 'url',
                            'type'  => 'url',
                        ],
                    ],
                ],
            ],
            'location' => [
                [
                    [
                        'param'    => 'options_page',
                        'operator' => '==',
                        'value'    => 'acf-options-site-settings',
                    ],
                ],
            ],
            'active' => true,
        ]);

        // Register options page
        if (function_exists('acf_add_options_page')) {
            acf_add_options_page([
                'page_title' => __('Site Settings', 'wp-custom-theme-kit'),
                'menu_title' => __('Site Settings', 'wp-custom-theme-kit'),
                'menu_slug'  => 'acf-options-site-settings',
                'capability' => 'manage_options',
                'redirect'   => false,
                'icon_url'   => 'dashicons-admin-settings',
            ]);
        }
    }
}
