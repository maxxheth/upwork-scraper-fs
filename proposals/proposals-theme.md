# UpWork WordPress/Theme Proposals — Sage + Bedrock Stack

> **Portfolio Reference**: Groundhogs TX (groundhogstx.com) & Sandoval Landscaping (sandovallandscaping.com)
> **Stack**: Roots Bedrock + Sage, Carbon Fields, ACF, Blade, Vite, Docker

---

## Proposal 1: Web Developer with Netlify Expertise (Job 2)
**Score: 75 | $40-60/hr | $192K client, 65 hires**
🔗 **Job Link:** [Open in UpWork](https://www.upwork.com/jobs/span-class-highlight-Web-span-span-class-highlight-Developer-span-with-Netlify-Expertise-for-Digital-Marketing-Agency_~022069289456224146921/?referrer_url_path=/nx/search/jobs/)

### Cover Letter

Hi there,

I'm a senior WordPress developer specializing in the Roots Bedrock/Sage stack — the same modern tooling that powers production sites like **groundhogstx.com** and **sandovallandscaping.com**. I see you need a developer with Netlify expertise for landing pages and digital marketing sites.

**My approach for your Netlify-based sites:**

1. **Bedrock + Sage foundation** — Composer-managed WordPress with a modern Sage theme (Blade templating, Vite asset pipeline, ACF/Carbon Fields)
2. **Netlify deployment config** — `netlify.toml` with build commands, redirect rules, and headers for WordPress headless or static export
3. **Landing page component library** — Reusable Blade components (hero, CTA, features, testimonials) that your marketing team can compose via ACF flexible content
4. **CI/CD pipeline** — GitHub Actions → Netlify auto-deploy on merge

**Why me?** I've built and deployed multiple Bedrock/Sage sites with Docker-based local dev and production Netlify deployments. I can start with a small PoC — a deployable Netlify-ready Sage starter with a sample landing page — so you can evaluate the quality before committing.

**Technical approach:**
- `netlify.toml` with `[build]` command, redirect rules for SPA/headless, security headers
- Sage Blade components for landing page sections (hero, features grid, CTA, footer)
- ACF flexible content field group for page builder functionality
- Vite build pipeline with Netlify post-processing

I'm available to start immediately. Let's discuss your specific landing page needs.

Best,
Maxx

---

## Proposal 2: Elite Front-End Web Designer (Job 4)
**Score: 64 | $85-150/hr | $44K client, 26 hires**
🔗 **Job Link:** [Open in UpWork](https://www.upwork.com/jobs/Elite-Based-Front-End-span-class-highlight-Web-span-Designer-span-class-highlight-Developer-span-for-Lifestyle-amp-Real-Estate-span-class-highlight-Sites-span_~022068329701604066626/?referrer_url_path=/nx/search/jobs/)

### Cover Letter

Hi there,

I'm a front-end developer and designer who builds high-end real estate and lifestyle sites using the **Roots Bedrock/Sage stack** — the same architecture powering **groundhogstx.com** and **sandovallandscaping.com**. Your real estate / lifestyle focus is right in my wheelhouse.

**My approach for your real estate / lifestyle sites:**

1. **Pixel-perfect Figma-to-Blade** — I translate your Figma designs into Sage Blade components with responsive CSS, maintaining design fidelity across all breakpoints
2. **Property listing system** — Custom post type with ACF fields (price, beds/baths, sqft, gallery, map coordinates, status) with Blade templates for listing archive, single property, and search results
3. **Responsive by default** — Mobile-first CSS with Tailwind or custom utilities, tested on real devices
4. **Performance optimized** — Vite asset pipeline, lazy-loaded images, deferred JS

**Why me?** I've built production real estate listing components for government and commercial sites. I can deliver a PoC property listing component with ACF fields, Blade templates, and responsive CSS in 2-3 days.

**Technical approach:**
- `Property` custom post type with ACF field group (price, beds, baths, sqft, lot size, garage, year built, status, featured image gallery, map coordinates)
- Blade components: `components/property-card.blade.php`, `components/property-gallery.blade.php`, `components/property-search.blade.php`
- Responsive CSS with mobile-first grid layout
- Map integration service class for Google Maps or Leaflet

I'd love to start with a small PoC — a single property listing component with your design specs. Let me know when you'd like to chat.

Best,
Maxx

---

## Proposal 3: WordPress Developer (Job 7)
**Score: 61 | $5-50/hr | New client**
🔗 **Job Link:** [Open in UpWork](https://www.upwork.com/jobs/span-class-highlight-Wordpress-span_~022066899736999195859/?referrer_url_path=/nx/search/jobs/)

### Cover Letter

Hi there,

I'm a WordPress developer who specializes in the **Roots Bedrock/Sage stack** — the modern, professional way to build WordPress themes. I've used this stack on production sites like **groundhogstx.com** and **sandovallandscaping.com**.

**My approach for converting your HTML template to WordPress:**

1. **Sage theme scaffold** — I'll set up a clean Sage theme with Blade templating, Vite asset bundling, and ACF/Carbon Fields for content management
2. **HTML-to-Blade migration** — Your existing HTML template gets converted to Blade partials (header, footer, sidebar, content templates) with proper WordPress hooks
3. **Minimal but extensible** — No bloat, just clean PHP and modern tooling. Easy for you to extend later
4. **Docker local dev** — One-command WordPress environment with `docker compose up`

**Why me?** I can take your HTML template and have a working WordPress theme in days, not weeks. I'll provide a migration guide so you understand every step.

**Technical approach:**
- Sage theme scaffold with `composer.json` for Bedrock + Sage dependencies
- Blade-to-HTML migration guide showing how each HTML section maps to a Blade partial
- Docker Compose for local development (WordPress + MySQL)
- ACF flexible content for page building

I can start with a free PoC — a minimal Sage theme scaffold with a migration guide for your specific HTML template. Let's connect!

Best,
Maxx

---

## Proposal 4: WordPress Development Partner (Job 11/12)
**Score: 56 | $58K client, 146 hires**
🔗 **Job Link:** [Open in UpWork](https://www.upwork.com/jobs/span-class-highlight-Wordpress-span-span-class-highlight-Development-span-Partner_~022067238640056015777/)

### Cover Letter

Hi there,

I'm a WordPress developer looking for an ongoing partnership. I specialize in the **Roots Bedrock/Sage stack** — the same modern architecture used on **groundhogstx.com** and **sandovallandscaping.com**. With 146 hires and a $58K client, you clearly need a reliable technical partner.

**My approach for your digital strategy firm:**

1. **Gutenberg block development** — Custom ACF-registered Gutenberg blocks with Blade templates, fully compatible with the block editor
2. **Google Maps integration** — Service class for Maps API (geocoding, map rendering, location-based queries) with proper API key management
3. **Sage component architecture** — Reusable Blade components, View Composers for data, Service Providers for dependency injection
4. **Ongoing maintenance & feature development** — Reliable, well-documented code with Git workflow and CI/CD

**Why me?** I've built custom Gutenberg blocks, API integrations, and complex WordPress features for government and commercial sites. I'm looking for a long-term partner, not a one-off gig.

**Technical approach:**
- ACF block registration for Gutenberg (e.g., `property-listing`, `location-map`, `testimonial-carousel`)
- Blade templates for each block with proper block.json registration
- `GoogleMapsService` class with geocoding, distance calculation, and map rendering
- View Composers for injecting data into templates
- Docker-based local dev for consistent environments

I can deliver a PoC Gutenberg block + Maps integration in 3-5 days. Let's set up a call to discuss your pipeline.

Best,
Maxx

---

## Proposal 5: WordPress Website Developer (Job 15)
**Score: 55 | $20-50/hr | New client**
🔗 **Job Link:** [Open in UpWork](https://www.upwork.com/jobs/span-class-highlight-WordPress-span-Website-Developer_~022067262729506784185/)

### Cover Letter

Hi there,

I'm a WordPress developer who builds modern, professional business websites using the **Roots Bedrock/Sage stack** — the same architecture powering **groundhogstx.com** and **sandovallandscaping.com**. I can build your business site from scratch.

**My approach for your business website:**

1. **Full Sage theme scaffold** — Complete theme with Blade templates, Vite asset pipeline, ACF flexible content, and custom post types
2. **Business site patterns** — Services page, About page, Contact form, Team members, Testimonials, Blog
3. **Responsive & fast** — Mobile-first design, optimized images, minimal dependencies
4. **Docker local dev** — `docker compose up` gets you a running WordPress instantly

**Why me?** I've built multiple business sites from scratch using this stack. Clean, maintainable code with proper separation of concerns.

**Technical approach:**
- Sage theme with Blade templates for all standard page types
- Custom post types: Services, Team Members, Testimonials, FAQs
- ACF field groups for each post type
- Contact form with email service class
- Docker Compose for local development
- SEO-optimized markup with schema.org microdata

I can start with a full PoC theme scaffold in 2-3 days. Let's discuss your business requirements!

Best,
Maxx

---

## Summary Table

| # | Job | Rate | Client | Key Tech | PoC Deliverable |
|---|-----|------|--------|----------|-----------------|
| 1 | Netlify Developer | $40-60/hr | $192K, 65 hires | Netlify, Blade, Vite | netlify.toml + landing page components |
| 2 | Elite Front-End Designer | $85-150/hr | $44K, 26 hires | Figma, ACF, Responsive | Property listing component + ACF fields |
| 3 | WordPress Developer | $5-50/hr | New client | HTML→Blade migration | Sage scaffold + migration guide |
| 4 | WordPress Dev Partner | TBD | $58K, 146 hires | Gutenberg, Maps API | ACF block + GoogleMapsService |
| 5 | WordPress Website Dev | $20-50/hr | New client | Full business site | Complete theme scaffold + patterns |
