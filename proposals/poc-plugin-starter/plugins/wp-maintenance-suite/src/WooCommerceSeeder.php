<?php

declare(strict_types=1);

namespace Nous\WpMaintenanceSuite;

/**
 * WooCommerce test data seeder - creates sample products, orders, and customers.
 */
final class WooCommerceSeeder
{
    public function register(): void
    {
        add_action('admin_post_wpms_seed_woocommerce', [$this, 'handleSeedRequest']);
        add_action('admin_post_wpms_clear_woocommerce', [$this, 'handleClearRequest']);
    }

    /**
     * Seed WooCommerce with test data.
     *
     * @return array<string, mixed>
     */
    public function seed(): array
    {
        if (!class_exists('WooCommerce')) {
            return [
                'success' => false,
                'message' => 'WooCommerce is not active. Install and activate WooCommerce first.',
            ];
        }

        $results = [
            'products'    => $this->seedProducts(),
            'categories'  => $this->seedCategories(),
            'orders'      => $this->seedOrders(),
            'customers'   => $this->seedCustomers(),
        ];

        return [
            'success' => true,
            'message' => 'WooCommerce test data seeded successfully.',
            'results' => $results,
        ];
    }

    /**
     * Clear seeded WooCommerce data.
     *
     * @return array<string, mixed>
     */
    public function clear(): array
    {
        if (!class_exists('WooCommerce')) {
            return [
                'success' => false,
                'message' => 'WooCommerce is not active.',
            ];
        }

        $deleted = [
            'products'   => 0,
            'orders'     => 0,
            'customers'  => 0,
        ];

        // Delete seeded products
        $products = get_posts([
            'post_type'      => 'product',
            'posts_per_page' => -1,
            'meta_key'       => '_wpms_seeded',
            'meta_value'     => '1',
            'fields'         => 'ids',
        ]);

        foreach ($products as $productId) {
            wp_delete_post($productId, true);
            $deleted['products']++;
        }

        // Delete seeded orders
        $orders = wc_get_orders([
            'limit'       => -1,
            'meta_key'    => '_wpms_seeded',
            'meta_value'  => '1',
            'return'      => 'ids',
        ]);

        foreach ($orders as $orderId) {
            wp_delete_post($orderId, true);
            $deleted['orders']++;
        }

        // Delete seeded customers
        $customers = get_users([
            'role__in'  => ['customer'],
            'meta_key'  => '_wpms_seeded',
            'meta_value' => '1',
            'fields'    => 'ID',
        ]);

        foreach ($customers as $customerId) {
            wp_delete_user($customerId);
            $deleted['customers']++;
        }

        return [
            'success' => true,
            'message' => sprintf(
                'Cleared %d products, %d orders, and %d customers.',
                $deleted['products'],
                $deleted['orders'],
                $deleted['customers']
            ),
            'deleted' => $deleted,
        ];
    }

    /**
     * Seed product categories.
     */
    private function seedCategories(): int
    {
        $categories = [
            'Electronics',
            'Clothing',
            'Home & Garden',
            'Books',
            'Sports & Outdoors',
        ];

        $count = 0;
        foreach ($categories as $catName) {
            if (!term_exists($catName, 'product_cat')) {
                wp_insert_term($catName, 'product_cat');
                $count++;
            }
        }

        return $count;
    }

    /**
     * Seed sample products.
     */
    private function seedProducts(): int
    {
        $products = [
            [
                'name'        => 'Premium Widget',
                'description' => 'A high-quality premium widget for all your needs. Features durable construction and elegant design.',
                'price'       => '29.99',
                'category'    => 'Electronics',
                'sku'         => 'WIDGET-001',
            ],
            [
                'name'        => 'Deluxe T-Shirt',
                'description' => 'Comfortable 100% cotton t-shirt. Available in multiple sizes.',
                'price'       => '19.99',
                'category'    => 'Clothing',
                'sku'         => 'TSHIRT-001',
            ],
            [
                'name'        => 'Garden Tool Set',
                'description' => 'Complete garden tool set with ergonomic handles. Includes trowel, pruner, and gloves.',
                'price'       => '49.99',
                'category'    => 'Home & Garden',
                'sku'         => 'GARDEN-001',
            ],
            [
                'name'        => 'PHP Development Guide',
                'description' => 'Comprehensive guide to modern PHP development with WordPress. Covers OOP, PSR-4, and Composer.',
                'price'       => '39.99',
                'category'    => 'Books',
                'sku'         => 'BOOK-PHP-001',
            ],
            [
                'name'        => 'Yoga Mat Premium',
                'description' => 'Extra-thick premium yoga mat with non-slip surface. Includes carrying strap.',
                'price'       => '34.99',
                'category'    => 'Sports & Outdoors',
                'sku'         => 'YOGA-001',
            ],
        ];

        $count = 0;
        foreach ($products as $product) {
            $productId = wp_insert_post([
                'post_title'   => $product['name'],
                'post_content' => $product['description'],
                'post_status'  => 'publish',
                'post_type'    => 'product',
            ]);

            if (is_wp_error($productId)) {
                continue;
            }

            // Set as simple product
            wp_set_object_terms($productId, 'simple', 'product_type');
            update_post_meta($productId, '_wpms_seeded', '1');
            update_post_meta($productId, '_price', $product['price']);
            update_post_meta($productId, '_regular_price', $product['price']);
            update_post_meta($productId, '_sku', $product['sku']);
            update_post_meta($productId, '_stock_status', 'instock');
            update_post_meta($productId, '_manage_stock', 'yes');
            update_post_meta($productId, '_stock', rand(10, 100));

            // Assign category
            $term = get_term_by('name', $product['category'], 'product_cat');
            if ($term) {
                wp_set_object_terms($productId, $term->term_id, 'product_cat');
            }

            // Set product image placeholder
            $this->setProductImage($productId);

            $count++;
        }

        return $count;
    }

