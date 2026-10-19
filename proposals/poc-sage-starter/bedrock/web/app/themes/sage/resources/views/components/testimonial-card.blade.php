@props([
    'testimonial' => [],
])

<div class="p-8 rounded-2xl border border-zinc-100 bg-white shadow-xl shadow-zinc-200/50">
    {{-- Quote --}}
    <svg class="w-8 h-8 text-brand-green/30 mb-4" fill="currentColor" viewBox="0 0 24 24">
        <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10H14.017zM0 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151C7.546 6.068 5.983 8.789 5.983 11H10v10H0z" />
    </svg>

    <blockquote class="text-zinc-700 text-lg leading-relaxed mb-6">
        {{ $testimonial['text'] ?? '' }}
    </blockquote>

    {{-- Author --}}
    <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-brand-green/20 flex items-center justify-center text-brand-green font-bold text-sm">
            {{ substr($testimonial['author'] ?? '?', 0, 1) }}
        </div>
        <div>
            <p class="font-bold text-zinc-900 text-sm">
                {{ $testimonial['author'] ?? '' }}
            </p>
            @if ($testimonial['position'] ?? false)
                <p class="text-zinc-500 text-xs">
                    {{ $testimonial['position'] }}
                </p>
            @endif
        </div>
    </div>
</div>
