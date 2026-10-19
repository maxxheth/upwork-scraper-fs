@extends('layouts.app')

@section('content')
    @include('partials.page-header')

    <div class="container mx-auto px-4 py-12">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            @foreach ($services as $service)
                @include('components.service-card', ['service' => $service])
            @endforeach
        </div>
    </div>
@endsection
