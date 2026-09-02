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

messaging.onBackgroundMessage((payload) => {
  const n = payload.notification || payload.data || {};
  const title = n.title || 'AppCartera';
  const body = n.body || '';

  // El tag hace que una notificacion con el mismo titulo+cuerpo REEMPLACE
  // a la anterior en lugar de apilarse. Si el navegador ya pinto una
  // automaticamente (payload con bloque "notification"), esta la sustituye
  // en vez de duplicarla.
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
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((lista) => {
      const tk = (event.notification.data && event.notification.data.tckr) || '';
      for (const c of lista) {
        if (c.url.includes('appcartera') && 'focus' in c) {
          if (tk) c.postMessage({ abrirValor: tk });
          return c.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(tk ? '/?v=' + encodeURIComponent(tk) : '/');
    })
  );
});
