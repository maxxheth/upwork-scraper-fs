#!/bin/bash
set -e

# This script runs after WordPress is fully installed
# It activates plugins and sets up demo content

echo "=== WordPress Setup Script ==="

# Wait for WordPress to be ready
sleep 5

# Activate plugins
wp plugin activate wp-css-audit --allow-root 2>/dev/null || echo "wp-css-audit not found or already active"
wp plugin activate wp-custom-theme-kit --allow-root 2>/dev/null || echo "wp-custom-theme-kit not found or already active"
wp plugin activate wp-maintenance-suite --allow-root 2>/dev/null || echo "wp-maintenance-suite not found or already active"

# Activate custom theme
wp theme activate custom-theme --allow-root 2>/dev/null || echo "custom-theme not found"

# Set permalink structure
wp rewrite structure '/%postname%/' --allow-root 2>/dev/null || true
wp rewrite flush --allow-root 2>/dev/null || true

echo "=== Setup Complete ==="
