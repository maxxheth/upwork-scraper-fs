@php
/**
 * Gutenberg ACF Block: Property Listing Map
 * Block name: acf/property-listing-map
 *
 * This block renders a Google Map with property markers.
 * ACF Fields:
 * - map_center_lat (text)
 * - map_center_lng (text)
 * - map_zoom (number, default: 10)
 * - map_height (number, default: 500)
 * - property_filter (taxonomy select)
 * - show_search (true/false)
 */
@endphp

@php
  $map_id = 'map-' . uniqid();
  $center_lat = get_field('map_center_lat') ?: 30.2672;
  $center_lng = get_field('map_center_lng') ?: -97.7431;
  $zoom = get_field('map_zoom') ?: 10;
  $map_height = get_field('map_height') ?: 500;
  $show_search = get_field('show_search') ?: true;

  // Query properties
  $args = [
    'post_type' => 'property',
    'posts_per_page' => -1,
    'meta_query' => [
      [
        'key' => 'property_lat',
        'compare' => 'EXISTS',
      ],
      [
        'key' => 'property_lng',
        'compare' => 'EXISTS',
      ],
    ],
  ];

  $filter = get_field('property_filter');
  if ($filter && $filter !== 'all') {
    $args['tax_query'] = [
      [
        'taxonomy' => 'property_type',
        'field' => 'slug',
        'terms' => $filter,
      ],
    ];
  }

  $properties = new WP_Query($args);
  $markers = [];

  while ($properties->have_posts()) {
    $properties->the_post();
    $lat = get_field('property_lat');
    $lng = get_field('property_lng');
    if ($lat && $lng) {
      $markers[] = [
        'lat' => (float) $lat,
        'lng' => (float) $lng,
        'title' => get_the_title(),
        'price' => get_field('property_price'),
        'url' => get_permalink(),
        'thumbnail' => get_the_post_thumbnail_url(get_the_ID(), 'thumbnail'),
      ];
    }
  }
  wp_reset_postdata();
@endphp

<section class="property-listing-map py-12">
  <div class="container mx-auto px-4">
    @if($show_search)
      <div class="property-listing-map__search mb-6">
        <div class="flex flex-wrap gap-4 items-center">
          <input
            type="text"
            id="{{ $map_id }}-search"
            placeholder="Search by city, zip, or address..."
            class="flex-1 min-w-[200px] px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <select
            id="{{ $map_id }}-filter"
            class="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Types</option>
            <option value="for-sale">For Sale</option>
            <option value="for-rent">For Rent</option>
            <option value="pending">Pending</option>
            <option value="sold">Sold</option>
          </select>
        </div>
      </div>
    @endif

    <div
      id="{{ $map_id }}"
      class="property-listing-map__canvas rounded-xl shadow-lg"
      style="height: {{ $map_height }}px;"
      data-center-lat="{{ $center_lat }}"
      data-center-lng="{{ $center_lng }}"
      data-zoom="{{ $zoom }}"
      data-markers="{{ json_encode($markers) }}"
    ></div>
  </div>
</section>

@push('scripts')
<script>
document.addEventListener('DOMContentLoaded', function() {
  const mapEl = document.getElementById('{{ $map_id }}');
  if (!mapEl || typeof google === 'undefined') return;

  const center = {
    lat: parseFloat(mapEl.dataset.centerLat),
    lng: parseFloat(mapEl.dataset.centerLng)
  };
  const zoom = parseInt(mapEl.dataset.zoom);
  const markers = JSON.parse(mapEl.dataset.markers);

  const map = new google.maps.Map(mapEl, {
    center: center,
    zoom: zoom,
    styles: [
      { featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] }
    ]
  });

  // Add markers
  const infoWindow = new google.maps.InfoWindow();
  markers.forEach(function(data) {
    const marker = new google.maps.Marker({
      position: { lat: data.lat, lng: data.lng },
      map: map,
      title: data.title
    });

    marker.addListener('click', function() {
      const content = `
        <div style="min-width: 200px;">
          ${data.thumbnail ? `<img src="${data.thumbnail}" alt="${data.title}" style="width:100%;height:120px;object-fit:cover;border-radius:8px;margin-bottom:8px;">` : ''}
          <h3 style="font-size:16px;font-weight:600;margin:0 0 4px;">${data.title}</h3>
          ${data.price ? `<p style="font-size:18px;font-weight:700;color:#2563eb;margin:0 0 8px;">$${Number(data.price).toLocaleString()}</p>` : ''}
          <a href="${data.url}" style="display:inline-block;background:#2563eb;color:white;padding:6px 16px;border-radius:6px;text-decoration:none;font-size:14px;">View Details</a>
        </div>
      `;
      infoWindow.setContent(content);
      infoWindow.open(map, marker);
    });
  });

  // Fit bounds if multiple markers
  if (markers.length > 1) {
    const bounds = new google.maps.LatLngBounds();
    markers.forEach(function(data) {
      bounds.extend(new google.maps.LatLng(data.lat, data.lng));
    });
    map.fitBounds(bounds);
  }
});
</script>
@endpush
