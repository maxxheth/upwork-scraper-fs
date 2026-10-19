#!/bin/bash
# Health check script for WordPress container
set -e

# Check if WordPress is installed
if [ ! -f /var/www/html/wp-config.php ]; then
    echo "WordPress not installed yet"
    exit 1
fi

# Check PHP-FPM/Apache is responding
if ! curl -sf http://localhost/ > /dev/null 2>&1; then
    echo "Apache not responding"
    exit 1
fi

# Check MySQL connection
php -r "
    \$mysqli = new mysqli('db', 'wordpress', 'wordpress_secret', 'wordpress');
    if (\$mysqli->connect_error) {
        exit(1);
    }
    echo 'DB OK';
    \$mysqli->close();
" 2>/dev/null || {
    echo "MySQL connection failed"
    exit 1
}

# Check Redis connection
php -r "
    \$redis = new Redis();
    if (!\$redis->connect('redis', 6379)) {
        exit(1);
    }
    echo 'Redis OK';
" 2>/dev/null || {
    echo "Redis connection failed"
    exit 1
}

echo "All health checks passed"
exit 0
