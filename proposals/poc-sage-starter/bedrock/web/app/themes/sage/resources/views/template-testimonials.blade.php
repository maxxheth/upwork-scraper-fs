@extends('layouts.app')

@section('content')
    @include('partials.page-header')

    <div class="container mx-auto px-4 py-12">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            @foreach ($testimonials as $testimonial)
                @include('components.testimonial-card', ['testimonial' => $testimonial])
            @endforeach
        </div>
    </div>
@endsection
