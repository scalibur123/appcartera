#!/usr/bin/env python3
"""
diana_filtros_completos.py

En la pestana Diana:
1. Quita el bloque historico scrollable (hist-status, d-historico) que no servia
2. Reemplaza los botones por 4 grupos independientes:
   - Estado: Todos / En objetivo / Pendientes
   - Tiempo: Hoy / Semana / Mes
   - Banco:  Todos los bancos
   - Orden:  % dia / Valor
3. Cambia la logica de renderDiana para combinar los 4 filtros
4. Mantiene el calculo de history/semanaSet/mesSet del backend
"""
from pathlib import Path
import re

p = Path.home() / "APPCARTERA_NUEVA" / "index.html"
h = p.read_text(encoding="utf-8")

# ============================================
# 1. Localizar el bloque .filters de Diana y reemplazarlo entero
# ============================================
# El bloque va desde el primer <div class="filters"> que esta dentro de id="diana"
# hasta su cierre. Vamos a buscarlo.

# Buscamos en index.html: <div id="diana" class="section">  ... <div class="filters">  ...  </div>
# Reemplazamos el .filters entero con la nueva estructura

m = re.search(r'(id="diana"[^>]*>\s*<h2[^<]*</h2>\s*)(<div class="filters">.*?</div>)', h, re.DOTALL)
if not m:
    # Probar sin h2
    m = re.search(r'(id="diana"[^>]*>\s*)(<div class="filters">.*?</div>)', h, re.DOTALL)

if m:
    nuevos_filtros = '''<div class="filters" id="d-estado-filters">
    <button class="filter-btn active" id="df-all" onclick="fD('estado','all',this)">Todos</button>
    <button class="filter-btn" id="df-neg" onclick="fD('estado','neg',this)">En objetivo ✓</button>
    <button class="filter-btn" id="df-warn" onclick="fD('estado','warn',this)">Pendientes</button>
  </div>
  <div class="filters" id="d-tiempo-filters">
    <button class="filter-btn active" id="dt-hoy" onclick="fD('tiempo','hoy',this)">HOY</button>
    <button class="filter-btn" id="dt-semana" onclick="fD('tiempo','semana',this)">SEMANA</button>
    <button class="filter-btn" id="dt-mes" onclick="fD('tiempo','mes',this)">MES</button>
  </div>
  <div class="filters" id="d-banco-filters">
    <button class="filter-btn active" id="db-all" onclick="fD('banco','all',this)">Todos</button>
    <button class="filter-btn" id="db-ING" onclick="fD('banco','ING',this)">ING</button>
    <button class="filter-btn" id="db-R4" onclick="fD('banco','R4',this)">R4</button>
    <button class="filter-btn" id="db-IBKR" onclick="fD('banco','IBKR',this)">IBKR</button>
    <button class="filter-btn" id="db-MEDIOLANUM" onclick="fD('banco','MEDIOLANUM',this)">MEDIOLANUM</button>
    <button class="filter-btn" id="db-REVOLUT" onclick="fD('banco','REVOLUT',this)">REVOLUT</button>
    <button class="filter-btn" id="db-MYINV" onclick="fD('banco','MYINV',this)">MYINV</button>
    <button class="filter-btn" id="db-R4/ING" onclick="fD('banco','R4/ING',this)">R4/ING</button>
    <button class="filter-btn" id="db-MEDIO/ING" onclick="fD('banco','MEDIO/ING',this)">MEDIO/ING</button>
  </div>
  <div class="filters" id="d-sort-filters">
    <button class="filter-btn" id="df-sort-pct" onclick="setSortD('pct',this)">↑ % día</button>
    <button class="filter-btn" id="df-sort-val" onclick="setSortD('val',this)">↑ Valor</button>
  </div>'''
    h = h.replace(m.group(2), nuevos_filtros)
    print("OK filtros de Diana reemplazados (4 grupos independientes)")
else:
    print("ERROR no encontre el bloque de filtros de Diana")
    exit(1)

# ============================================
# 2. Quitar hist-status y d-historico (no se usan ahora)
# ============================================
h = re.sub(r'\s*<div id="hist-status"[^>]*></div>\s*', '\n  ', h)
h = re.sub(r'\s*<div id="d-historico"></div>\s*', '\n', h)
print("OK hist-status y d-historico eliminados")

