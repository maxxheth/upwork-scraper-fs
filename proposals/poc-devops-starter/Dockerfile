FROM wordpress:6.7-php8.2-apache

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    unzip \
    libzip-dev \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libxml2-dev \
    libonig-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install PHP extensions
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) \
        gd \
        zip \
        pdo \
        pdo_mysql \
        mysqli \
        bcmath \
        exif \
        opcache \
        soap \
        intl

# Install Redis extension
RUN pecl install redis-6.0.2 && docker-php-ext-enable redis

# Enable Apache modules
RUN a2enmod rewrite headers expires deflate brotli

# Install Composer
COPY --from=composer:2.7 /usr/bin/composer /usr/local/bin/composer

# Install Node.js + NPM for frontend builds
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# PHP opcache config for performance
RUN { \
    echo 'opcache.memory_consumption=256'; \
    echo 'opcache.interned_strings_buffer=16'; \
    echo 'opcache.max_accelerated_files=10000'; \
    echo 'opcache.revalidate_freq=2'; \
    echo 'opcache.fast_shutdown=1'; \
    echo 'opcache.enable_cli=1'; \
    echo 'opcache.jit=1255'; \
    echo 'opcache.jit_buffer_size=100M'; \
} > /usr/local/etc/php/conf.d/opcache-custom.ini

# PHP memory and execution limits
RUN { \
    echo 'memory_limit=512M'; \
    echo 'max_execution_time=300'; \
    echo 'max_input_time=300'; \
    echo 'upload_max_filesize=128M'; \
    echo 'post_max_size=128M'; \
    echo 'max_input_vars=5000'; \
} > /usr/local/etc/php/conf.d/limits-custom.ini

# Health check script
COPY scripts/health-check.sh /usr/local/bin/health-check
RUN chmod +x /usr/local/bin/health-check

WORKDIR /var/www/html
