// HealthWatch Lightweight Service Worker
const CACHE_NAME = 'healthwatch-app-v2';
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.svg',
  '/icon-512.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch((err) => {
        console.warn('SW pre-cache warning:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map(async (key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
          // Also purge any accidental APK entries in active cache
          try {
            const cache = await caches.open(key);
            const requests = await cache.keys();
            await Promise.all(
              requests
                .filter((req) => req.url.includes('.apk') || req.url.includes('/download/'))
                .map((req) => cache.delete(req))
            );
          } catch (_) {}
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // Pass-through API calls, APK downloads, and non-GET requests straight to network
  // CRITICAL: NEVER intercept or cache Android APK packages in Service Worker CacheStorage!
  if (
    event.request.method !== 'GET' ||
    url.includes('/api/') ||
    url.endsWith('.apk') ||
    url.includes('.apk') ||
    url.includes('/download/') ||
    url.includes('HealthWatch')
  ) {
    return;
  }

  // Network-first with cache fallback for app shell assets
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          if (event.request.mode === 'navigate') {
            return caches.match('/index.html');
          }
          return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
        });
      })
  );
});
