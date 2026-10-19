<?php

declare(strict_types=1);

namespace Nous\WpCssAudit;

/**
 * Scans theme template files for hard-coded HTML elements.
 */
final class TemplateScanner
{
    private const TEMPLATE_DIRS = [
        'templates',
        'template-parts',
        'blocks',
        'patterns',
    ];

    /**
     * Scan all active theme templates for hard-coded elements.
     *
     * @return array<int, array<string, mixed>>
     */
    public function scan(): array
    {
        $themeDir = get_template_directory();
        $results  = [];

        $files = $this->getTemplateFiles($themeDir);

        foreach ($files as $file) {
            $relativePath = str_replace($themeDir, '', $file);
            $content      = file_get_contents($file);

            if ($content === false) {
                continue;
            }

            $hardcodedElements = $this->findHardcodedElements($content, $relativePath);
            $results           = array_merge($results, $hardcodedElements);
        }

        return $results;
    }

    /**
     * Get all template files from the theme directory.
     *
     * @return array<int, string>
     */
    private function getTemplateFiles(string $themeDir): array
    {
        $files = [];

        // Scan root theme directory for PHP files
        $rootFiles = glob($themeDir . '/*.php');
        if ($rootFiles !== false) {
            $files = $rootFiles;
        }

        // Scan common template subdirectories
        foreach (self::TEMPLATE_DIRS as $dir) {
            $subDir = $themeDir . '/' . $dir;
            if (is_dir($subDir)) {
                $iterator = new \RecursiveIteratorIterator(
                    new \RecursiveDirectoryIterator($subDir, \RecursiveDirectoryIterator::SKIP_DOTS)
                );
                foreach ($iterator as $file) {
                    if ($file->isFile() && $file->getExtension() === 'php') {
                        $files[] = $file->getPathname();
                    }
                }
            }
        }

        return $files;
    }

    /**
     * Find hard-coded HTML elements in template content.
     *
     * @return array<int, array<string, mixed>>
     */
    private function findHardcodedElements(string $content, string $relativePath): array
    {
        $results = [];

        // Pattern 1: Hard-coded text nodes (text outside PHP tags)
        $textPattern = '/>(?<text>[^<]+)</';
        preg_match_all($textPattern, $content, $textMatches, PREG_SET_ORDER);

        foreach ($textMatches as $match) {
            $text = trim($match['text']);
            if (strlen($text) > 3 && !str_starts_with($text, '<?')) {
                $results[] = [
                    'type'     => 'hardcoded_text',
                    'file'     => $relativePath,
                    'content'  => $text,
                    'severity' => 'medium',
                    'note'     => 'This text is hard-coded in the template. To change it via CSS, use content property or visibility.',
                ];
            }
        }

        // Pattern 2: Inline styles
        $stylePattern = '/style\s*=\s*["\'](?<styles>[^"\']+)["\']/i';
        preg_match_all($stylePattern, $content, $styleMatches, PREG_SET_ORDER);

        foreach ($styleMatches as $match) {
            $results[] = [
                'type'     => 'inline_style',
                'file'     => $relativePath,
                'content'  => $match['styles'],
                'severity' => 'high',
                'note'     => 'Inline styles override CSS. Move to stylesheet for CSS-only changes.',
            ];
        }

        // Pattern 3: Hard-coded HTML structure (divs with no dynamic classes)
        $structurePattern = '/<(div|section|article|header|footer|aside|nav|main)\b[^>]*class\s*=\s*["\'](?<classes>[^"\']*?)["\']/i';
        preg_match_all($structurePattern, $content, $structMatches, PREG_SET_ORDER);

        foreach ($structMatches as $match) {
            $classes = trim($match['classes']);
            if (!empty($classes) && !str_contains($classes, '<?')) {
                $results[] = [
                    'type'     => 'structural_element',
                    'file'     => $relativePath,
                    'content'  => sprintf('<%s class="%s">', $match[1], $classes),
                    'severity' => 'low',
                    'note'     => 'Structural element with static classes. Style via CSS class selectors.',
                ];
            }
        }

        return $results;
    }
}
