<?php

declare(strict_types=1);

namespace Nous\WpCustomThemeKit;

/**
 * Handles front-end form submissions (Gravity Forms alternative using WP Forms API).
 */
final class FormHandler
{
    public function register(): void
    {
        add_action('init', [$this, 'registerContactFormPostType']);
        add_action('wp_ajax_nopriv_submit_custom_form', [$this, 'handleAjaxSubmission']);
        add_action('wp_ajax_submit_custom_form', [$this, 'handleAjaxSubmission']);
        add_shortcode('custom_contact_form', [$this, 'renderContactFormShortcode']);
    }

    /**
     * Register a custom post type to store form submissions.
     */
    public function registerContactFormPostType(): void
    {
        register_post_type('form_submission', [
            'labels'              => [
                'name'          => __('Form Submissions', 'wp-custom-theme-kit'),
                'singular_name' => __('Form Submission', 'wp-custom-theme-kit'),
            ],
            'public'              => false,
            'show_ui'             => true,
            'show_in_menu'        => true,
            'menu_icon'           => 'dashicons-email-alt',
            'supports'            => ['title', 'editor'],
            'capability_type'     => 'post',
            'capabilities'        => [
                'create_posts' => 'do_not_allow', // Only programmatic creation
            ],
            'map_meta_cap'        => true,
        ]);
    }

    /**
     * AJAX handler for form submissions.
     */
    public function handleAjaxSubmission(): void
    {
        // Verify nonce
        if (!wp_verify_nonce($_POST['nonce'] ?? '', 'custom_form_nonce')) {
            wp_send_json_error(['message' => 'Security check failed.']);
        }

        $name    = sanitize_text_field(wp_unslash($_POST['name'] ?? ''));
        $email   = sanitize_email(wp_unslash($_POST['email'] ?? ''));
        $subject = sanitize_text_field(wp_unslash($_POST['subject'] ?? ''));
        $message = sanitize_textarea_field(wp_unslash($_POST['message'] ?? ''));

        // Validation
        $errors = [];
        if (empty($name)) {
            $errors[] = __('Name is required.', 'wp-custom-theme-kit');
        }
        if (empty($email) || !is_email($email)) {
            $errors[] = __('A valid email is required.', 'wp-custom-theme-kit');
        }
        if (empty($message)) {
            $errors[] = __('Message is required.', 'wp-custom-theme-kit');
        }

        if (!empty($errors)) {
            wp_send_json_error(['errors' => $errors]);
        }

        // Store submission
        $postId = wp_insert_post([
            'post_title'   => sprintf('Submission from %s (%s)', $name, $email),
            'post_type'    => 'form_submission',
            'post_status'  => 'publish',
            'post_content' => sprintf(
                "Name: %s\nEmail: %s\nSubject: %s\nMessage:\n%s",
                $name,
                $email,
                $subject,
                $message
            ),
        ]);

        if (is_wp_error($postId)) {
            wp_send_json_error(['message' => 'Failed to save submission.']);
        }

        // Save meta
        update_post_meta($postId, '_submission_name', $name);
        update_post_meta($postId, '_submission_email', $email);
        update_post_meta($postId, '_submission_subject', $subject);

        // Send email notification
        $adminEmail = get_option('admin_email');
        wp_mail(
            $adminEmail,
            sprintf('[%s] New Contact Form Submission from %s', get_bloginfo('name'), $name),
            sprintf("Name: %s\nEmail: %s\nSubject: %s\nMessage:\n%s", $name, $email, $subject, $message),
            ['Reply-To: ' . $email]
        );

        wp_send_json_success([
            'message' => __('Thank you! Your message has been sent.', 'wp-custom-theme-kit'),
        ]);
    }

    /**
     * Shortcode: [custom_contact_form]
     */
    public function renderContactFormShortcode(): string
    {
        ob_start();
        ?>
        <form class="custom-contact-form" method="post" action="<?php echo esc_url(admin_url('admin-ajax.php')); ?>">
            <div class="form-field">
                <label for="cf_name"><?php esc_html_e('Name *', 'wp-custom-theme-kit'); ?></label>
                <input type="text" id="cf_name" name="name" required />
            </div>

            <div class="form-field">
                <label for="cf_email"><?php esc_html_e('Email *', 'wp-custom-theme-kit'); ?></label>
                <input type="email" id="cf_email" name="email" required />
            </div>

            <div class="form-field">
                <label for="cf_subject"><?php esc_html_e('Subject', 'wp-custom-theme-kit'); ?></label>
                <input type="text" id="cf_subject" name="subject" />
            </div>

            <div class="form-field">
                <label for="cf_message"><?php esc_html_e('Message *', 'wp-custom-theme-kit'); ?></label>
                <textarea id="cf_message" name="message" rows="5" required></textarea>
            </div>

            <input type="hidden" name="action" value="submit_custom_form" />
            <input type="hidden" name="nonce" value="<?php echo esc_attr(wp_create_nonce('custom_form_nonce')); ?>" />

            <button type="submit" class="button button-primary">
                <?php esc_html_e('Send Message', 'wp-custom-theme-kit'); ?>
            </button>

            <div class="form-feedback" style="display:none;"></div>
        </form>

        <style>
            .custom-contact-form .form-field { margin-bottom: 1rem; }
            .custom-contact-form label { display: block; font-weight: 600; margin-bottom: 0.25rem; }
            .custom-contact-form input,
            .custom-contact-form textarea { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; }
            .custom-contact-form .form-feedback { margin-top: 1rem; padding: 0.75rem; border-radius: 4px; }
            .custom-contact-form .form-feedback.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .custom-contact-form .form-feedback.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>

        <script>
        jQuery(document).ready(function($) {
            $('.custom-contact-form').on('submit', function(e) {
                e.preventDefault();
                var $form = $(this);
                var $feedback = $form.find('.form-feedback');

                $.post($form.attr('action'), $form.serialize(), function(response) {
                    if (response.success) {
                        $feedback.removeClass('error').addClass('success')
                            .html('<p>' + response.data.message + '</p>').show();
                        $form[0].reset();
                    } else {
                        var errors = response.data.errors || [response.data.message];
                        $feedback.removeClass('success').addClass('error')
                            .html('<ul><li>' + errors.join('</li><li>') + '</li></ul>').show();
                    }
                });
            });
        });
        </script>
        <?php
        return ob_get_clean();
    }
}
