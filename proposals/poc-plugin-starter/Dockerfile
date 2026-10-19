FROM wordpress:6.7-php8.2-apache

# Install required PHP extensions and tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    unzip \
    libzip-dev \
    && docker-php-ext-install zip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Composer
COPY --from=composer:2 /usr/bin/composer /usr/local/bin/composer

# Install WP-CLI
RUN curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
    && chmod +x wp-cli.phar \
    && mv wp-cli.phar /usr/local/bin/wp

# Enable Apache mod_rewrite
RUN a2enmod rewrite

# Copy the WordPress setup script
COPY docker-setup.sh /usr/local/bin/docker-setup.sh
RUN chmod +x /usr/local/bin/docker-setup.sh

# Copy custom php.ini for development
RUN echo "memory_limit = 256M" > /usr/local/etc/php/conf.d/memory.ini \
    && echo "upload_max_filesize = 64M" >> /usr/local/etc/php/conf.d/upload.ini \
    && echo "post_max_size = 64M" >> /usr/local/etc/php/conf.d/upload.ini \
    && echo "max_execution_time = 300" >> /usr/local/etc/php/conf.d/timeout.ini

# Entry point: run setup then Apache
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint-custom.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-custom.sh

ENTRYPOINT ["docker-entrypoint-custom.sh"]
CMD ["apache2-foreground"]
