#!/usr/bin/env python3
"""
Parche para index.html de AppCartera:
1. Añade petición de EURUSD=X al cargar precios
2. Muestra el cambio EUR/USD bajo el título
3. Convierte USD->EUR en updateResumen
4. Convierte USD->EUR en renderCartera
"""
import os, re, shutil
from datetime import datetime

INDEX = os.path.expanduser("~/APPCARTERA_NUEVA/index.html")

# Backup primero
backup = INDEX + ".backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy(INDEX, backup)
print(f"Backup creado: {backup}")

with open(INDEX, 'r') as f:
    html = f.read()

cambios = 0

# ==============================================
# CAMBIO 1: updateResumen - convertir USD->EUR
# ==============================================
old1 = "for(const i of C){const p=prices[i.tckr];if(p)b+=i.titulos*p.price-i.coste_eur;}"
new1 = "for(const i of C){const p=prices[i.tckr];if(p){const pe=i.moneda==='USD'&&eurUsd?p.price/eurUsd:p.price;b+=i.titulos*pe-i.coste_eur;}}"

if old1 in html:
    html = html.replace(old1, new1)
    cambios += 1
    print("OK 1/4: updateResumen actualizado (conversion USD->EUR)")
else:
    print("AVISO 1/4: No se encontro la linea de updateResumen (puede que ya este parcheada)")

# ==============================================
# CAMBIO 2: renderCartera - convertir USD->EUR en plusvalia individual
# ==============================================
old2 = "if(p){const pm=item.titulos*p.price-item.coste_eur;pms=(pm>=0?'+':'')+fE(pm);pmc=pm>=0?'pos':'loss';}"
new2 = "if(p){const pe=item.moneda==='USD'&&eurUsd?p.price/eurUsd:p.price;const pm=item.titulos*pe-item.coste_eur;pms=(pm>=0?'+':'')+fE(pm);pmc=pm>=0?'pos':'loss';}"

if old2 in html:
    html = html.replace(old2, new2)
    cambios += 1
    print("OK 2/4: renderCartera actualizado (conversion USD->EUR)")
else:
    print("AVISO 2/4: No se encontro la linea de renderCartera")

# ==============================================
# CAMBIO 3: declaracion variable eurUsd al principio del script
# ==============================================
# La metemos justo despues de "let busy=false;" o similar
patron_decl = re.search(r"(let\s+busy\s*=\s*false\s*[,;])", html)
if patron_decl and "let eurUsd" not in html and "var eurUsd" not in html:
    insert_point = patron_decl.end()
    html = html[:insert_point] + "let eurUsd=null;" + html[insert_point:]
    cambios += 1
    print("OK 3/4: Variable eurUsd declarada")
elif "let eurUsd" in html or "var eurUsd" in html:
    print("INFO 3/4: Variable eurUsd ya estaba declarada")
    cambios += 1
else:
    # Plan B: la metemos antes de "function yT"
    if "function yT(" in html and "let eurUsd" not in html:
        html = html.replace("function yT(", "let eurUsd=null;\nfunction yT(", 1)
        cambios += 1
        print("OK 3/4: Variable eurUsd declarada (plan B)")
    else:
        print("AVISO 3/4: No se pudo declarar eurUsd automaticamente")

# ==============================================
# CAMBIO 4: pedir EURUSD=X al cargar precios
# ==============================================
# Buscamos el bucle "for(let i=0;i<allY.length;i+=BATCH){" y antes de el pedimos el cambio
old4 = "const allY=C.map(yT);"
new4 = """const allY=C.map(yT);
  // Pedir cambio EUR/USD
  try{
    const fxRes=await fetchBatch(['EURUSD=X']);
    if(fxRes && fxRes['EURUSD=X']){
      eurUsd=fxRes['EURUSD=X'].price;
      const fxEl=document.getElementById('eurusd-display');
      if(fxEl) fxEl.textContent='Cambio EUR/USD: '+eurUsd.toFixed(4);
    }
  }catch(e){console.error('Error EURUSD',e);}"""

if old4 in html and "fetchBatch(['EURUSD=X'])" not in html:
    html = html.replace(old4, new4)
    cambios += 1
    print("OK 4/4: Peticion EURUSD=X anadida")
elif "fetchBatch(['EURUSD=X'])" in html:
    print("INFO 4/4: Peticion EURUSD=X ya estaba")
    cambios += 1
else:
    print("AVISO 4/4: No se encontro 'const allY=C.map(yT);'")

# ==============================================
# CAMBIO 5: anadir el div del cambio bajo el titulo
# ==============================================
# Lo metemos despues del primer status-bar o donde haya "30/196"
# Buscamos un sitio razonable: despues de "id=\"status-text\"" o similar
if 'id="eurusd-display"' not in html:
    # Buscamos el span del status y metemos el div justo despues del contenedor padre
    # Estrategia simple: insertar antes del primer <div class="tabs"> o <div id="resumen">
    patron_tabs = re.search(r'(<div[^>]*(class="nav-tabs"|class="tabs"|id="resumen"))', html)
    if patron_tabs:
        insert_at = patron_tabs.start()
        div_html = '<div id="eurusd-display" style="text-align:center;padding:6px 0;font-size:11px;color:var(--muted)">Cambio EUR/USD: --</div>'
        html = html[:insert_at] + div_html + html[insert_at:]
        cambios += 1
        print("OK 5/5: Div del cambio EUR/USD anadido al HTML")
    else:
        print("AVISO 5/5: No se encontro punto de insercion para div EUR/USD")
else:
    print("INFO 5/5: Div EUR/USD ya existia")
    cambios += 1

# ==============================================
# Guardar
# ==============================================
if cambios > 0:
    with open(INDEX, 'w') as f:
        f.write(html)
    print(f"\n{cambios} cambios aplicados. index.html actualizado.")
    print(f"Si algo falla, restaura con: cp {backup} {INDEX}")
else:
    print("\nNo se aplico ningun cambio.")
