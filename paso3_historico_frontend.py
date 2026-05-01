#!/usr/bin/env python3
"""
paso3_historico_frontend.py

Anade en index.html un bloque NUEVO al final de Diana con:
  - <div id="hist-status"> para el texto "Actualizando precios historicos..."
  - <div id="d-historico"> donde se renderizan las secciones Semana y Mes

NO toca renderDiana ni d-list. Si las secciones Semana/Mes fallan,
el resto de Diana sigue funcionando.
"""
from pathlib import Path

p = Path.home() / "APPCARTERA_NUEVA" / "index.html"
h = p.read_text(encoding="utf-8")

# 1. Insertar div nuevo justo despues de d-list
target = '<div class="list-card" id="d-list"><div class="empty">Cargando…</div></div>'
nuevo_div = '''<div class="list-card" id="d-list"><div class="empty">Cargando…</div></div>
  <div id="hist-status" style="text-align:center;color:var(--muted);font-size:11px;padding:8px 0"></div>
  <div id="d-historico"></div>'''

if 'id="d-historico"' not in h:
    if target in h:
        h = h.replace(target, nuevo_div)
        print("OK div d-historico anadido despues de d-list")
    else:
        print("ERROR no encontre d-list, abortando")
        exit(1)
else:
    print("AVISO: d-historico ya existe")

# 2. Anadir variables globales
if "history={}" not in h:
    old = "let prices={}, names={},"
    new = "let prices={}, names={}, history={}, semanaSet=null, mesSet=null,"
    if old in h:
        h = h.replace(old, new)
        print("OK variables history/semanaSet/mesSet anadidas")
    else:
        print("ERROR no encontre 'let prices={}, names={},'")
        exit(1)
else:
    print("AVISO: variables history ya existian")

# 3. Anadir funciones antes de </script>
funciones = '''
function cargarHistorico(){
  if(typeof C === 'undefined' || !C.length) return;
  const status = document.getElementById('hist-status');
  if(status) status.textContent = 'Actualizando precios históricos...';
  const symbols = C.map(i => i.symbol).join(',');
  fetch('/history?symbols=' + symbols)
    .then(r => r.json())
    .then(h => {
      history = h;
      calcularPermanencia();
      renderHistorico();
      if(status) status.textContent = '';
    })
    .catch(e => {
      console.error('Error historico:', e);
      if(status) status.textContent = '';
    });
}

function calcularPermanencia(){
  const hoy = new Date();
  const ano = hoy.getFullYear(), mes = hoy.getMonth();
  const dia = hoy.getDay();
  const offsetLunes = dia === 0 ? -6 : 1 - dia;
  const lunes = new Date(hoy);
  lunes.setDate(hoy.getDate() + offsetLunes);
  lunes.setHours(0,0,0,0);
  const inicioMes = new Date(ano, mes, 1);
  semanaSet = new Set();
  mesSet = new Set();
  for(const item of C){
    if(!item.objetivo) continue;
    const hist = history[item.symbol];
    if(!hist || !hist.length) continue;
    let okSemana = true, okMes = true;
    let nSemana = 0, nMes = 0;
    for(const punto of hist){
      const d = new Date(punto.date + 'T00:00:00');
      if(d >= lunes){ nSemana++; if(punto.close < item.objetivo) okSemana = false; }
      if(d >= inicioMes){ nMes++; if(punto.close < item.objetivo) okMes = false; }
    }
    if(okSemana && nSemana > 0) semanaSet.add(item.tckr);
    if(okMes && nMes > 0) mesSet.add(item.tckr);
  }
}

function renderHistorico(){
  const cont = document.getElementById('d-historico');
  if(!cont) return;
  if(!semanaSet || !mesSet){ cont.innerHTML = ''; return; }
  const semana = C.filter(i => semanaSet.has(i.tckr));
  const mes = C.filter(i => mesSet.has(i.tckr));
  function renderItem(item){
    const p = prices[item.symbol] && prices[item.symbol].price;
    const ps = p ? fN(p) : '—';
    const obj = fN(item.objetivo);
    var nombre = '';
    if(typeof getDisplayName === 'function' && getDisplayName(item) !== item.tckr){
      nombre = '<br><span style="font-size:11px;color:var(--muted);font-weight:normal">' + getDisplayName(item) + '</span>';
    }
    return '<div class="list-row"><div class="row-left"><span class="tckr">' + item.tckr + nombre + '</span><span class="banco-pill">' + item.banco + '</span></div><div class="row-right"><span class="price-val at-obj">' + ps + '</span><span class="price-sub">Obj. ' + obj + '</span></div></div>';
  }
  function seccion(titulo, items){
    if(!items.length) return '';
    return '<div style="margin-top:18px;padding:8px 12px;font-size:12px;color:var(--muted);font-weight:600;letter-spacing:.5px;text-transform:uppercase">' + titulo + ' (' + items.length + ')</div>' +
           '<div class="list-card">' + items.map(renderItem).join('') + '</div>';
  }
  cont.innerHTML = seccion('Esta semana', semana) + seccion('Este mes', mes);
}
'''

if "function cargarHistorico" not in h:
    h = h.replace("</script>", funciones + "</script>")
    print("OK funciones cargarHistorico/calcularPermanencia/renderHistorico anadidas")
else:
    print("AVISO: funciones ya existian")

# 4. Disparar cargarHistorico tras cargar precios
target_load = "for(const item of C){if(combined[item.symbol])prices[item.symbol]=combined[item.symbol];}"
if "cargarHistorico()" not in h:
    if target_load in h:
        h = h.replace(target_load, target_load + "\n  setTimeout(cargarHistorico, 500);")
        print("OK cargarHistorico se dispara tras cargar precios")
    else:
        print("ERROR no encontre el bucle de prices, no se dispara cargarHistorico")
else:
    print("AVISO: cargarHistorico ya se dispara")

p.write_text(h, encoding="utf-8")
print("\nOK index.html guardado")
print("\nSiguiente: probar en local con")
print("  cd ~/APPCARTERA_NUEVA && node server.js")
print("  Y abrir http://localhost:3000 en otro Chrome")
print("Si va bien, subir con: actualizar")
