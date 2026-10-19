<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Carbon_Fields\Carbon_Fields;
use App\Fields\ThemeOptions;
use App\Fields\PropertyDetails;
use App\Fields\BusinessInfo;

if (!defined('Carbon_Fields\URL')) {
    define('Carbon_Fields\URL', home_url('/app/vendor/htmlburger/carbon-fields'));
}

class FieldsServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    public function boot(): void
    {
        add_action('after_setup_theme', function () {
            Carbon_Fields::boot();
        });

        add_action('carbon_fields_fields_registered', [$this, 'registerFields']);
    }

    public function registerFields(): void
    {
        ThemeOptions::make();
        PropertyDetails::make();
        BusinessInfo::make();
    }
}
