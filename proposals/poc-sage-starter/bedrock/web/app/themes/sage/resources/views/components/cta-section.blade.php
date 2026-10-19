@props([
    'title' => 'Ready to Get Started?',
    'description' => 'Contact us today to discuss your project.',
    'ctaText' => 'Contact Us',
    'ctaUrl' => '#contact',
    'bgColor' => 'bg-brand-green',
])

<section class="py-20 {{ $bgColor }}">
    <div class="container mx-auto px-4 text-center">
        <h2 class="text-3xl md:text-4xl font-black text-white mb-4">
            {{ $title }}
        </h2>

        @if ($description)
            <p class="text-lg text-white/80 max-w-xl mx-auto mb-8">
                {{ $description }}
            </p>
        @endif

        <a href="{{ $ctaUrl }}"
           class="inline-flex items-center gap-2 px-8 py-4 bg-white text-zinc-900 font-bold rounded-xl hover:bg-zinc-100 transition-all duration-300">
            {{ $ctaText }}
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
        </a>
    </div>
</section>
