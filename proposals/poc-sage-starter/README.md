# Sage + Bedrock PoC Starter

A proof-of-concept WordPress theme starter using the **Roots Bedrock + Sage** stack, designed for UpWork proposals. This PoC demonstrates production-ready patterns used on sites like **groundhogstx.com** and **sandovallandscaping.com**.

## What's Included

### 1. Netlify Deployment Config (Job 2)
- `netlify.toml` — Build commands, redirect rules, security headers, cache control
- PHP 8.1 + Node 20 + Composer 2 environment
- SPA fallback for headless mode
- Serverless function support

### 2. Real Estate Property Components (Job 4)
- `resources/views/components/property-card.blade.php` — Responsive property listing card with price, beds/baths/sqft, status badge, gallery
- `resources/views/components/property-listing-map.blade.php` — Google Maps block with markers, info windows, and search
- `app/Fields/acf-registrations.php` — ACF field groups for Property CPT (price, beds, baths, sqft, lot size, garage, year built, status, gallery, address, coordinates)
- `app/View/Composers/PropertyArchive.php` — View Composer with filtering, pagination, and aggregate stats
- `app/Http/Controllers/Api/PropertyController.php` — REST API endpoints for properties

### 3. Landing Page Components (Job 2 & 7)
- `resources/views/components/hero.blade.php` — Full-width hero with background image, overlay, CTA buttons, scroll indicator
- `resources/views/components/testimonial-carousel.blade.php` — Alpine.js-powered carousel with ratings, avatars, autoplay
- ACF flexible content field group for page builder functionality

### 4. Gutenberg Blocks (Job 11/12)
- `app/Providers/GutenbergBlockServiceProvider.php` — Registers ACF blocks: Property Listing Map, Testimonial Carousel, Hero Section
- Each block renders via Sage Blade templates
- Custom block category "Sage Blocks"

### 5. Google Maps Integration (Job 11/12)
- `app/Services/GoogleMapsService.php` — Geocoding, batch geocoding, distance calculation (Haversine), nearby property search
- API key management via `GOOGLE_MAPS_API_KEY` constant or env var
- Script enqueueing for frontend

### 6. Contact Form Service (Job 15)
- `app/Services/ContactFormService.php` — Validation, sanitization, honeypot, rate limiting, HTML email, database storage

### 7. Docker Local Dev (All Jobs)
- `docker-compose.yml` — WordPress (FPM), Nginx, MariaDB, Redis, phpMyAdmin, MailHog
- `config/nginx/default.conf` — Bedrock-optimized Nginx config
- `.env.example` — All environment variables documented

### 8. Composer Dependencies
- `composer.json` — Bedrock, Sage, ACF, Carbon Fields, WP SMTP, PHPCS

## Quick Start

```bash
# 1. Clone and install
cp .env.example .env
composer install
npm install

# 2. Start Docker
docker compose up -d

# 3. Build assets
npm run build

# 4. Access site
open http://localhost:8080
```

## Architecture

```
poc-sage-starter/
├── app/
│   ├── Fields/
│   │   └── acf-registrations.php      # ACF field groups + CPTs
│   ├── Http/
│   │   └── Controllers/
│   │       └── Api/
│   │           └── PropertyController.php  # REST API
│   ├── Providers/
│   │   ├── GutenbergBlockServiceProvider.php  # ACF blocks
│   │   └── ViewComposerServiceProvider.php    # View composers
│   ├── Services/
│   │   ├── ContactFormService.php     # Contact form handling
│   │   └── GoogleMapsService.php      # Maps API integration
│   └── View/
│       └── Composers/
│           └── PropertyArchive.php    # Property archive data
├── config/
│   └── nginx/
│       └── default.conf               # Nginx config
├── resources/
│   └── views/
│       └── components/
│           ├── hero.blade.php         # Landing page hero
│           ├── property-card.blade.php # Real estate card
│           ├── property-listing-map.blade.php # Map block
│           └── testimonial-carousel.blade.php # Testimonials
├── composer.json                      # PHP dependencies
├── docker-compose.yml                 # Local dev environment
├── netlify.toml                       # Netlify deployment
└── .env.example                      # Environment template
```

## Key Features

- **Blade Templating** — Clean, secure, extensible templates
- **Vite Asset Pipeline** — Fast HMR, optimized builds
- **ACF Flexible Content** — Page builder for non-developers
- **Gutenberg Blocks** — Custom blocks with Blade rendering
- **REST API** — Headless-capable endpoints
- **Docker Dev** — Consistent environments across team
- **Netlify Ready** — One-click deploy configuration

## Portfolio References

- **Groundhogs TX** (groundhogstx.com) — Bedrock + Sage production site
- **Sandoval Landscaping** (sandovallandscaping.com) — Bedrock + Sage production site

Both use the same stack demonstrated in this PoC: Bedrock for WordPress management, Sage for theme development, Blade for templating, ACF for content modeling, and Docker for local development.
