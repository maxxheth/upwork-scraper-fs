@props([
    'property' => [],
])

@php
    $statusLabels = [
        'for-sale' => 'For Sale',
        'for-lease' => 'For Lease',
        'sold' => 'Sold',
        'coming-soon' => 'Coming Soon',
    ];
    $statusColors = [
        'for-sale' => 'bg-green-500',
        'for-lease' => 'bg-blue-500',
        'sold' => 'bg-gray-500',
        'coming-soon' => 'bg-yellow-500',
    ];
    $status = $property['status'] ?? 'for-sale';
@endphp

<div class="group rounded-xl border border-zinc-100 bg-white shadow-xl shadow-zinc-200/50 overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl">
    {{-- Property Image --}}
    <div class="relative h-56 overflow-hidden">
        @if ($property['thumbnail'])
            <img src="{{ $property['thumbnail'] }}" alt="{{ $property['title'] }}"
                 class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" />
        @else
            <div class="w-full h-full bg-zinc-200 flex items-center justify-center">
                <svg class="w-12 h-12 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
            </div>
        @endif

        {{-- Status Badge --}}
        <span class="absolute top-3 left-3 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider text-white {{ $statusColors[$status] ?? 'bg-gray-500' }}">
            {{ $statusLabels[$status] ?? $status }}
        </span>

        {{-- Price --}}
        @if ($property['price'])
            <span class="absolute top-3 right-3 px-3 py-1 rounded-full text-sm font-bold bg-white/90 text-zinc-900 shadow">
                {{ $property['price'] }}
            </span>
        @endif
    </div>

    {{-- Property Details --}}
    <div class="p-5">
        <h3 class="text-lg font-bold text-zinc-900 mb-1">
            <a href="{{ $property['permalink'] }}" class="hover:text-brand-green transition-colors">
                {{ $property['title'] }}
            </a>
        </h3>

        @if ($property['address'] || $property['city'])
            <p class="text-sm text-zinc-500 mb-3">
                <svg class="inline w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {{ $property['address'] ?: '' }}{{ $property['city'] ? ', ' . $property['city'] : '' }}{{ $property['state'] ? ', ' . $property['state'] : '' }}
            </p>
        @endif

        {{-- Stats --}}
        <div class="flex gap-4 text-sm text-zinc-600 mb-4">
            @if ($property['bedrooms'])
                <span class="flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                    </svg>
                    {{ $property['bedrooms'] }} bed
                </span>
            @endif
            @if ($property['bathrooms'])
                <span class="flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    {{ $property['bathrooms'] }} bath
                </span>
            @endif
            @if ($property['sqft'])
                <span class="flex items-center gap-1">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                    </svg>
                    {{ number_format((int) $property['sqft']) }} sqft
                </span>
            @endif
        </div>

        {{-- Description --}}
        @if ($property['description'])
            <p class="text-sm text-zinc-600 line-clamp-2 mb-4">
                {{ strip_tags($property['description']) }}
            </p>
        @endif

        {{-- Amenities --}}
        @if (!empty($property['amenities']))
            <div class="flex flex-wrap gap-2 mb-4">
                @foreach (array_slice($property['amenities'], 0, 3) as $amenity)
                    <span class="px-2 py-1 bg-zinc-100 text-zinc-600 text-xs rounded">
                        {{ is_array($amenity) ? ($amenity['amenity'] ?? '') : $amenity }}
                    </span>
                @endforeach
                @if (count($property['amenities']) > 3)
                    <span class="px-2 py-1 bg-zinc-100 text-zinc-600 text-xs rounded">
                        +{{ count($property['amenities']) - 3 }} more
                    </span>
                @endif
            </div>
        @endif

        {{-- View Details Link --}}
        <a href="{{ $property['permalink'] }}"
           class="inline-flex items-center gap-2 text-sm font-semibold text-brand-green hover:text-brand-green-dark transition-colors">
            View Details
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
        </a>
    </div>
</div>
