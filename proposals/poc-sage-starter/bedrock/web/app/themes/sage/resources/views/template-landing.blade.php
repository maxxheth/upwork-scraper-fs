@extends('layouts.app')

@section('content')
    @include('partials.page-header')

    <div class="container mx-auto px-4 py-12">
        <div class="prose prose-lg max-w-none">
            @php(the_content())
        </div>

        @include('components.landing-hero')
        @include('components.features-grid')
        @include('components.cta-section')
    </div>
@endsection
