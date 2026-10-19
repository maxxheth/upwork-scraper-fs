<?php

namespace App\Fields;

use Carbon_Fields\Container;
use Carbon_Fields\Field;

class BusinessInfo
{
    public static function make()
    {
        Container::make('post_meta', __('Business Information', 'sage'))
            ->where('post_type', '=', 'page')
            ->add_fields([
                Field::make('text', 'page_subtitle', __('Page Subtitle', 'sage')),
                Field::make('image', 'page_hero_image', __('Hero Image', 'sage')),
                Field::make('text', 'page_cta_text', __('CTA Button Text', 'sage')),
                Field::make('text', 'page_cta_url', __('CTA Button URL', 'sage')),
                Field::make('complex', 'page_services', __('Services', 'sage'))
                    ->add_fields([
                        Field::make('text', 'service_title', __('Service Title', 'sage')),
                        Field::make('textarea', 'service_description', __('Service Description', 'sage')),
                        Field::make('image', 'service_icon', __('Service Icon', 'sage')),
                    ]),
                Field::make('complex', 'page_testimonials', __('Testimonials', 'sage'))
                    ->add_fields([
                        Field::make('textarea', 'testimonial_text', __('Testimonial', 'sage')),
                        Field::make('text', 'testimonial_author', __('Author', 'sage')),
                        Field::make('text', 'testimonial_position', __('Position', 'sage')),
                    ]),
            ]);
    }
}
