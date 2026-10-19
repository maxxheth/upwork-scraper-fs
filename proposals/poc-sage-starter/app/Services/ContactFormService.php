<?php
/**
 * Contact Form Service
 *
 * Handles contact form submissions with validation, sanitization,
 * and email delivery via WordPress wp_mail or SMTP.
 *
 * @package Sage\Services
 */

namespace App\Services;

class ContactFormService
{
    /**
     * Validation errors
     *
     * @var array
     */
    protected array $errors = [];

    /**
     * Process a contact form submission
     *
     * @param array $data Form data (name, email, phone, subject, message)
     * @return array{success: bool, message: string, errors?: array}
     */
    public function process(array $data): array
    {
        $this->errors = [];

        // Sanitize inputs
        $name    = sanitize_text_field($data['name'] ?? '');
        $email   = sanitize_email($data['email'] ?? '');
        $phone   = sanitize_text_field($data['phone'] ?? '');
        $subject = sanitize_text_field($data['subject'] ?? '');
        $message = sanitize_textarea_field($data['message'] ?? '');

        // Validate
        if (empty($name)) {
            $this->errors['name'] = 'Name is required.';
        }

        if (empty($email) || !is_email($email)) {
            $this->errors['email'] = 'A valid email address is required.';
        }

        if (empty($message)) {
            $this->errors['message'] = 'Message is required.';
        }

        // Honeypot check
        if (!empty($data['website'] ?? '')) {
            return [
                'success' => true,
                'message' => 'Thank you for your message. We will get back to you shortly.',
            ];
        }

        // Rate limiting (1 submission per minute per IP)
        $rateLimitKey = 'contact_form_' . $this->getClientIp();
        $lastSubmission = get_transient($rateLimitKey);
        if ($lastSubmission) {
            return [
                'success' => false,
                'message' => 'Please wait before submitting another message.',
            ];
        }

        if (!empty($this->errors)) {
            return [
                'success' => false,
                'message' => 'Please correct the errors below.',
                'errors'  => $this->errors,
            ];
        }

        // Build email
        $to = $this->getRecipientEmail();
        $emailSubject = sprintf('[%s] %s', get_bloginfo('name'), $subject ?: 'New Contact Form Submission');
        $headers = [
            'Content-Type: text/html; charset=UTF-8',
            sprintf('From: %s <%s>', $name, $email),
            sprintf('Reply-To: %s <%s>', $name, $email),
        ];

        $body = $this->buildEmailBody($name, $email, $phone, $subject, $message);

        // Send email
        $sent = wp_mail($to, $emailSubject, $body, $headers);

        if ($sent) {
            // Set rate limit
            set_transient($rateLimitKey, time(), MINUTE_IN_SECONDS);

            // Store in database (optional)
            $this->storeSubmission($name, $email, $phone, $subject, $message);

            return [
                'success' => true,
                'message' => 'Thank you for your message. We will get back to you shortly.',
            ];
        }

        return [
            'success' => false,
            'message' => 'There was an error sending your message. Please try again later.',
        ];
    }

    /**
     * Build HTML email body
     */
    protected function buildEmailBody(
        string $name,
        string $email,
        string $phone,
        string $subject,
        string $message
    ): string {
        $siteName = get_bloginfo('name');
        $siteUrl  = get_bloginfo('url');

        ob_start();
        ?>
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #f8f9fa; border-radius: 12px; padding: 30px;">
                <h1 style="color: #1a1a2e; font-size: 24px; margin: 0 0 20px;">New Contact Form Submission</h1>
                <p style="color: #6c757d; margin: 0 0 20px;">From <strong><?= esc_html($siteName) ?></strong></p>

                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #6c757d; width: 100px;">Name:</td>
                        <td style="padding: 10px 0; font-weight: 600;"><?= esc_html($name) ?></td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #6c757d;">Email:</td>
                        <td style="padding: 10px 0;"><a href="mailto:<?= esc_attr($email) ?>"><?= esc_html($email) ?></a></td>
                    </tr>
                    <?php if ($phone): ?>
                    <tr>
                        <td style="padding: 10px 0; color: #6c757d;">Phone:</td>
                        <td style="padding: 10px 0;"><?= esc_html($phone) ?></td>
                    </tr>
                    <?php endif; ?>
                    <?php if ($subject): ?>
                    <tr>
                        <td style="padding: 10px 0; color: #6c757d;">Subject:</td>
                        <td style="padding: 10px 0;"><?= esc_html($subject) ?></td>
                    </tr>
                    <?php endif; ?>
                </table>

                <div style="background: white; border-radius: 8px; padding: 20px; margin-top: 20px;">
                    <h3 style="margin: 0 0 10px; color: #1a1a2e;">Message:</h3>
                    <p style="margin: 0; line-height: 1.6; color: #333;"><?= nl2br(esc_html($message)) ?></p>
                </div>

                <p style="color: #6c757d; font-size: 12px; margin-top: 20px;">
                    Sent from <a href="<?= esc_url($siteUrl) ?>" style="color: #2563eb;"><?= esc_html($siteName) ?></a>
                </p>
            </div>
        </body>
        </html>
        <?php
        return ob_get_clean();
    }

    /**
     * Store submission in database for record-keeping
     */
    protected function storeSubmission(
        string $name,
        string $email,
        string $phone,
        string $subject,
        string $message
    ): void {
        global $wpdb;

        $wpdb->insert(
            $wpdb->prefix . 'contact_submissions',
            [
                'name'      => $name,
                'email'     => $email,
                'phone'     => $phone,
                'subject'   => $subject,
                'message'   => $message,
                'ip'        => $this->getClientIp(),
                'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? '',
                'created_at' => current_time('mysql'),
            ],
            ['%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s']
        );
    }

    /**
     * Get the recipient email address
     */
    protected function getRecipientEmail(): string
    {
        $email = get_field('contact_form_email', 'option');
        if (!$email) {
            $email = get_option('admin_email');
        }
        return $email;
    }

    /**
     * Get client IP address
     */
    protected function getClientIp(): string
    {
        if (!empty($_SERVER['HTTP_CLIENT_IP'])) {
            return $_SERVER['HTTP_CLIENT_IP'];
        }
        if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
            return explode(',', $_SERVER['HTTP_X_FORWARDED_FOR'])[0];
        }
        return $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    }
}
