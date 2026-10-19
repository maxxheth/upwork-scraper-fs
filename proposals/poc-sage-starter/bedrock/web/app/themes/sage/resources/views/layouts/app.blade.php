<!doctype html>
<html @php(language_attributes())>

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    @php(do_action('get_header'))
    @php(wp_head())

    @vite(['resources/css/app.css', 'resources/js/app.ts'])
</head>

<body @php(body_class('bg-white font-sans text-zinc-900 antialiased'))>
    @php(wp_body_open())

    <div id="app" class="flex min-h-screen flex-col">
        <a class="sr-only focus:not-sr-only focus:left-4 focus:top-4" href="#main">
            {{ __('Skip to content', 'sage') }}
        </a>

        @include('sections.header')

        <main id="main" class="main flex-1">
            @yield('content')
        </main>

        @include('sections.footer')
    </div>

    @php(do_action('get_footer'))
    @php(wp_footer())
</body>

</html>
