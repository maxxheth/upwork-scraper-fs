#!/bin/bash
set -e

# Wait for database
echo "Waiting for database..."
until mysql -h "$WORDPRESS_DB_HOST" -u "$WORDPRESS_DB_USER" -p"$WORDPRESS_DB_PASSWORD" "$WORDPRESS_DB_NAME" -e "SELECT 1" &>/dev/null; do
    sleep 2
done
echo "Database is ready."

# Run WordPress docker entrypoint (handles wp-config, etc.)
# Then run our custom setup
exec /usr/local/bin/docker-entrypoint.sh "$@"
