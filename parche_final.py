#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import shutil, datetime, sys

BASE = Path.home() / "APPCARTERA_NUEVA"
IDX  = BASE / "index.html"
SW   = BASE / "firebase-messaging-sw.js"
ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

SW_NUEVO = r"""importScripts('https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js');
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
"""

shutil.copy2(SW, SW.parent / ("firebase-messaging-sw.js.backup_" + ts))
SW.write_text(SW_NUEVO, encoding="utf-8")
print("OK service worker reescrito")

BLOQUE = """function abrirValorDesdeNotif(tckr){
  if(!tckr) return;
  tckr = String(tckr).trim();
  if(window.__notifUlt === tckr && Date.now() - (window.__notifUltT||0) < 5000) return;
  window.__notifUlt = tckr; window.__notifUltT = Date.now();
  const intenta = (n) => {
    const it = C.find(i => i.tckr === tckr);
    if(typeof showDetalle === 'function' && it && prices[it.symbol]){ showDetalle(tckr); return; }
    if(n > 0){ setTimeout(() => intenta(n-1), 500); return; }
    if(typeof goToCartera === 'function') goToCartera(tckr);
  };
  intenta(60);
}
function pedirPendienteAlSW(){
  if(!navigator.serviceWorker) return;
  navigator.serviceWorker.ready.then(reg => {
    const sw = reg.active || navigator.serviceWorker.controller;
    if(!sw) return;
    const ch = new MessageChannel();
    ch.port1.onmessage = e => { if(e.data && e.data.tckr) abrirValorDesdeNotif(e.data.tckr); };
    sw.postMessage({tipo:'pedirPendiente'}, [ch.port2]);
  }).catch(()=>{});
}
(function(){
  const v = new URLSearchParams(location.search).get('v');
  if(v) abrirValorDesdeNotif(v);
  if(navigator.serviceWorker){
    navigator.serviceWorker.addEventListener('message', e => {
      if(e.data && e.data.abrirValor) abrirValorDesdeNotif(e.data.abrirValor);
    });
  }
  const rafaga = () => {
    [0,300,700,1200,2000,3000,4500,6000].forEach(ms => setTimeout(() => {
      if(document.visibilityState === 'visible') pedirPendienteAlSW();
    }, ms));
  };
  rafaga();
  document.addEventListener('visibilitychange', () => {
    if(document.visibilityState === 'visible') rafaga();
  });
  window.addEventListener('pageshow', rafaga);
  window.addEventListener('focus', rafaga);
})();"""

html = IDX.read_text(encoding="utf-8")
i = html.find("function abrirValorDesdeNotif")
if i == -1:
    print("ERROR no encuentro abrirValorDesdeNotif"); sys.exit(1)
j = html.find("})();", i)
if j == -1:
    print("ERROR no encuentro el final del bloque"); sys.exit(1)
j += 5
html = html[:i] + BLOQUE + html[j:]

v1 = "${p.high52 ? (p.price>=p.high52 ? '\U0001F195 Nuevo m\u00e1ximo' : fNum(p.high52)) : '\u2014'}"
n1 = "${p.high52 ? (p.price>=p.high52 ? '\U0001F195 Nuevo m\u00e1ximo '+fNum(Math.max(p.price,p.high52)) : fNum(p.high52)) : '\u2014'}"
if v1 in html:
    html = html.replace(v1, n1, 1)
    print("OK el nuevo maximo ya muestra el importe")
elif n1 in html:
    print("YA estaba el importe del nuevo maximo")

shutil.copy2(IDX, IDX.parent / ("index.html.backup_final_" + ts))
IDX.write_text(html, encoding="utf-8")
print("OK index.html parcheado (pregunta 8 veces en los primeros 6 s)")
print("Backups con sufijo _" + ts)
