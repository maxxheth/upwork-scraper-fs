<?php
/**
 * Service Provider for View Composers
 *
 * Registers all View Composers with Acorn.
 *
 * @package Sage\Providers
 */

namespace App\Providers;

use Roots\Acorn\ServiceProvider;
use App\View\Composers\PropertyArchive;

class ViewComposerServiceProvider extends ServiceProvider
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
        // Register View Composers
        $this->app->make('view')->composer(
            PropertyArchive::$views,
            PropertyArchive::class
        );
    }
}
