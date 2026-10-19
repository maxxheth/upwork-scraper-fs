@props([
    'service' => [],
])

<div class="group p-6 rounded-xl border border-zinc-100 bg-white shadow-xl shadow-zinc-200/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl">
    @if ($service['icon'] ?? false)
        <div class="w-14 h-14 rounded-full bg-brand-green/10 flex items-center justify-center mb-4">
            <img src="{{ $service['icon'] }}" alt="" class="w-7 h-7" />
        </div>
    @endif

    <h3 class="text-xl font-bold text-zinc-900 mb-2">
        {{ $service['title'] ?? '' }}
    </h3>

    <p class="text-zinc-600 text-sm leading-relaxed mb-4">
        {{ $service['description'] ?? '' }}
    </p>

    @if ($service['url'] ?? false)
        <a href="{{ $service['url'] }}"
           class="inline-flex items-center gap-1 text-sm font-semibold text-brand-green hover:text-brand-green-dark transition-colors">
            Learn More
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
        </a>
    @endif
</div>