    /**
     * Seed sample orders.
     */
    private function seedOrders(): int
    {
        $products = get_posts([
            'post_type'      => 'product',
            'posts_per_page' => 3,
            'meta_key'       => '_wpms_seeded',
            'meta_value'     => '1',
            'fields'         => 'ids',
        ]);

        if (empty($products)) {
            return 0;
        }

        $statuses = ['completed', 'processing', 'on-hold', 'pending'];
        $count    = 0;

        for ($i = 0; $i < 5; $i++) {
            $order = wc_create_order();
            if (is_wp_error($order)) {
                continue;
            }

            // Add random products
            $numItems = rand(1, 3);
            for ($j = 0; $j < $numItems; $j++) {
                $productId = $products[array_rand($products)];
                $order->add_product(wc_get_product($productId), rand(1, 2));
            }

            $order->set_status($statuses[array_rand($statuses)]);
            $order->set_customer_id(0); // Guest order
            $order->update_meta_data('_wpms_seeded', '1');
            $order->calculate_totals();
            $order->save();

            $count++;
        }

        return $count;
    }

    /**
     * Seed sample customer accounts.
     */
    private function seedCustomers(): int
    {
        $customers = [
            ['email' => 'john.doe@example.com', 'name' => 'John Doe'],
            ['email' => 'jane.smith@example.com', 'name' => 'Jane Smith'],
            ['email' => 'bob.wilson@example.com', 'name' => 'Bob Wilson'],
        ];

        $count = 0;
        foreach ($customers as $data) {
            if (email_exists($data['email'])) {
                continue;
            }

            $userId = wp_insert_user([
                'user_login' => sanitize_user($data['email']),
                'user_email' => $data['email'],
                'display_name' => $data['name'],
                'user_pass'  => wp_generate_password(),
                'role'       => 'customer',
            ]);

            if (is_wp_error($userId)) {
                continue;
            }

            update_user_meta($userId, '_wpms_seeded', '1');
            $count++;
        }

        return $count;
    }

    /**
     * Set a placeholder product image.
     */
    private function setProductImage(int $productId): void
    {
        // Use a generated SVG placeholder
        $svg = sprintf(
            '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600">
                <rect fill="#f0f0f0" width="600" height="600"/>
                <text fill="#ccc" font-family="Arial" font-size="24" x="300" y="300" text-anchor="middle" dominant-baseline="middle">Product Image</text>
            </svg>'
        );

        $uploadDir = wp_upload_dir();
        $filename  = sprintf('product-%d.svg', $productId);
        $filepath   = $uploadDir['path'] . '/' . $filename;

        file_put_contents($filepath, $svg);

        $attachmentId = wp_insert_attachment([
            'post_mime_type' => 'image/svg+xml',
            'post_title'     => sprintf('Product %d Image', $productId),
            'post_content'   => '',
            'post_status'    => 'inherit',
        ], $filepath, $productId);

        if (!is_wp_error($attachmentId)) {
            set_post_thumbnail($productId, $attachmentId);
        }
    }

    /**
     * Handle seed request from admin.
     */
    public function handleSeedRequest(): void
    {
        if (!current_user_can('manage_options')) {
            wp_die('Unauthorized');
        }

        check_admin_referer('wpms_seed_woocommerce');

        $result = $this->seed();
        set_transient('wpms_seed_result', $result, 60);

        wp_redirect(admin_url('admin.php?page=wp-maintenance-suite&tab=woocommerce'));
        exit;
    }

    /**
     * Handle clear request from admin.
     */
    public function handleClearRequest(): void
    {
        if (!current_user_can('manage_options')) {
            wp_die('Unauthorized');
        }

        check_admin_referer('wpms_clear_woocommerce');

        $result = $this->clear();
        set_transient('wpms_clear_result', $result, 60);

        wp_redirect(admin_url('admin.php?page=wp-maintenance-suite&tab=woocommerce'));
        exit;
    }
}
