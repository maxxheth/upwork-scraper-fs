<?php

namespace App\Fields;

use Carbon_Fields\Container;
use Carbon_Fields\Field;

class PropertyDetails
{
    public static function make()
    {
        Container::make('post_meta', __('Property Details', 'sage'))
            ->where('post_type', '=', 'property')
            ->add_fields([
                Field::make('text', 'property_price', __('Price', 'sage'))
                    ->set_help_text('e.g., $1,200,000'),
                Field::make('text', 'property_bedrooms', __('Bedrooms', 'sage')),
                Field::make('text', 'property_bathrooms', __('Bathrooms', 'sage')),
                Field::make('text', 'property_sqft', __('Square Footage', 'sage')),
                Field::make('text', 'property_lot_size', __('Lot Size', 'sage')),
                Field::make('text', 'property_year_built', __('Year Built', 'sage')),
                Field::make('text', 'property_address', __('Address', 'sage')),
                Field::make('text', 'property_city', __('City', 'sage')),
                Field::make('text', 'property_state', __('State', 'sage')),
                Field::make('text', 'property_zip', __('ZIP Code', 'sage')),
                Field::make('text', 'property_lat', __('Latitude', 'sage')),
                Field::make('text', 'property_lng', __('Longitude', 'sage')),
                Field::make('select', 'property_status', __('Status', 'sage'))
                    ->add_options([
                        'for-sale' => 'For Sale',
                        'for-lease' => 'For Lease',
                        'sold' => 'Sold',
                        'coming-soon' => 'Coming Soon',
                    ]),
                Field::make('select', 'property_type', __('Property Type', 'sage'))
                    ->add_options([
                        'residential' => 'Residential',
                        'commercial' => 'Commercial',
                        'mixed-use' => 'Mixed-Use',
                        'land' => 'Land',
                    ]),
                Field::make('media_gallery', 'property_gallery', __('Photo Gallery', 'sage'))
                    ->set_type(['image']),
                Field::make('image', 'property_featured_image', __('Featured Image', 'sage')),
                Field::make('rich_text', 'property_description', __('Description', 'sage')),
                Field::make('complex', 'property_amenities', __('Amenities', 'sage'))
                    ->add_fields([
                        Field::make('text', 'amenity', __('Amenity', 'sage')),
                    ]),
                Field::make('complex', 'property_features', __('Features', 'sage'))
                    ->add_fields([
                        Field::make('text', 'feature', __('Feature', 'sage')),
                    ]),
                Field::make('text', 'property_agent_name', __('Agent Name', 'sage')),
                Field::make('text', 'property_agent_phone', __('Agent Phone', 'sage')),
                Field::make('text', 'property_agent_email', __('Agent Email', 'sage')),
            ]);
    }
}
