#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import shutil, datetime, sys

IDX = Path.home() / "APPCARTERA_NUEVA" / "index.html"
ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

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
    [0,400,1000,2000,3500].forEach(ms => setTimeout(() => {
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

nuevo = html[:i] + BLOQUE + html[j:]
if "dbgbox" in nuevo:
    print("AVISO queda alguna referencia al diagnostico, revisalo")

shutil.copy2(IDX, IDX.parent / ("index.html.backup_limpio_" + ts))
IDX.write_text(nuevo, encoding="utf-8")
print("OK franja de diagnostico eliminada")
print("Backup: index.html.backup_limpio_" + ts)
