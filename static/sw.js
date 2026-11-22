const CACHE_NAME = 'gharib-v3';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png'
];

// تثبيت الـ Service Worker وتخزين الملفات الأساسية
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// تفعيل الـ Service Worker وحذف الكاش القديم
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // لا نخزّن طلبات الـ API لنضمن حصولنا على أحدث النتائج
  if (e.request.url.includes('/api/')) {
    return;
  }

  // صفحات HTML: الشبكة أولًا (لتصل التحديثات فورًا)، والكاش عند انقطاع الإنترنت
  const isPage = e.request.mode === 'navigate' ||
                 (e.request.headers.get('accept') || '').includes('text/html');
  if (isPage) {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(e.request, copy));
          return res;
        })
        .catch(() => caches.match(e.request).then((r) => r || caches.match('/')))
    );
    return;
  }

  // باقي الملفات (أيقونات...): الكاش أولًا
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request))
  );
});
