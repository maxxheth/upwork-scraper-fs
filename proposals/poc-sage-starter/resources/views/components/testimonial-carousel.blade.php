@php
/**
 * Testimonial Carousel Component
 * Usage: @component('components.testimonial-carousel', ['testimonials' => $testimonials])
 *
 * ACF Fields (repeater):
 * - testimonial_quote (textarea)
 * - testimonial_author (text)
 * - testimonial_role (text)
 * - testimonial_company (text)
 * - testimonial_avatar (image)
 * - testimonial_rating (number, 1-5)
 */
@endphp

<section class="testimonial-carousel py-16 bg-gray-50">
  <div class="container mx-auto px-4">
    @if($title ?? false)
      <h2 class="testimonial-carousel__title text-3xl md:text-4xl font-bold text-center mb-12">
        {{ $title }}
      </h2>
    @endif

    @if(!empty($testimonials))
      <div
        class="testimonial-carousel__track relative overflow-hidden"
        x-data="testimonialCarousel()"
        x-init="init()"
      >
        <div class="flex transition-transform duration-500 ease-in-out"
             :style="`transform: translateX(-${currentSlide * 100}%)`">
          @foreach($testimonials as $testimonial)
            <div class="testimonial-carousel__slide min-w-full md:min-w-[50%] lg:min-w-[33.333%] px-4">
              <div class="bg-white rounded-xl shadow-md p-8 h-full flex flex-col">
                {{-- Rating Stars --}}
                @if($testimonial['testimonial_rating'] ?? false)
                  <div class="testimonial-carousel__rating mb-4 flex gap-1">
                    @for($i = 1; $i <= 5; $i++)
                      <svg class="w-5 h-5 {{ $i <= $testimonial['testimonial_rating'] ? 'text-yellow-400' : 'text-gray-300' }}"
                           fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                      </svg>
                    @endfor
                  </div>
                @endif

                {{-- Quote --}}
                <blockquote class="testimonial-carousel__quote flex-1 text-gray-700 text-lg leading-relaxed mb-6">
                  "{{ $testimonial['testimonial_quote'] ?? '' }}"
                </blockquote>

                {{-- Author --}}
                <div class="testimonial-carousel__author flex items-center gap-4 mt-auto pt-6 border-t border-gray-100">
                  @if($testimonial['testimonial_avatar'] ?? false)
                    <img
                      src="{{ $testimonial['testimonial_avatar']['url'] ?? $testimonial['testimonial_avatar'] }}"
                      alt="{{ $testimonial['testimonial_author'] ?? 'Avatar' }}"
                      class="w-12 h-12 rounded-full object-cover"
                      loading="lazy"
                    />
                  @else
                    <div class="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                      <span class="text-blue-600 font-bold text-lg">
                        {{ substr($testimonial['testimonial_author'] ?? '?', 0, 1) }}
                      </span>
                    </div>
                  @endif
                  <div>
                    <p class="font-semibold text-gray-900">{{ $testimonial['testimonial_author'] ?? '' }}</p>
                    <p class="text-sm text-gray-500">
                      {{ $testimonial['testimonial_role'] ?? '' }}
                      @if($testimonial['testimonial_company'] ?? false)
                        , {{ $testimonial['testimonial_company'] }}
                      @endif
                    </p>
                  </div>
                </div>
              </div>
            </div>
          @endforeach
        </div>

        {{-- Navigation Arrows --}}
        <button @click="prev()" class="absolute left-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white shadow-lg rounded-full p-3 transition-all z-10">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
          </svg>
        </button>
        <button @click="next()" class="absolute right-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white shadow-lg rounded-full p-3 transition-all z-10">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
          </svg>
        </button>

        {{-- Dots --}}
        <div class="flex justify-center gap-2 mt-8">
          <template x-for="(slide, index) in slides" :key="index">
            <button
              @click="goTo(index)"
              :class="{'bg-blue-600 w-8': currentSlide === index, 'bg-gray-300 w-3': currentSlide !== index}"
              class="h-3 rounded-full transition-all duration-300"
            ></button>
          </template>
        </div>
      </div>

      <script>
      function testimonialCarousel() {
        return {
          currentSlide: 0,
          slides: @json($testimonials),
          autoplayInterval: null,

          init() {
            this.startAutoplay();
          },

          next() {
            const total = this.slides.length;
            this.currentSlide = (this.currentSlide + 1) % total;
            this.resetAutoplay();
          },

          prev() {
            const total = this.slides.length;
            this.currentSlide = (this.currentSlide - 1 + total) % total;
            this.resetAutoplay();
          },

          goTo(index) {
            this.currentSlide = index;
            this.resetAutoplay();
          },

          startAutoplay() {
            this.autoplayInterval = setInterval(() => this.next(), 5000);
          },

          resetAutoplay() {
            clearInterval(this.autoplayInterval);
            this.startAutoplay();
          }
        }
      }
      </script>
    @else
      <p class="text-center text-gray-500">No testimonials available.</p>
    @endif
  </div>
</section>
