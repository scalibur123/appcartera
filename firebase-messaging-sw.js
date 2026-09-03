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
  const destino = tk ? '/?v=' + encodeURIComponent(tk) : '/';

  event.waitUntil((async () => {
    if (tk) await guardarPendiente(tk);

    // iOS congela la pagina al minimizar: avisarla no sirve de nada porque
    // no ejecuta nada al volver. Se fuerza una carga limpia con la direccion,
    // que es el unico camino fiable.
    if (self.clients.openWindow) {
      try { await self.clients.openWindow(destino); return; } catch (e) {}
    }

    // Respaldo: si openWindow no esta disponible, avisar a la ventana viva.
    const lista = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of lista) {
      if (!c.url.includes('appcartera')) continue;
      if ('focus' in c) { try { await c.focus(); } catch (e) {} }
      if (tk) { try { c.postMessage({ abrirValor: tk }); } catch (e) {} }
      return;
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
