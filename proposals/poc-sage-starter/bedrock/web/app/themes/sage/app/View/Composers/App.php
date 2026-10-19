<?php

namespace App\View\Composers;

use Roots\Acorn\View\Composer;

class App extends Composer
{
    /**
     * List of views served by this composer.
     *
     * @var array
     */
    protected static $views = [
        '*',
    ];

    /**
     * Retrieve the site name.
     */
    public function siteName(): string
    {
        return get_bloginfo('name', 'display');
    }

    /**
     * Retrieve the site description.
     */
    public function siteDescription(): string
    {
        return get_bloginfo('description', 'display');
    }

    /**
     * Get primary navigation menu.
     */
    public function primaryNavigation(): array
    {
        if (!has_nav_menu('primary_navigation')) {
            return [];
        }

        $locations = get_nav_menu_locations();
        $menu = wp_get_nav_menu_object($locations['primary_navigation']);

        if (!$menu) {
            return [];
        }

        $menu_items = wp_get_nav_menu_items($menu->term_id);

        return $menu_items ?: [];
    }
}