# ============================================
# 3. Cambiar variables: en vez de dFilter unico, usar dEstado/dTiempo/dBanco
# ============================================
old_vars = "let prices={}, names={}, history={}, semanaSet=null, mesSet=null, cFilter='all', dFilter='all', busy=false, cSort=null, dSort=null;"
new_vars = "let prices={}, names={}, history={}, semanaSet=null, mesSet=null, semanaPendSet=null, mesPendSet=null, cFilter='all', dFilter='all', dEstado='all', dTiempo='hoy', dBanco='all', busy=false, cSort=null, dSort=null;"
if old_vars in h:
    h = h.replace(old_vars, new_vars)
    print("OK variables dEstado/dTiempo/dBanco anadidas")
elif "dEstado" in h:
    print("AVISO: variables ya estaban")
else:
    # Probar variante mas flexible
    m = re.search(r"let prices=\{\}[^;]+;", h)
    if m:
        h = h.replace(m.group(0), new_vars)
        print("OK variables actualizadas (variante)")
    else:
        print("ERROR no encontre la linea de variables")
        exit(1)

# ============================================
# 4. Reemplazar funcion fD: ahora acepta (tipo, valor, btn)
# ============================================
old_fd = re.search(r"function fD\([^)]+\)\{[^}]+\}", h)
if old_fd:
    nueva_fd = """function fD(tipo,valor,btn){
  if(tipo==='estado'){dEstado=valor; document.querySelectorAll('#d-estado-filters .filter-btn').forEach(b=>b.classList.remove('active')); btn.classList.add('active');}
  else if(tipo==='tiempo'){dTiempo=valor; document.querySelectorAll('#d-tiempo-filters .filter-btn').forEach(b=>b.classList.remove('active')); btn.classList.add('active');}
  else if(tipo==='banco'){dBanco=valor; document.querySelectorAll('#d-banco-filters .filter-btn').forEach(b=>b.classList.remove('active')); btn.classList.add('active');}
  renderDiana();
}"""
    h = h.replace(old_fd.group(0), nueva_fd)
    print("OK funcion fD reescrita (acepta tipo + valor)")
else:
    print("ERROR no encontre function fD")

# ============================================
# 5. Cambiar goToDiana para que use los nuevos filtros
# ============================================
old_goto = re.search(r"function goToDiana\([^)]+\)\{[^}]+\}", h)
if old_goto:
    nueva_goto = """function goToDiana(f){
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.nav-btn')[2].classList.add('active');
  document.getElementById('diana').classList.add('active');
  // Activar el filtro de estado correspondiente
  document.querySelectorAll('#d-estado-filters .filter-btn').forEach(b=>b.classList.remove('active'));
  const btn = document.getElementById('df-'+f);
  if(btn) btn.classList.add('active');
  dEstado = f;
  renderDiana();
}"""
    h = h.replace(old_goto.group(0), nueva_goto)
    print("OK goToDiana actualizado")

# ============================================
# 6. Calcular tambien los sets de pendientes para semana y mes
# ============================================
old_calc = re.search(r"function calcularPermanencia\(\)\{.*?\n\}", h, re.DOTALL)
if old_calc:
    nueva_calc = """function calcularPermanencia(){
  const hoy = new Date();
  const ano = hoy.getFullYear(), mes = hoy.getMonth();
  const dia = hoy.getDay();
  const offsetLunes = dia === 0 ? -6 : 1 - dia;
  const lunes = new Date(hoy);
  lunes.setDate(hoy.getDate() + offsetLunes);
  lunes.setHours(0,0,0,0);
  const inicioMes = new Date(ano, mes, 1);
  semanaSet = new Set();      // En objetivo al menos un dia esta semana
  mesSet = new Set();         // En objetivo al menos un dia este mes
  semanaPendSet = new Set();  // Pendiente <7% al menos un dia esta semana
  mesPendSet = new Set();     // Pendiente <7% al menos un dia este mes
  for(const item of C){
    if(!item.objetivo) continue;
    const hist = history[item.symbol];
    if(!hist || !hist.length) continue;
    for(const punto of hist){
      const d = new Date(punto.date + 'T00:00:00');
      const enObjetivo = punto.close >= item.objetivo;
      const distancia = (item.objetivo - punto.close) / item.objetivo;
      const pendiente = !enObjetivo && distancia >= 0 && distancia <= 0.07;
      if(d >= lunes){
        if(enObjetivo) semanaSet.add(item.tckr);
        if(pendiente) semanaPendSet.add(item.tckr);
      }
      if(d >= inicioMes){
        if(enObjetivo) mesSet.add(item.tckr);
        if(pendiente) mesPendSet.add(item.tckr);
      }
    }
  }
}"""
    h = h.replace(old_calc.group(0), nueva_calc)
    print("OK calcularPermanencia actualizado (incluye pendientes)")

