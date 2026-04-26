const CACHE_NAME = 'pos-cache-v1';
const DB_NAME = 'posOfflineDB';

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll([
                '/',
                '/static/js/pos.js',
                '/static/js/sync.js'
            ]);
        })
    );
    self.skipWaiting();
});

self.addEventListener('fetch', event => {
    // Network-first for APIs, cache fallback for assets
    if (event.request.url.includes('/api/')) {
        event.respondWith(
            fetch(event.request).catch(() => new Response(JSON.stringify({ error: "Offline" }), {
                headers: { 'Content-Type': 'application/json' },
                status: 503
            }))
        );
    } else {
        event.respondWith(
            caches.match(event.request).then(response => {
                return response || fetch(event.request).then(fetchRes => {
                    return caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, fetchRes.clone());
                        return fetchRes;
                    });
                });
            })
        );
    }
});
