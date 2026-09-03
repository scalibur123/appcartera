importScripts('https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyBcOZ_G6bmj1wjkc2f97tgTh9BMi3ws9ZA",
  authDomain: "appcartera123.firebaseapp.com",
  projectId: "appcartera123",
  storageBucket: "appcartera123.firebasestorage.app",
  messagingSenderId: "206685291968",
  appId: "1:206685291968:web:6f2db50f8a7ed0e107f425"
});

const messaging = firebase.messaging();

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

const CACHE_PEND = 'notif-pendiente';
const CLAVE_PEND = '/__notif_pendiente';

async function guardarPendiente(tckr) {
  try {
    const c = await caches.open(CACHE_PEND);
    await c.put(new Request(CLAVE_PEND), new Response(String(tckr || '')));
  } catch (e) {}
}

async function leerPendiente() {
  try {
    const c = await caches.open(CACHE_PEND);
    const r = await c.match(CLAVE_PEND);
    if (!r) return '';
    const t = (await r.text()).trim();
    await c.delete(CLAVE_PEND);
    return t;
  } catch (e) { return ''; }
}

messaging.onBackgroundMessage((payload) => {
  const n = payload.notification || payload.data || {};
  const title = n.title || 'AppCartera';
  const body = n.body || '';
  self.registration.showNotification(title, {
    body,
    icon: '/icon.png',
    tag: title + '|' + body,
    renotify: false,
    data: { tckr: n.tckr || '' }
  });
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const tk = (event.notification.data && event.notification.data.tckr) || '';

  event.waitUntil((async () => {
    if (tk) await guardarPendiente(tk);

    const lista = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    let cli = null;
    for (const c of lista) { if (c.url.includes('appcartera')) { cli = c; break; } }

    if (!cli) {
      if (self.clients.openWindow) {
        await self.clients.openWindow(tk ? '/?v=' + encodeURIComponent(tk) : '/');
      }
      return;
    }

    if ('focus' in cli) { try { await cli.focus(); } catch (e) {} }
    if (!tk) return;

    for (const espera of [0, 400, 1000, 2000]) {
      if (espera) await new Promise(r => setTimeout(r, espera));
      try { cli.postMessage({ abrirValor: tk }); } catch (e) {}
    }
  })());
});

self.addEventListener('message', (event) => {
  const d = event.data || {};
  if (d.tipo !== 'pedirPendiente') return;
  event.waitUntil((async () => {
    const t = await leerPendiente();
    if (event.ports && event.ports[0]) event.ports[0].postMessage({ tckr: t });
  })());
});
