<?php

declare(strict_types=1);

namespace Nous\WpCssAudit;

/**
 * Admin page for the CSS Audit tool.
 */
final class AdminPage
{
    public function __construct(
        private readonly TemplateScanner $scanner,
        private readonly CssEditor $cssEditor,
    ) {
    }

    public function register(): void
    {
        add_action('admin_menu', [$this, 'addAdminMenu']);
    }

    public function addAdminMenu(): void
    {
        add_menu_page(
            __('CSS Audit Tool', 'wp-css-audit'),
            __('CSS Audit', 'wp-css-audit'),
            'manage_options',
            'wp-css-audit',
            [$this, 'renderPage'],
            'dashicons-visibility',
            80
        );
    }

    public function renderPage(): void
    {
        if (!current_user_can('manage_options')) {
            wp_die('Unauthorized');
        }

        $scanResults = $this->scanner->scan();
        $customCss   = $this->cssEditor->getCustomCss();

        ?>
        <div class="wrap wp-css-audit-wrap">
            <h1><?php echo esc_html__('CSS Audit Tool', 'wp-css-audit'); ?></h1>

            <div class="wp-css-audit-tabs">
                <nav class="nav-tab-wrapper">
                    <a href="#tab-scan" class="nav-tab nav-tab-active" data-tab="scan">
                        <?php esc_html_e('Template Scan', 'wp-css-audit'); ?>
                    </a>
                    <a href="#tab-editor" class="nav-tab" data-tab="editor">
                        <?php esc_html_e('Live CSS Editor', 'wp-css-audit'); ?>
                    </a>
                    <a href="#tab-report" class="nav-tab" data-tab="report">
                        <?php esc_html_e('Audit Report', 'wp-css-audit'); ?>
                    </a>
                </nav>

                <div id="tab-scan" class="tab-content active">
                    <h2><?php esc_html_e('Template Scan Results', 'wp-css-audit'); ?></h2>
                    <p><?php esc_html_e('The following hard-coded elements were found in your active theme templates:', 'wp-css-audit'); ?></p>

                    <?php if (empty($scanResults)): ?>
                        <div class="notice notice-success">
                            <p><?php esc_html_e('No hard-coded elements found! Your theme is well-structured.', 'wp-css-audit'); ?></p>
                        </div>
                    <?php else: ?>
                        <table class="wp-list-table widefat fixed striped">
                            <thead>
                                <tr>
                                    <th><?php esc_html_e('Type', 'wp-css-audit'); ?></th>
                                    <th><?php esc_html_e('File', 'wp-css-audit'); ?></th>
                                    <th><?php esc_html_e('Content', 'wp-css-audit'); ?></th>
                                    <th><?php esc_html_e('Severity', 'wp-css-audit'); ?></th>
                                    <th><?php esc_html_e('Note', 'wp-css-audit'); ?></th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($scanResults as $result): ?>
                                    <tr>
                                        <td>
                                            <span class="result-type result-type-<?php echo esc_attr($result['type']); ?>">
                                                <?php echo esc_html(ucwords(str_replace('_', ' ', $result['type']))); ?>
                                            </span>
                                        </td>
                                        <td><code><?php echo esc_html($result['file']); ?></code></td>
                                        <td><code><?php echo esc_html(substr($result['content'], 0, 80)); ?></code></td>
                                        <td>
                                            <span class="severity-badge severity-<?php echo esc_attr($result['severity']); ?>">
                                                <?php echo esc_html(ucfirst($result['severity'])); ?>
                                            </span>
                                        </td>
                                        <td><?php echo esc_html($result['note']); ?></td>
                                    </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>

                        <p class="description">
                            <?php esc_html_e('Total hard-coded elements found: ', 'wp-css-audit'); ?>
                            <strong><?php echo count($scanResults); ?></strong>
                        </p>
                    <?php endif; ?>

                    <button type="button" class="button button-secondary" id="rescan-templates">
                        <?php esc_html_e('Rescan Templates', 'wp-css-audit'); ?>
                    </button>
                </div>

                <div id="tab-editor" class="tab-content">
                    <h2><?php esc_html_e('Live CSS Editor', 'wp-css-audit'); ?></h2>
                    <p><?php esc_html_e('Write CSS below to test changes on your site. Changes are applied in real-time to the frontend.', 'wp-css-audit'); ?></p>

                    <form id="wp-css-audit-editor-form">
                        <textarea id="wp-css-audit-css-editor" name="css" rows="20" class="large-text code"><?php echo esc_textarea($customCss); ?></textarea>

                        <p class="submit">
                            <button type="submit" class="button button-primary" id="save-css">
                                <?php esc_html_e('Save CSS', 'wp-css-audit'); ?>
                            </button>
                            <button type="button" class="button button-secondary" id="preview-css">
                                <?php esc_html_e('Preview on Frontend', 'wp-css-audit'); ?>
                            </button>
                        </p>
                    </form>

                    <div id="css-editor-feedback" class="notice" style="display:none;"></div>
                </div>

                <div id="tab-report" class="tab-content">
                    <h2><?php esc_html_e('Audit Report', 'wp-css-audit'); ?></h2>
                    <p><?php esc_html_e('Generate a downloadable audit report of all findings.', 'wp-css-audit'); ?></p>

                    <div class="audit-summary">
                        <h3><?php esc_html_e('Summary', 'wp-css-audit'); ?></h3>
                        <ul>
                            <li>
                                <strong><?php esc_html_e('Theme:', 'wp-css-audit'); ?></strong>
                                <?php echo esc_html(wp_get_theme()->get('Name')); ?>
                            </li>
                            <li>
                                <strong><?php esc_html_e('Templates Scanned:', 'wp-css-audit'); ?></strong>
                                <?php echo count($scanResults); ?> issues found
                            </li>
                            <li>
                                <strong><?php esc_html_e('CSS-Only Changes Possible:', 'wp-css-audit'); ?></strong>
                                <?php
                                $cssOnly = array_filter($scanResults, fn($r) => $r['severity'] !== 'high');
                                echo count($cssOnly);
                                ?>
                            </li>
                        </ul>
                    </div>

                    <button type="button" class="button button-primary" id="download-report">
                        <?php esc_html_e('Download Report (CSV)', 'wp-css-audit'); ?>
                    </button>
                </div>
            </div>
        </div>

        <style>
            .wp-css-audit-wrap .tab-content { display: none; padding: 20px 0; }
            .wp-css-audit-wrap .tab-content.active { display: block; }
            .severity-badge { padding: 2px 8px; border-radius: 3px; font-size: 11px; text-transform: uppercase; }
            .severity-high { background: #f55; color: #fff; }
            .severity-medium { background: #f90; color: #fff; }
            .severity-low { background: #5b9; color: #fff; }
            .result-type { font-size: 12px; }
            .audit-summary { background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0; }
            .audit-summary ul { margin: 10px 0; }
            .audit-summary li { margin: 5px 0; }
        </style>

        <script>
        jQuery(document).ready(function($) {
            // Tab switching
            $('.nav-tab').on('click', function(e) {
                e.preventDefault();
                $('.nav-tab').removeClass('nav-tab-active');
                $(this).addClass('nav-tab-active');
                $('.tab-content').removeClass('active');
                $($(this).attr('href')).addClass('active');
            });

            // Save CSS
            $('#wp-css-audit-editor-form').on('submit', function(e) {
                e.preventDefault();
                var css = $('#wp-css-audit-css-editor').val();
                $.post(wpCssAudit.ajaxUrl, {
                    action: 'wp_css_audit_save_css',
                    css: css,
                    nonce: wpCssAudit.nonce
                }, function(response) {
                    if (response.success) {
                        $('#css-editor-feedback').removeClass('notice-error').addClass('notice-success')
                            .html('<p>' + response.data.message + '</p>').show();
                    }
                });
            });

            // Preview CSS
            $('#preview-css').on('click', function() {
                var css = $('#wp-css-audit-css-editor').val();
                $.post(wpCssAudit.ajaxUrl, {
                    action: 'wp_css_audit_preview_css',
                    css: css,
                    nonce: wpCssAudit.nonce
                }, function(response) {
                    if (response.success) {
                        $('#css-editor-feedback').removeClass('notice-error').addClass('notice-success')
                            .html('<p>' + response.data.message + ' <a href="<?php echo esc_url(home_url()); ?>" target="_blank">View site</a></p>').show();
                    }
                });
            });

            // Download report
            $('#download-report').on('click', function() {
                var csv = 'Type,File,Content,Severity,Note\n';
                $('.wp-list-table tbody tr').each(function() {
                    var cols = $(this).find('td');
                    csv += '"' + $(cols[0]).text().trim() + '",';
                    csv += '"' + $(cols[1]).text().trim() + '",';
                    csv += '"' + $(cols[2]).text().trim() + '",';
                    csv += '"' + $(cols[3]).text().trim() + '",';
                    csv += '"' + $(cols[4]).text().trim() + '"\n';
                });
                var blob = new Blob([csv], { type: 'text/csv' });
                var link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = 'css-audit-report.csv';
                link.click();
            });
        });
        </script>
        <?php
    }
}
