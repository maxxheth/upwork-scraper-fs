<?php

namespace App\Fields;

use Carbon_Fields\Container;
use Carbon_Fields\Field;

class ThemeOptions
{
    public static function make()
    {
        Container::make('theme_options', __('Site Settings', 'sage'))
            ->set_page_parent('themes.php')
            ->add_fields([
                Field::make('text', 'business_name', __('Business Name', 'sage')),
                Field::make('text', 'business_phone', __('Phone Number', 'sage')),
                Field::make('text', 'business_email', __('Email Address', 'sage')),
                Field::make('textarea', 'business_address', __('Address', 'sage')),
                Field::make('image', 'business_logo', __('Logo', 'sage')),
                Field::make('complex', 'social_links', __('Social Links', 'sage'))
                    ->add_fields([
                        Field::make('text', 'platform', __('Platform', 'sage')),
                        Field::make('text', 'url', __('URL', 'sage')),
                    ]),
            ]);
    }
}
