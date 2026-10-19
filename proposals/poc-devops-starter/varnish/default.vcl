vcl 4.1;

import std;

backend default {
    .host = "wordpress";
    .port = "80";
}

# Cloudflare-like caching rules
sub vcl_recv {
    # Only cache GET/HEAD requests
    if (req.method != "GET" && req.method != "HEAD") {
        return (pass);
    }

    # Skip cache for WP admin and logged-in users
    if (req.url ~ "^/wp-(admin|login|json)" || req.url ~ "preview=true") {
        return (pass);
    }

    # Skip cache for AJAX and API calls
    if (req.url ~ "admin-ajax" || req.url ~ "rest/v") {
        return (pass);
    }

    # Remove cookies for static files
    if (req.url ~ "\.(css|js|png|gif|jpg|jpeg|ico|svg|woff2?|ttf|eot|webp)(\?|$)") {
        unset req.http.Cookie;
        return (hash);
    }

    # Normalize Accept-Encoding
    if (req.http.Accept-Encoding) {
        if (req.url ~ "\.(jpg|jpeg|png|gif|gz|tgz|bz2|tbz|mp3|ogg|swf|webp)$") {
            unset req.http.Accept-Encoding;
        } elsif (req.http.Accept-Encoding ~ "gzip") {
            set req.http.Accept-Encoding = "gzip";
        } elsif (req.http.Accept-Encoding ~ "deflate") {
            set req.http.Accept-Encoding = "deflate";
        } else {
            unset req.http.Accept-Encoding;
        }
    }

    return (hash);
}

sub vcl_backend_response {
    # Cache static assets for 30 days
    if (bereq.url ~ "\.(css|js|png|gif|jpg|jpeg|ico|svg|woff2?|ttf|eot|webp)(\?|$)") {
        set beresp.ttl = 30d;
        set beresp.http.Cache-Control = "public, max-age=2592000, immutable";
    }

    # Cache HTML for 5 minutes
    if (beresp.http.Content-Type ~ "text/html") {
        set beresp.ttl = 5m;
        set beresp.http.Cache-Control = "public, max-age=300, s-maxage=300";
    }

    # Grace mode for stale content
    set beresp.grace = 1h;

    # Remove cookies from cacheable responses
    if (beresp.ttl > 0s) {
        unset beresp.http.Set-Cookie;
    }

    return (deliver);
}

sub vcl_deliver {
    # Add cache hit/miss header
    if (obj.hits > 0) {
        set resp.http.X-Cache = "HIT";
    } else {
        set resp.http.X-Cache = "MISS";
    }

    # Remove Varnish-specific headers
    unset resp.http.Via;
    unset resp.http.X-Varnish;
}
