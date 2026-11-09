const CACHE = 'damda-v12';
const FONT = 'https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/variable/woff2/PretendardVariable.woff2';
const ASSETS = ['./', './index.html', './manifest.json', './icon.svg', './icon-192.png', './icon-512.png', './icon-maskable-512.png'];

self.addEventListener('install', e => {
  // 폰트는 실패해도 설치는 계속 (오프라인 설치 대비)
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS).then(() => c.add(FONT).catch(() => {}))));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.url.includes('generativelanguage.googleapis.com')) return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: e.request.mode === 'navigate' }).then(r => r || fetch(e.request).then(res => {
      if (res.ok && e.request.method === 'GET' && e.request.mode !== 'navigate') {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return res;
    }))
  );
});
