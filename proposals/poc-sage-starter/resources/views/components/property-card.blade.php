@php
/**
 * Property Card Component for Real Estate Listings
 * Usage: @component('components.property-card', [
 *   'property' => $property // WP_Post object with ACF fields
 * ])
 * @endcomponent
 *
 * ACF Fields expected:
 * - property_price (number)
 * - property_bedrooms (number)
 * - property_bathrooms (number)
 * - property_sqft (number)
 * - property_lot_size (text)
 * - property_garage (number)
 * - property_year_built (number)
 * - property_status (select: for-sale, pending, sold, for-rent)
 * - property_gallery (gallery)
 * - property_address (text)
 * - property_city (text)
 * - property_state (text)
 * - property_zip (text)
 * - property_lat (text)
 * - property_lng (text)
 * - featured_image (featured image)
 */
@endphp

<div class="property-card group bg-white rounded-xl shadow-md overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-1">
  {{-- Property Image --}}
  <div class="property-card__image relative aspect-[4/3] overflow-hidden">
    @if(has_post_thumbnail($property))
      <img
        src="{{ get_the_post_thumbnail_url($property, 'large') }}"
        alt="{{ get_the_title($property) }}"
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        loading="lazy"
      />
    @else
      <div class="w-full h-full bg-gray-200 flex items-center justify-center">
        <svg class="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
        </svg>
      </div>
    @endif

    {{-- Status Badge --}}
    @php $status = get_field('property_status', $property->ID); @endphp
    @if($status)
      <span class="property-card__status absolute top-4 left-4 px-3 py-1 rounded-full text-sm font-semibold text-white
        @if($status === 'for-sale') bg-green-600
        @elseif($status === 'pending') bg-yellow-500
        @elseif($status === 'sold') bg-red-600
        @elseif($status === 'for-rent') bg-blue-600
        @else bg-gray-600 @endif">
        {{ ucfirst(str_replace('-', ' ', $status)) }}
      </span>
    @endif

    {{-- Price --}}
    @php $price = get_field('property_price', $property->ID); @endphp
    @if($price)
      <div class="property-card__price absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm px-4 py-2 rounded-lg shadow">
        <span class="text-2xl font-bold text-gray-900">
          ${{ number_format($price) }}
        </span>
      </div>
    @endif
  </div>

  {{-- Property Details --}}
  <div class="property-card__details p-6">
    <h3 class="property-card__title text-xl font-semibold text-gray-900 mb-2">
      <a href="{{ get_permalink($property) }}" class="hover:text-blue-600 transition-colors">
        {{ get_the_title($property) }}
      </a>
    </h3>

    @php $address = get_field('property_address', $property->ID); @endphp
    @if($address)
      <p class="property-card__address text-gray-500 mb-4">
        <svg class="inline-block w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
        </svg>
        {{ $address }}
      </p>
    @endif

    {{-- Stats Grid --}}
    <div class="property-card__stats grid grid-cols-3 gap-4 border-t border-gray-100 pt-4">
      @php $beds = get_field('property_bedrooms', $property->ID); @endphp
      @if($beds)
        <div class="text-center">
          <span class="block text-lg font-bold text-gray-900">{{ $beds }}</span>
          <span class="block text-xs text-gray-500 uppercase tracking-wide">Beds</span>
        </div>
      @endif

      @php $baths = get_field('property_bathrooms', $property->ID); @endphp
      @if($baths)
        <div class="text-center">
          <span class="block text-lg font-bold text-gray-900">{{ $baths }}</span>
          <span class="block text-xs text-gray-500 uppercase tracking-wide">Baths</span>
        </div>
      @endif

      @php $sqft = get_field('property_sqft', $property->ID); @endphp
      @if($sqft)
        <div class="text-center">
          <span class="block text-lg font-bold text-gray-900">{{ number_format($sqft) }}</span>
          <span class="block text-xs text-gray-500 uppercase tracking-wide">Sq Ft</span>
        </div>
      @endif
    </div>

    {{-- Additional details row --}}
    <div class="property-card__extras flex flex-wrap gap-3 mt-4 text-sm text-gray-500">
      @php $garage = get_field('property_garage', $property->ID); @endphp
      @if($garage)
        <span class="flex items-center">
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path>
          </svg>
          {{ $garage }} Garage
        </span>
      @endif

      @php $year = get_field('property_year_built', $property->ID); @endphp
      @if($year)
        <span class="flex items-center">
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
          </svg>
          Built {{ $year }}
        </span>
      @endif

      @php $lot = get_field('property_lot_size', $property->ID); @endphp
      @if($lot)
        <span class="flex items-center">
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"></path>
          </svg>
          {{ $lot }}
        </span>
      @endif
    </div>
  </div>

  {{-- View Details Link --}}
  <div class="property-card__footer px-6 pb-6">
    <a
      href="{{ get_permalink($property) }}"
      class="block w-full text-center bg-blue-600 text-white font-semibold py-3 rounded-lg hover:bg-blue-700 transition-colors duration-200"
    >
      View Details
    </a>
  </div>
</div>
