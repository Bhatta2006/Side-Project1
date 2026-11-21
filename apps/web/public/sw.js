/*
 * Socrat service worker: makes the app installable and shows an offline page when a
 * navigation fails. It never caches API responses or learner data, only the offline page
 * and the app icons. Code-runner workers and runtimes keep their own HTTP caching.
 */
const CACHE = 'socrat-shell-v1';
const OFFLINE = '/offline.html';
const PRECACHE = [OFFLINE, '/icons/icon-192.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  if (request.method !== 'GET' || request.mode !== 'navigate') return;
  // Only this site's own pages: a Playground visual is a frame from the sandbox origin, and
  // re-fetching it here falls under the page's connect-src and blocks the visual.
  if (new URL(request.url).origin !== self.location.origin) return;
  event.respondWith(fetch(request).catch(() => caches.match(OFFLINE)));
});
