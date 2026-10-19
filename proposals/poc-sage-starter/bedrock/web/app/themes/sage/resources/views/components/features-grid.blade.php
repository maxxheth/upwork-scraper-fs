@props([
    'title' => 'Our Services',
    'subtitle' => null,
    'services' => [],
])

<section class="py-20 bg-white">
    <div class="container mx-auto px-4">
        @if ($subtitle)
            <p class="text-sm font-bold uppercase tracking-[0.2em] text-brand-green text-center mb-4">
                {{ $subtitle }}
            </p>
        @endif

        @if ($title)
            <h2 class="text-3xl md:text-4xl font-black text-center text-zinc-900 mb-12">
                {{ $title }}
            </h2>
        @endif

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            @forelse ($services as $service)
                <div class="group p-6 rounded-xl border border-zinc-100 bg-white shadow-xl shadow-zinc-200/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl">
                    @if ($service['icon'] ?? false)
                        <div class="w-14 h-14 rounded-full bg-brand-green/10 flex items-center justify-center mb-4">
                            <img src="{{ $service['icon'] }}" alt="" class="w-7 h-7" />
                        </div>
                    @endif

                    <h3 class="text-xl font-bold text-zinc-900 mb-2">
                        {{ $service['title'] ?? '' }}
                    </h3>

                    <p class="text-zinc-600 text-sm leading-relaxed">
                        {{ $service['description'] ?? '' }}
                    </p>
                </div>
            @empty
                {{ $slot }}
            @endforelse
        </div>
    </div>
</section>
