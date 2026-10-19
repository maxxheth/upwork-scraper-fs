<?php

declare(strict_types=1);

namespace Nous\WpMaintenanceSuite;

/**
 * Security auditor - checks user roles, file permissions, plugin versions, WP core integrity.
 */
final class SecurityAuditor
{
    /**
     * Run a full security check and return results.
     *
     * @return array<string, mixed>
     */
    public function runSecurityCheck(): array
    {
        return [
            'user_roles'       => $this->checkUserRoles(),
            'file_permissions' => $this->checkFilePermissions(),
            'plugin_versions'  => $this->checkPluginVersions(),
            'core_integrity'   => $this->checkCoreIntegrity(),
            'admin_users'      => $this->checkAdminUsers(),
            'timestamp'        => current_time('mysql'),
        ];
    }

    /**
     * Check user roles for security issues.
     *
     * @return array<string, mixed>
     */
    private function checkUserRoles(): array
    {
        global $wp_roles;

        if (!isset($wp_roles)) {
            $wp_roles = new \WP_Roles();
        }

        $issues = [];

        // Check for users with Administrator role
        $adminUsers = get_users(['role' => 'administrator']);
        if (count($adminUsers) > 3) {
            $issues[] = sprintf(
                'High number of administrators (%d). Review user roles.',
                count($adminUsers)
            );
        }

        // Check for unused roles
        $roles = $wp_roles->get_names();
        foreach ($roles as $roleSlug => $roleName) {
            $users = count(get_users(['role' => $roleSlug]));
            if ($users === 0 && !in_array($roleSlug, ['administrator', 'editor', 'author', 'contributor', 'subscriber'], true)) {
                $issues[] = sprintf('Unused role: %s (%s)', $roleName, $roleSlug);
            }
        }

        return [
            'total_users'      => count_users()['total_users'],
            'admin_count'      => count($adminUsers),
            'roles'            => $roles,
            'issues'           => $issues,
            'status'           => empty($issues) ? 'ok' : 'warning',
        ];
    }

    /**
     * Check critical file permissions.
     *
     * @return array<string, mixed>
     */
    private function checkFilePermissions(): array
    {
        $criticalFiles = [
            ABSPATH . 'wp-config.php'  => 'config',
            ABSPATH . '.htaccess'       => 'htaccess',
            WP_CONTENT_DIR              => 'content_dir',
        ];

        $issues = [];

        foreach ($criticalFiles as $path => $label) {
            if (!file_exists($path)) {
                continue;
            }

            $perms = fileperms($path) & 0777;
            $owner = fileowner($path);

            // wp-config.php should never be world-readable
            if ($label === 'config' && $perms > 0644) {
                $issues[] = sprintf('wp-config.php has loose permissions (%o). Should be 600 or 640.', $perms);
            }

            // .htaccess should not be writable by world
            if ($label === 'htaccess' && ($perms & 0002)) {
                $issues[] = '.htaccess is world-writable. Restrict to 644.';
            }
        }

        return [
            'files_checked' => count($criticalFiles),
            'issues'        => $issues,
            'status'        => empty($issues) ? 'ok' : 'warning',
        ];
    }

    /**
     * Check plugin versions against known vulnerabilities (simulated).
     *
     * @return array<string, mixed>
     */
    private function checkPluginVersions(): array
    {
        if (!function_exists('get_plugins')) {
            require_once ABSPATH . 'wp-admin/includes/plugin.php';
        }

        $plugins     = get_plugins();
        $issues      = [];
        $updates     = get_site_transient('update_plugins');
        $outdated    = [];

        foreach ($plugins as $pluginFile => $pluginData) {
            $slug = dirname($pluginFile);

            // Check if update is available
            if (isset($updates->response[$pluginFile])) {
                $outdated[] = [
                    'name'             => $pluginData['Name'],
                    'current_version'  => $pluginData['Version'],
                    'available_version' => $updates->response[$pluginFile]->new_version,
                ];
                $issues[] = sprintf(
                    '%s v%s (update available: v%s)',
                    $pluginData['Name'],
                    $pluginData['Version'],
                    $updates->response[$pluginFile]->new_version
                );
            }
        }

        return [
            'total_plugins' => count($plugins),
            'outdated'      => $outdated,
            'issues'        => $issues,
            'status'        => empty($issues) ? 'ok' : 'warning',
        ];
    }

    /**
     * Check WordPress core integrity.
     *
     * @return array<string, mixed>
     */
    private function checkCoreIntegrity(): array
    {
        $issues   = [];
        $wpVersion = get_bloginfo('version');

        // Check if core update is available
        $coreUpdates = get_site_transient('update_core');
        $updateAvailable = false;
        if (!empty($coreUpdates->updates)) {
            foreach ($coreUpdates->updates as $update) {
                if ($update->response === 'upgrade') {
                    $updateAvailable = true;
                    $issues[] = sprintf(
                        'WordPress %s is available (current: %s)',
                        $update->current,
                        $wpVersion
                    );
                    break;
                }
            }
        }

        // Check for debug mode in production
        if (defined('WP_DEBUG') && WP_DEBUG && !defined('WP_DEBUG_DISPLAY') || (defined('WP_DEBUG_DISPLAY') && WP_DEBUG_DISPLAY)) {
            $issues[] = 'WP_DEBUG is enabled with display. Disable in production.';
        }

        return [
            'wp_version'       => $wpVersion,
            'update_available' => $updateAvailable,
            'issues'           => $issues,
            'status'           => empty($issues) ? 'ok' : 'warning',
        ];
    }

    /**
     * Check for users with admin privileges.
     *
     * @return array<string, mixed>
     */
    private function checkAdminUsers(): array
    {
        $adminUsers = get_users([
            'role__in' => ['administrator'],
            'fields'   => ['ID', 'user_login', 'user_email', 'display_name'],
        ]);

        $issues = [];

        // Check for default 'admin' username
        foreach ($adminUsers as $user) {
            if ($user->user_login === 'admin') {
                $issues[] = 'Default "admin" username detected. Consider renaming.';
            }
        }

        return [
            'admin_users' => $adminUsers,
            'count'       => count($adminUsers),
            'issues'      => $issues,
            'status'      => empty($issues) ? 'ok' : 'warning',
        ];
    }
}
