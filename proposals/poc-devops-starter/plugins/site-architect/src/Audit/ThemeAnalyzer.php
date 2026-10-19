<?php

declare(strict_types=1);

namespace Upwork\SiteArchitect\Audit;

class ThemeAnalyzer
{
    /**
     * Analyze the active theme structure
     */
    public function analyze(): \WP_REST_Response
    {
        $theme = wp_get_theme();
        $themeRoot = get_template_directory();

        $result = [
            'name' => $theme->get('Name'),
            'version' => $theme->get('Version'),
            'author' => $theme->get('Author'),
            'description' => $theme->get('Description'),
            'template' => $theme->get('Template'),
            'is_child_theme' => is_child_theme(),
            'text_domain' => $theme->get('TextDomain'),
            'tags' => $theme->get('Tags'),
            'structure' => $this->analyzeStructure($themeRoot),
            'template_hierarchy' => $this->getTemplateHierarchy(),
            'enqueued_assets' => $this->getEnqueuedAssets(),
            'warnings' => [],
            'issues' => [],
        ];

        // Check for common issues
        if ($result['is_child_theme'] && !$result['template']) {
            $result['issues'][] = 'Child theme detected but no parent template defined';
        }

        // Check for required files
        $requiredFiles = ['index.php', 'style.css', 'functions.php'];
        foreach ($requiredFiles as $file) {
            if (!file_exists($themeRoot . '/' . $file)) {
                $result['issues'][] = "Missing required file: {$file}";
            }
        }

        // Check for performance issues
        if (count($result['enqueued_assets']['styles']) > 20) {
            $result['warnings'][] = 'High number of enqueued stylesheets may impact performance';
        }
        if (count($result['enqueued_assets']['scripts']) > 30) {
            $result['warnings'][] = 'High number of enqueued scripts may impact performance';
        }

        return new \WP_REST_Response([
            'success' => true,
            'data' => $result,
        ], 200);
    }

    /**
     * Analyze theme directory structure
     */
    private function analyzeStructure(string $themeRoot): array
    {
        $structure = [
            'template_files' => [],
            'php_files' => 0,
            'css_files' => 0,
            'js_files' => 0,
            'image_files' => 0,
            'total_size' => 0,
            'has_parts_directory' => is_dir($themeRoot . '/parts'),
            'has_templates_directory' => is_dir($themeRoot . '/templates'),
            'has_blocks_directory' => is_dir($themeRoot . '/blocks'),
            'has_languages_directory' => is_dir($themeRoot . '/languages'),
        ];

        $iterator = new \RecursiveIteratorIterator(
            new \RecursiveDirectoryIterator($themeRoot, \RecursiveDirectoryIterator::SKIP_DOTS)
        );

        foreach ($iterator as $file) {
            if ($file->isFile()) {
                $ext = strtolower($file->getExtension());
                $structure['total_size'] += $file->getSize();

                match ($ext) {
                    'php' => $structure['php_files']++,
                    'css' => $structure['css_files']++,
                    'js' => $structure['js_files']++,
                    'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp' => $structure['image_files']++,
                    default => null,
                };

                // Track template files
                if (str_starts_with($file->getFilename(), 'template-') || $file->getFilename() === 'index.php') {
                    $structure['template_files'][] = $file->getFilename();
                }
            }
        }

        $structure['total_size_mb'] = round($structure['total_size'] / 1024 / 1024, 2);
        unset($structure['total_size']);

        return $structure;
    }

    /**
     * Get the WordPress template hierarchy
     */
    private function getTemplateHierarchy(): array
    {
        return [
            'front_page' => get_front_page_template(),
            'home' => get_home_template(),
            'single' => get_single_template(),
            'page' => get_page_template(),
            'archive' => get_archive_template(),
            'search' => get_search_template(),
            '404' => get_404_template(),
        ];
    }

    /**
     * Get all enqueued styles and scripts
     */
    private function getEnqueuedAssets(): array
    {
        global $wp_styles, $wp_scripts;

        $styles = [];
        $scripts = [];

        if (is_admin()) {
            // In admin, we can't easily get frontend enqueues
            return ['styles' => [], 'scripts' => []];
        }

        if (isset($wp_styles->queue)) {
            foreach ($wp_styles->queue as $handle) {
                $style = $wp_styles->registered[$handle] ?? null;
                if ($style) {
                    $styles[] = [
                        'handle' => $handle,
                        'src' => $style->src,
                        'deps' => $style->deps,
                        'ver' => $style->ver,
                    ];
                }
            }
        }

        if (isset($wp_scripts->queue)) {
            foreach ($wp_scripts->queue as $handle) {
                $script = $wp_scripts->registered[$handle] ?? null;
                if ($script) {
                    $scripts[] = [
                        'handle' => $handle,
                        'src' => $script->src,
                        'deps' => $script->deps,
                        'ver' => $script->ver,
                        'in_footer' => $script->extra['group'] ?? 0,
                    ];
                }
            }
        }

        return ['styles' => $styles, 'scripts' => $scripts];
    }
}
