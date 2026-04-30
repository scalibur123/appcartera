#!/usr/bin/env python3
"""
Anade en Cartera: 5 bancos nuevos (MEDIOLANUM, REVOLUT, MYINV, R4/ING, MEDIO/ING)
                  + 2 botones de orden (% dia, Valor)
Anade en Diana: 2 botones de orden (% dia, Valor)
Anade variables cSort/dSort y funciones setSortC/setSortD/sortItems
Aplica el sort en renderCartera y renderDiana
"""
from pathlib import Path
import re

p = Path.home() / "APPCARTERA_NUEVA" / "index.html"
h = p.read_text(encoding="utf-8")

# 1. CARTERA: anadir 5 bancos nuevos despues de IBKR
old_c = '<button class="filter-btn" id="cf-IBKR" onclick="fC(\'IBKR\',this)">IBKR</button>'
new_c = '''<button class="filter-btn" id="cf-IBKR" onclick="fC('IBKR',this)">IBKR</button>
    <button class="filter-btn" id="cf-MEDIOLANUM" onclick="fC('MEDIOLANUM',this)">MEDIOLANUM</button>
    <button class="filter-btn" id="cf-REVOLUT" onclick="fC('REVOLUT',this)">REVOLUT</button>
    <button class="filter-btn" id="cf-MYINV" onclick="fC('MYINV',this)">MYINV</button>
    <button class="filter-btn" id="cf-R4/ING" onclick="fC('R4/ING',this)">R4/ING</button>
    <button class="filter-btn" id="cf-MEDIO/ING" onclick="fC('MEDIO/ING',this)">MEDIO/ING</button>
    <button class="filter-btn" id="cf-sort-pct" onclick="setSortC('pct',this)">↑ % día</button>
    <button class="filter-btn" id="cf-sort-val" onclick="setSortC('val',this)">↑ Valor</button>'''
if old_c in h and 'cf-MEDIOLANUM' not in h:
    h = h.replace(old_c, new_c)
    print("OK cartera: 5 bancos + 2 orden")
else:
    print("AVISO cartera: ya estaban o no encontre")

# 2. DIANA: anadir 2 botones de orden
old_d = '<button class="filter-btn" id="df-MEDIO/ING" onclick="fD(\'MEDIO/ING\',this)">MEDIO/ING</button>'
new_d = '''<button class="filter-btn" id="df-MEDIO/ING" onclick="fD('MEDIO/ING',this)">MEDIO/ING</button>
    <button class="filter-btn" id="df-sort-pct" onclick="setSortD('pct',this)">↑ % día</button>
    <button class="filter-btn" id="df-sort-val" onclick="setSortD('val',this)">↑ Valor</button>'''
if old_d in h and 'df-sort-pct' not in h:
    h = h.replace(old_d, new_d)
    print("OK diana: 2 orden")
else:
    print("AVISO diana: ya estaban o no encontre")

# 3. Variables cSort/dSort
old_vars = "let prices={}, names={}, cFilter='all', dFilter='all', busy=false;"
new_vars = "let prices={}, names={}, cFilter='all', dFilter='all', busy=false, cSort=null, dSort=null;"
if old_vars in h:
    h = h.replace(old_vars, new_vars)
    print("OK variables cSort/dSort")
else:
    print("AVISO variables: ya estaban o no encontre")

# 4. Filtros bancos en logica de Cartera
old_fc_logic = '''  if(cFilter==='ING')return item.banco.toUpperCase().includes('ING');
  if(cFilter==='R4')return item.banco.toUpperCase().includes('R4');
  if(cFilter==='IBKR')return item.banco.toUpperCase().includes('IBKR');'''
new_fc_logic = '''  if(cFilter==='ING')return item.banco.toUpperCase().includes('ING');
  if(cFilter==='R4')return item.banco.toUpperCase().includes('R4');
  if(cFilter==='IBKR')return item.banco.toUpperCase().includes('IBKR');
  if(cFilter==='MEDIOLANUM')return item.banco.toUpperCase().includes('MEDIO');
  if(cFilter==='REVOLUT')return item.banco.toUpperCase().includes('REVOLUT');
  if(cFilter==='MYINV')return item.banco.toUpperCase().includes('MYINV');
  if(cFilter==='R4/ING')return item.banco==='R4/ING';
  if(cFilter==='MEDIO/ING')return item.banco==='MEDIO/ING';'''
if old_fc_logic in h and "cFilter==='MEDIOLANUM'" not in h:
    h = h.replace(old_fc_logic, new_fc_logic)
    print("OK cartera: 5 filtros bancos en logica")
else:
    print("AVISO logica cartera: ya estaba o no encontre")

# 5. Helpers setSortC/setSortD/sortItems antes de </script>
helpers = '''
function setSortC(s,btn){if(cSort===s){cSort=null;btn.classList.remove('active');}else{cSort=s;document.querySelectorAll('[id^="cf-sort-"]').forEach(b=>b.classList.remove('active'));btn.classList.add('active');}renderCartera();}
function setSortD(s,btn){if(dSort===s){dSort=null;btn.classList.remove('active');}else{dSort=s;document.querySelectorAll('[id^="df-sort-"]').forEach(b=>b.classList.remove('active'));btn.classList.add('active');}renderDiana();}
function sortItems(items,sortBy){if(!sortBy)return items;return [...items].sort((a,b)=>{if(sortBy==='pct'){const pa=prices[a.symbol]?.pct||-999;const pb=prices[b.symbol]?.pct||-999;return pb-pa;}if(sortBy==='val'){const va=(prices[a.symbol]?.price||0)*a.titulos;const vb=(prices[b.symbol]?.price||0)*b.titulos;return vb-va;}return 0;});}
'''
if 'function setSortC' not in h:
    h = h.replace('</script>', helpers + '</script>')
    print("OK helpers anadidos antes de </script>")
else:
    print("AVISO helpers ya existian")

# 6. Aplicar sort en renderCartera
m = re.search(r'function renderCartera\(\).*?function ', h, re.DOTALL)
if m and 'sortItems(C,cSort)' not in m.group(0):
    bloque = m.group(0)
    if "let data=C.filter(item=>{" in bloque:
        nuevo = bloque.replace("let data=C.filter(item=>{", "let data=sortItems(C,cSort).filter(item=>{", 1)
        h = h.replace(bloque, nuevo)
        print("OK renderCartera: aplica sort")
    else:
        print("AVISO renderCartera: no encontre 'let data=C.filter'")
else:
    print("AVISO renderCartera: ya tenia sort o no encontre")

# 7. Aplicar sort en renderDiana
m = re.search(r'function renderDiana\(\).*?(?=function )', h, re.DOTALL)
if m and 'sortItems(C,dSort)' not in m.group(0):
    bloque = m.group(0)
    if "let data=C.filter(i=>i.objetivo)" in bloque:
        nuevo = bloque.replace("let data=C.filter(i=>i.objetivo)", "let data=sortItems(C,dSort).filter(i=>i.objetivo)", 1)
        h = h.replace(bloque, nuevo)
        print("OK renderDiana: aplica sort")
    else:
        print("AVISO renderDiana: no encontre 'let data=C.filter(i=>i.objetivo)'")
else:
    print("AVISO renderDiana: ya tenia sort o no encontre")

p.write_text(h, encoding="utf-8")
print("\nOK index.html guardado")
