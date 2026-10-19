<?php
/**
 * ACF Field Group Registrations for Sage Theme
 *
 * This file registers all ACF field groups used by the PoC components.
 * Place in: app/Fields/ or load via theme setup.
 *
 * @package Sage\Fields
 */

namespace App\Fields;

use function Roots\view;

/**
 * Register Property custom post type
 */
add_action('init', function () {
    register_post_type('property', [
        'labels' => [
            'name'          => __('Properties'),
            'singular_name' => __('Property'),
            'add_new_item'  => __('Add New Property'),
            'edit_item'     => __('Edit Property'),
            'view_item'     => __('View Property'),
            'search_items'  => __('Search Properties'),
            'not_found'     => __('No properties found'),
        ],
        'public'       => true,
        'has_archive'  => true,
        'rewrite'      => ['slug' => 'properties'],
        'supports'     => ['title', 'editor', 'thumbnail', 'excerpt', 'custom-fields'],
        'menu_icon'    => 'dashicons-admin-multisite',
        'show_in_rest' => true,
    ]);

    // Register Property Type taxonomy
    register_taxonomy('property_type', 'property', [
        'labels' => [
            'name'          => __('Property Types'),
            'singular_name' => __('Property Type'),
            'add_new_item'  => __('Add New Property Type'),
        ],
        'public'       => true,
        'rewrite'      => ['slug' => 'property-type'],
        'show_in_rest' => true,
        'hierarchical' => true,
    ]);
});

/**
 * Register ACF Field Groups
 * These would normally be imported via ACF JSON sync or local fields.
 * For the PoC, we define them programmatically.
 */