# ============================================
# 7. Reescribir renderDiana con la logica combinada
# ============================================
# Busca renderDiana hasta la siguiente function
m_rd = re.search(r"function renderDiana\(\)\{.*?(?=\nfunction )", h, re.DOTALL)
if m_rd:
    nueva_render = """function renderDiana(){
  const cont = document.getElementById('d-list');
  if(!cont) return;
  const cnt = document.getElementById('d-count');

  function pasaTiempo(item){
    if(dTiempo==='hoy'){
      const p = prices[item.symbol] && prices[item.symbol].price;
      if(dEstado==='neg') return p!=null && p>=item.objetivo;
      if(dEstado==='warn'){if(!p)return false; const d=(item.objetivo-p)/item.objetivo; return d>=0&&d<=0.07;}
      return true;
    }
    if(dTiempo==='semana'){
      if(!semanaSet || !semanaPendSet) return false;
      if(dEstado==='neg') return semanaSet.has(item.tckr);
      if(dEstado==='warn') return semanaPendSet.has(item.tckr);
      return semanaSet.has(item.tckr) || semanaPendSet.has(item.tckr);
    }
    if(dTiempo==='mes'){
      if(!mesSet || !mesPendSet) return false;
      if(dEstado==='neg') return mesSet.has(item.tckr);
      if(dEstado==='warn') return mesPendSet.has(item.tckr);
      return mesSet.has(item.tckr) || mesPendSet.has(item.tckr);
    }
    return true;
  }

  function pasaBanco(item){
    if(dBanco==='all') return true;
    if(dBanco==='R4/ING') return item.banco==='R4/ING';
    if(dBanco==='MEDIO/ING') return item.banco==='MEDIO/ING';
    if(dBanco==='MEDIOLANUM') return item.banco.toUpperCase().includes('MEDIO');
    return item.banco.toUpperCase().includes(dBanco);
  }

  let data = sortItems(C, dSort).filter(i => i.objetivo).filter(pasaTiempo).filter(pasaBanco);

  if(cnt) cnt.textContent = data.length + ' valores';

  if(!data.length){
    cont.innerHTML = '<div class="empty" style="padding:30px;text-align:center;color:var(--muted)">Sin valores que cumplan los filtros</div>';
    return;
  }

  cont.innerHTML = data.map(item => {
    const p = prices[item.symbol] && prices[item.symbol].price;
    const pc = (prices[item.symbol] && prices[item.symbol].pct) || 0;
    const pcs = (pc>=0?'+':'')+pc.toFixed(2)+'%';
    const pcc = pc>=0?'var(--green)':'var(--red)';
    const ps = p?fN(p):'—';
    const atO = p!=null&&p>=item.objetivo;
    const nearO = p!=null&&!atO&&((item.objetivo-p)/item.objetivo)<=0.07;
    const d = item.objetivo&&p!=null?((p-item.objetivo)/item.objetivo*100):null;
    const ds = d!=null?(d>=0?'+':'')+d.toFixed(2)+'% obj':'—';
    const dc = d!=null&&d>=0?'green':'amber';
    var nombre = '';
    if(typeof getDisplayName === 'function' && getDisplayName(item) !== item.tckr){
      nombre = '<br><span style="font-size:11px;color:var(--muted);font-weight:normal">' + getDisplayName(item) + '</span>';
    }
    return '<div class="list-row"><div class="row-left"><span class="tckr">' + item.tckr + nombre + '</span><span class="banco-pill">' + item.banco + '</span></div><div class="row-right"><span class="price-val ' + (atO?'at-obj':nearO?'near-obj':'normal') + '">' + ps + ' <span style="font-size:10px;color:' + pcc + '">' + pcs + '</span></span>' + (p!=null?'<span class="pill ' + dc + '">' + ds + '</span>':'<span style="font-size:10px;color:var(--muted)">—</span>') + '<span class="price-sub">Obj. ' + fN(item.objetivo) + '</span></div></div>';
  }).join('');
}

"""
    h = h.replace(m_rd.group(0), nueva_render)
    print("OK renderDiana reescrito con filtros combinados")

# ============================================
# 8. Eliminar la funcion renderHistorico antigua si existe
# ============================================
old_rh = re.search(r"function renderHistorico\(\)\{.*?\n\}\n", h, re.DOTALL)
if old_rh:
    h = h.replace(old_rh.group(0), "")
    print("OK renderHistorico antiguo eliminado")

# Eliminar tambien la llamada renderHistorico() dentro de cargarHistorico
h = re.sub(r"renderHistorico\(\);\s*", "renderDiana();\n      ", h)

p.write_text(h, encoding="utf-8")
print("\nOK index.html guardado")
print("\nSiguiente: probar en local con  node server.js")
print("Si va bien:  git add index.html && git commit -m 'feat: Diana con filtros combinados estado/tiempo/banco' && git push")
