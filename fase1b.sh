#!/bin/bash
# fase1b.sh - Nombres de tickers desde Yahoo Finance (longName)
#
# Que hace:
#  1. Modifica server.js para anadir endpoint /names que devuelve {ticker: longName}
#  2. Modifica index.html para que tras cargar precios pida los nombres
#     y los muestre en cartera y diana como "TCKR — Nombre"
#  3. Hace UN commit con todo y push
#
# Cero impacto en plusvalia, solo añade displayName a la UI.

set -e
cd ~/APPCARTERA_NUEVA

echo "============================================="
echo "  FASE 1B - Nombres desde Yahoo"
echo "============================================="
echo ""

# Backup
cp server.js server.js.bak_pre_1b
cp index.html index.html.bak_pre_1b
echo "OK Backups creados"

# ============================================================
# 1. Modificar server.js: añadir handleNames y handler /names
# ============================================================
python3 << 'PYEOF'
from pathlib import Path
import re

p = Path.home() / "APPCARTERA_NUEVA" / "server.js"
js = p.read_text(encoding="utf-8")

# 1a. Añadir funcion fetchYahooName antes de "function loadTickerMap"
nueva_funcion = '''
function fetchYahooName(symbol) {
  return new Promise((resolve) => {
    const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(symbol)}`;
    const req = https.get(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' },
      timeout: TIMEOUT
    }, (res) => {
      let data = '';
      res.on('data', (c) => data += c);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          const r = json.quoteResponse && json.quoteResponse.result && json.quoteResponse.result[0];
          if (!r) return resolve({ symbol, name: null });
          const name = r.longName || r.shortName || r.displayName || null;
          resolve({ symbol, name });
        } catch (e) {
          resolve({ symbol, name: null });
        }
      });
    });
    req.on('error', () => resolve({ symbol, name: null }));
    req.on('timeout', () => { req.destroy(); resolve({ symbol, name: null }); });
  });
}

async function fetchNamesBatch(symbols) {
  const results = {};
  const BATCH_NAMES = 50;
  for (let i = 0; i < symbols.length; i += BATCH_NAMES) {
    const slice = symbols.slice(i, i + BATCH_NAMES);
    const batch = await Promise.all(slice.map(fetchYahooName));
    for (const r of batch) {
      if (r.name) results[r.symbol] = r.name;
    }
  }
  return results;
}

async function handleNames(req, res, symbolsParam) {
  const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
  const names = await fetchNamesBatch(symbols);
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(names));
}

'''

# Insertar antes de "function loadTickerMap"
if "fetchYahooName" not in js:
    js = js.replace("function loadTickerMap()", nueva_funcion + "function loadTickerMap()")
    print("OK funciones de nombres anadidas a server.js")
else:
    print("AVISO: fetchYahooName ya existe en server.js")

# 1b. Añadir ruta /names en el router
ruta_names = "    if (pathname === '/names' && symbols) return handleNames(req, res, symbols);\n"
if "/names" not in js:
    # Insertar despues de la linea con /audit
    js = js.replace(
        "    if (pathname === '/audit')",
        ruta_names + "    if (pathname === '/audit')"
    )
    print("OK ruta /names anadida al router")
else:
    print("AVISO: ruta /names ya existe")

p.write_text(js, encoding="utf-8")
print("OK server.js actualizado")
PYEOF

echo ""
# ============================================================
# 2. Modificar index.html
# ============================================================
python3 << 'PYEOF'
from pathlib import Path
import re

p = Path.home() / "APPCARTERA_NUEVA" / "index.html"
html = p.read_text(encoding="utf-8")

# 2a. Anadir variable global names al inicio (justo despues de "let prices=")
if "let names=" not in html:
    html = html.replace(
        "let prices={}",
        "let prices={}, names={}"
    )
    print("OK variable global names anadida")

# 2b. Despues de cargar precios, pedir nombres en background
# Buscamos la zona "for(const item of C){if(combined[item.symbol])prices[item.symbol]=combined[item.symbol];}"
# Y justo despues anadimos la peticion de nombres (no bloquea la UI)

bloque_nombres = '''
  // Cargar nombres de Yahoo en background (no bloquea UI)
  fetch('/names?symbols=' + C.map(i => i.symbol).join(','))
    .then(r => r.json())
    .then(n => { names = n; updateResumen(); renderCartera(); renderDiana(); })
    .catch(e => console.error('Error nombres:', e));

  '''

if "/names?symbols=" not in html:
    # Insertar despues del bucle que rellena prices
    target = "for(const item of C){if(combined[item.symbol])prices[item.symbol]=combined[item.symbol];}"
    if target in html:
        html = html.replace(target, target + bloque_nombres)
        print("OK fetch de nombres anadido tras cargar precios")
    else:
        print("ERROR: no encontre el bucle de prices, no se anade fetch de nombres")
else:
    print("AVISO: fetch /names ya existe")

# 2c. Funcion helper para obtener nombre legible
helper = '''function getDisplayName(item){const n=names[item.symbol];if(n && n.length>0) return n;if(item.nombre && item.nombre!=='#VALUE!') return item.nombre;return item.tckr;}
'''
if "function getDisplayName" not in html:
    # Insertar antes de "function updateResumen"
    html = html.replace(
        "function updateResumen()",
        helper + "function updateResumen()"
    )
    print("OK helper getDisplayName anadido")

p.write_text(html, encoding="utf-8")
print("OK index.html actualizado")

# Verificar
print("\nVerificacion sintaxis JS const C:")
import subprocess
r = subprocess.run(["node", "-e", """
const fs=require('fs');
const html=fs.readFileSync('index.html','utf8');
const m=html.match(/const C=(\\[.*?\\]);/s);
if(m){try{eval('('+m[1]+')');console.log('OK const C parseable');}catch(e){console.log('ERROR:',e.message);process.exit(1);}}else{console.log('NO const C');process.exit(1);}
"""], cwd=str(p.parent), capture_output=True, text=True)
print(r.stdout)
if r.returncode != 0:
    print("ABORTAR: index.html roto")
    print(r.stderr)
    exit(1)
PYEOF

echo ""
echo "OK Cambios aplicados a server.js e index.html"
echo ""
echo "============================================="
echo "Listo para probar."
echo "============================================="
echo ""
echo "Para subir AHORA y verlo en Render:"
echo "   git add -A && git commit -m 'feat: nombres de Yahoo en cartera y diana' && git push"
echo ""
echo "Si rompe algo, rollback:"
echo "   cp server.js.bak_pre_1b server.js && cp index.html.bak_pre_1b index.html"
echo "   git checkout -- server.js index.html"
