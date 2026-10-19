@php
/**
 * Hero Component for Landing Pages
 * Usage: @component('components.hero', [
 *   'title' => 'Welcome',
 *   'subtitle' => 'Your subtitle here',
 *   'background_image' => wp_get_attachment_image_url(get_field('hero_background'), 'full'),
 *   'cta_text' => 'Get Started',
 *   'cta_url' => '/contact',
 *   'overlay_opacity' => 0.6
 * ])
 * @endcomponent
 */
@endphp

<section class="hero relative min-h-[80vh] flex items-center justify-center overflow-hidden">
  {{-- Background Image --}}
  @if($background_image ?? false)
    <div class="hero__background absolute inset-0 z-0">
      <img
        src="{{ $background_image }}"
        alt="{{ $title ?? 'Hero background' }}"
        class="w-full h-full object-cover"
        loading="lazy"
      />
    </div>
    {{-- Overlay --}}
    <div
      class="hero__overlay absolute inset-0 z-[1]"
      style="background: rgba(0,0,0,{{ $overlay_opacity ?? 0.5 }});"
    ></div>
  @endif

  {{-- Content --}}
  <div class="hero__content relative z-[2] text-center px-4 max-w-4xl mx-auto">
    @if($pretitle ?? false)
      <span class="hero__pretitle inline-block text-sm uppercase tracking-widest text-white/80 mb-4">
        {{ $pretitle }}
      </span>
    @endif

    <h1 class="hero__title text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight">
      {{ $title ?? 'Default Title' }}
    </h1>

    @if($subtitle ?? false)
      <p class="hero__subtitle text-xl md:text-2xl text-white/90 mb-8 max-w-2xl mx-auto">
        {{ $subtitle }}
      </p>
    @endif

    @if(($cta_text ?? false) && ($cta_url ?? false))
      <a
        href="{{ $cta_url }}"
        class="hero__cta inline-block bg-white text-gray-900 font-semibold px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors duration-200 shadow-lg"
      >
        {{ $cta_text }}
      </a>
    @endif

    @if($secondary_cta_text ?? false)
      <a
        href="{{ $secondary_cta_url ?? '#' }}"
        class="hero__cta-secondary inline-block ml-4 text-white font-semibold px-8 py-4 rounded-lg border-2 border-white hover:bg-white/10 transition-colors duration-200"
      >
        {{ $secondary_cta_text }}
      </a>
    @endif
  </div>

  {{-- Scroll indicator --}}
  <div class="hero__scroll absolute bottom-8 left-1/2 -translate-x-1/2 z-[2] animate-bounce">
    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path>
    </svg>
  </div>
</section>

@php
/**
 * Styles (add to your theme's CSS or Tailwind config)
 *
 * .hero {
 *   position: relative;
 *   min-height: 80vh;
 *   display: flex;
 *   align-items: center;
 *   justify-content: center;
 *   overflow: hidden;
 * }
 *
 * @media (max-width: 768px) {
 *   .hero {
 *     min-height: 60vh;
 *   }
 *   .hero__title {
 *     font-size: 2.5rem;
 *   }
 * }
 */
@endphp