add_action('acf/include_fields', function () {
    // Bail if ACF not active
    if (!function_exists('acf_add_local_field_group')) {
        return;
    }

    /**
     * Field Group: Property Details
     */
    acf_add_local_field_group([
        'key'    => 'group_property_details',
        'title'  => 'Property Details',
        'fields' => [
            [
                'key'   => 'field_property_price',
                'name'  => 'property_price',
                'label' => 'Price ($)',
                'type'  => 'number',
                'required' => 1,
                'min'   => 0,
                'max'   => 999999999,
            ],
            [
                'key'   => 'field_property_bedrooms',
                'name'  => 'property_bedrooms',
                'label' => 'Bedrooms',
                'type'  => 'number',
                'min'   => 0,
                'max'   => 50,
            ],
            [
                'key'   => 'field_property_bathrooms',
                'name'  => 'property_bathrooms',
                'label' => 'Bathrooms',
                'type'  => 'number',
                'min'   => 0,
                'max'   => 50,
            ],
            [
                'key'   => 'field_property_sqft',
                'name'  => 'property_sqft',
                'label' => 'Square Feet',
                'type'  => 'number',
                'min'   => 0,
            ],
            [
                'key'   => 'field_property_lot_size',
                'name'  => 'property_lot_size',
                'label' => 'Lot Size',
                'type'  => 'text',
                'placeholder' => 'e.g., 0.25 acres',
            ],
            [
                'key'   => 'field_property_garage',
                'name'  => 'property_garage',
                'label' => 'Garage Spaces',
                'type'  => 'number',
                'min'   => 0,
                'max'   => 10,
            ],
            [
                'key'   => 'field_property_year_built',
                'name'  => 'property_year_built',
                'label' => 'Year Built',
                'type'  => 'number',
                'min'   => 1800,
                'max'   => 2099,
            ],
            [
                'key'   => 'field_property_status',
                'name'  => 'property_status',
                'label' => 'Status',
                'type'  => 'select',
                'choices' => [
                    'for-sale' => 'For Sale',
                    'pending'  => 'Pending',
                    'sold'     => 'Sold',
                    'for-rent' => 'For Rent',
                ],
                'default_value' => 'for-sale',
                'required' => 1,
            ],
            [
                'key'   => 'field_property_gallery',
                'name'  => 'property_gallery',
                'label' => 'Photo Gallery',
                'type'  => 'gallery',
                'min'   => 0,
                'max'   => 30,
            ],
            [
                'key'   => 'field_property_address',
                'name'  => 'property_address',
                'label' => 'Street Address',
                'type'  => 'text',
            ],
            [
                'key'   => 'field_property_city',
                'name'  => 'property_city',
                'label' => 'City',
                'type'  => 'text',
            ],
            [
                'key'   => 'field_property_state',
                'name'  => 'property_state',
                'label' => 'State',
                'type'  => 'text',
            ],
            [
                'key'   => 'field_property_zip',
                'name'  => 'property_zip',
                'label' => 'ZIP Code',
                'type'  => 'text',
            ],
            [
                'key'   => 'field_property_lat',
                'name'  => 'property_lat',
                'label' => 'Latitude',
                'type'  => 'text',
                'instructions' => 'For Google Maps marker placement',
            ],
            [
                'key'   => 'field_property_lng',
                'name'  => 'property_lng',
                'label' => 'Longitude',
                'type'  => 'text',
                'instructions' => 'For Google Maps marker placement',
            ],
        ],
        'location' => [
            [
                [
                    'param'    => 'post_type',
                    'operator' => '==',
                    'value'    => 'property',
                ],
            ],
        ],
        'position'       => 'acf_after_title',
        'style'          => 'seamless',
        'label_placement' => 'top',
    ]);

    /**
     * Field Group: Landing Page Sections (Flexible Content)
     */
    acf_add_local_field_group([
        'key'    => 'group_landing_page',
        'title'  => 'Page Sections',
        'fields' => [
            [
                'key'   => 'field_page_sections',
                'name'  => 'page_sections',
                'label' => 'Page Sections',
                'type'  => 'flexible_content',
                'layouts' => [
                    'layout_hero' => [
                        'key'        => 'layout_hero',
                        'name'       => 'hero',
                        'label'      => 'Hero Section',
                        'display'    => 'block',
                        'sub_fields' => [
                            [
                                'key'   => 'field_hero_title',
                                'name'  => 'hero_title',
                                'label' => 'Title',
                                'type'  => 'text',
                            ],
                            [
                                'key'   => 'field_hero_subtitle',
                                'name'  => 'hero_subtitle',
                                'label' => 'Subtitle',
                                'type'  => 'textarea',
                            ],
                            [
                                'key'   => 'field_hero_background',
                                'name'  => 'hero_background',
                                'label' => 'Background Image',
                                'type'  => 'image',
                            ],
                            [
                                'key'   => 'field_hero_cta_text',
                                'name'  => 'hero_cta_text',
                                'label' => 'CTA Button Text',
                                'type'  => 'text',
                            ],
                            [
                                'key'   => 'field_hero_cta_url',
                                'name'  => 'hero_cta_url',
                                'label' => 'CTA Button URL',
                                'type'  => 'url',
                            ],
                        ],
                    ],
                    'layout_features' => [
                        'key'        => 'layout_features',
                        'name'       => 'features',
                        'label'      => 'Features Grid',
                        'display'    => 'block',
                        'sub_fields' => [
                            [
                                'key'   => 'field_features_title',
                                'name'  => 'features_title',
                                'label' => 'Section Title',
                                'type'  => 'text',
                            ],
                            [
                                'key'   => 'field_features_items',
                                'name'  => 'features_items',
                                'label' => 'Features',
                                'type'  => 'repeater',
                                'sub_fields' => [
                                    [
                                        'key'   => 'field_feature_icon',
                                        'name'  => 'feature_icon',
                                        'label' => 'Icon',
                                        'type'  => 'image',
                                    ],
                                    [
                                        'key'   => 'field_feature_title',
                                        'name'  => 'feature_title',
                                        'label' => 'Title',
                                        'type'  => 'text',
                                    ],
                                    [
                                        'key'   => 'field_feature_description',
                                        'name'  => 'feature_description',
                                        'label' => 'Description',
                                        'type'  => 'textarea',
                                    ],
                                ],
                            ],
                        ],
                    ],
                    'layout_cta' => [
                        'key'        => 'layout_cta',
                        'name'       => 'cta',
                        'label'      => 'Call to Action',
                        'display'    => 'block',
                        'sub_fields' => [
                            [
                                'key'   => 'field_cta_title',
                                'name'  => 'cta_title',
                                'label' => 'Title',
                                'type'  => 'text',
                            ],
                            [
                                'key'   => 'field_cta_description',
                                'name'  => 'cta_description',
                                'label' => 'Description',
                                'type'  => 'textarea',
                            ],
                            [
                                'key'   => 'field_cta_button_text',
                                'name'  => 'cta_button_text',
                                'label' => 'Button Text',
                                'type'  => 'text',
                            ],
                            [
                                'key'   => 'field_cta_button_url',
                                'name'  => 'cta_button_url',
                                'label' => 'Button URL',
                                'type'  => 'url',
                            ],
                            [
                                'key'   => 'field_cta_background',
                                'name'  => 'cta_background',
                                'label' => 'Background Color',
                                'type'  => 'color_picker',
                            ],
                        ],
                    ],
                ],
                'min' => 0,
                'max' => 20,
            ],
        ],
        'location' => [
            [
                [
                    'param'    => 'post_type',
                    'operator' => '==',
                    'value'    => 'page',
                ],
            ],
        ],
        'position' => 'normal',
        'style'    => 'seamless',
    ]);
});
