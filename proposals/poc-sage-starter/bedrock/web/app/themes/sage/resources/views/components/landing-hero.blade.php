@props([
    'title' => null,
    'subtitle' => null,
    'description' => null,
    'ctaText' => 'Get Started',
    'ctaUrl' => '#contact',
    'secondaryCtaText' => null,
    'secondaryCtaUrl' => null,
    'backgroundImage' => null,
    'overlayOpacity' => 0.5,
])

<section class="relative overflow-hidden bg-zinc-900 text-white py-24">
    {{-- Background --}}
    @if ($backgroundImage)
        <div class="absolute inset-0">
            <img src="{{ $backgroundImage }}" alt="" class="w-full h-full object-cover" />
            <div class="absolute inset-0 bg-black" style="opacity: {{ $overlayOpacity }}"></div>
        </div>
    @else
        <div class="absolute inset-0 bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900"></div>
    @endif

    {{-- Content --}}
    <div class="relative container mx-auto px-4 text-center">
        @if ($subtitle)
            <p class="text-sm font-bold uppercase tracking-[0.2em] text-brand-green mb-4">
                {{ $subtitle }}
            </p>
        @endif

        @if ($title)
            <h1 class="text-4xl md:text-5xl lg:text-6xl font-black tracking-tight mb-6">
                {{ $title }}
            </h1>
        @endif

        @if ($description)
            <p class="text-lg md:text-xl text-zinc-300 max-w-2xl mx-auto mb-8">
                {{ $description }}
            </p>
        @endif

        <div class="flex flex-col sm:flex-row gap-4 justify-center">
            <a href="{{ $ctaUrl }}"
               class="inline-flex items-center gap-2 px-8 py-4 bg-brand-green text-white font-bold rounded-xl hover:bg-brand-green-dark transition-all duration-300">
                {{ $ctaText }}
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
            </a>

            @if ($secondaryCtaText && $secondaryCtaUrl)
                <a href="{{ $secondaryCtaUrl }}"
                   class="inline-flex items-center gap-2 px-8 py-4 border-2 border-white/30 text-white font-bold rounded-xl hover:bg-white/10 transition-all duration-300">
                    {{ $secondaryCtaText }}
                </a>
            @endif
        </div>
    </div>
</section>
