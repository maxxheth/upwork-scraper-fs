<?php

declare(strict_types=1);

namespace Nous\WpCustomThemeKit;

/**
 * Main plugin class for Custom Theme Kit.
 */
final class Plugin
{
    private static ?Plugin $instance = null;

    private PostTypeRegistrar $postTypeRegistrar;
    private AcfFieldRegistrar $acfFieldRegistrar;
    private FormHandler $formHandler;

    public function __construct()
    {
        $this->postTypeRegistrar = new PostTypeRegistrar();
        $this->acfFieldRegistrar = new AcfFieldRegistrar();
        $this->formHandler       = new FormHandler();
    }

    public function boot(): void
    {
        $this->postTypeRegistrar->register();
        $this->acfFieldRegistrar->register();
        $this->formHandler->register();

        add_action('wp_enqueue_scripts', [$this, 'enqueueFrontendAssets']);
    }

    public function enqueueFrontendAssets(): void
    {
        // Enqueue Tailwind-compiled CSS if it exists
        $cssFile = get_template_directory() . '/dist/css/app.css';
        if (file_exists($cssFile)) {
            wp_enqueue_style(
                'custom-theme-tailwind',
                get_template_directory_uri() . '/dist/css/app.css',
                [],
                filemtime($cssFile)
            );
        }
    }

    public static function getInstance(): self
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
}
