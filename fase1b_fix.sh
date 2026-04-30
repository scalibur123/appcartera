#!/bin/bash
# fase1b_fix.sh - Reescribe server.js completo con nombres + arregla index.html
# Sin parches frágiles. Reescritura limpia.

set -e
cd ~/APPCARTERA_NUEVA

echo "============================================="
echo "  FASE 1B FIX - server.js completo + nombres"
echo "============================================="
echo ""

# Backup
cp server.js server.js.bak_$(date +%Y%m%d_%H%M%S)
echo "OK Backup de server.js"

# 1. Reescribir server.js completo
cat > server.js << 'SERVER_EOF'
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const BATCH = 15;
const TIMEOUT = 8000;

// ============== UTIL ==============

function fetchYahoo(symbol) {
  return new Promise((resolve) => {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}`;
    const req = https.get(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' },
      timeout: TIMEOUT
    }, (res) => {
      let data = '';
      res.on('data', (c) => data += c);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          const r = json.chart && json.chart.result && json.chart.result[0];
          if (!r) return resolve({ symbol, error: 'no_result' });
          const m = r.meta || {};
          resolve({
            symbol: m.symbol || symbol,
            price: m.regularMarketPrice,
            currency: m.currency,
            exchange: m.fullExchangeName || m.exchangeName,
            changePct: m.regularMarketChangePercent || 0
          });
        } catch (e) {
          resolve({ symbol, error: 'parse_error' });
        }
      });
    });
    req.on('error', (e) => resolve({ symbol, error: e.message }));
    req.on('timeout', () => { req.destroy(); resolve({ symbol, error: 'timeout' }); });
  });
}

async function fetchYahooBatch(symbols) {
  const results = [];
  for (let i = 0; i < symbols.length; i += BATCH) {
    const slice = symbols.slice(i, i + BATCH);
    const batchResults = await Promise.all(slice.map(fetchYahoo));
    results.push(...batchResults);
  }
  return results;
}

// ============== NAMES ==============

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

// ============== HANDLERS ==============

async function handleSymbols(req, res, symbolsParam) {
  const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
  const results = await fetchYahooBatch(symbols);
  // Devolver formato compatible con la app: {quoteResponse:{result:[...]}}
  const out = {
    quoteResponse: {
      result: results.filter(r => !r.error).map(r => ({
        symbol: r.symbol,
        regularMarketPrice: r.price,
        regularMarketChangePercent: r.changePct
      }))
    }
  };
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(out));
}

async function handleNames(req, res, symbolsParam) {
  const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
  const names = await fetchNamesBatch(symbols);
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(names));
}

function handleIndex(req, res) {
  const file = path.join(__dirname, 'index.html');
  if (fs.existsSync(file)) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(fs.readFileSync(file));
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('index.html no encontrado');
  }
}

function handleStatic(req, res, urlPath) {
  const safe = urlPath.replace(/\.\./g, '');
  const file = path.join(__dirname, safe);
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
    return;
  }
  const ext = path.extname(file);
  const types = {
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.html': 'text/html',
    '.ico': 'image/x-icon'
  };
  res.writeHead(200, { 'Content-Type': (types[ext] || 'application/octet-stream') + '; charset=utf-8' });
  res.end(fs.readFileSync(file));
}

// ============== ROUTER ==============

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const pathname = url.pathname;
    const symbols = url.searchParams.get('symbols');

    console.log(new Date().toISOString(), req.method, pathname);

    if (pathname === '/names' && symbols) return handleNames(req, res, symbols);
    if (pathname === '/' && symbols) return handleSymbols(req, res, symbols);
    if (pathname === '/' || pathname === '/index.html') return handleIndex(req, res);

    return handleStatic(req, res, pathname);
  } catch (e) {
    console.error('ERROR:', e);
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    res.end('Error: ' + e.message);
  }
});

server.listen(PORT, () => {
  console.log(`AppCartera escuchando en puerto ${PORT}`);
});
SERVER_EOF
echo "OK server.js reescrito (limpio, con /names)"
echo ""

# 2. Verificar que index.html tiene la variable names global
python3 << 'PYEOF'
from pathlib import Path
import re

p = Path.home() / "APPCARTERA_NUEVA" / "index.html"
html = p.read_text(encoding="utf-8")

# Buscar declaracion existente
m = re.search(r"let prices=\{\}[^;]*;", html)
if m:
    actual = m.group(0)
    print(f"Actual: {actual}")
    if "names" not in actual:
        nuevo = "let prices={}, names={}, cFilter='all', dFilter='all', busy=false;"
        # Reemplazar la linea entera let prices=... hasta ;
        html = re.sub(r"let prices=\{\}[^;]*;", nuevo, html, count=1)
        p.write_text(html, encoding="utf-8")
        print("OK variable names anadida")
    else:
        print("OK variable names ya existe")
else:
    print("ERROR: no encontre declaracion de let prices")
PYEOF
echo ""

# 3. Verificar el fetch de names
python3 << 'PYEOF'
from pathlib import Path
p = Path.home() / "APPCARTERA_NUEVA" / "index.html"
html = p.read_text(encoding="utf-8")
if "/names?symbols=" in html:
    print("OK fetch /names ya esta en el frontend")
else:
    # Buscar el bucle prices y anadir despues
    target = "for(const item of C){if(combined[item.symbol])prices[item.symbol]=combined[item.symbol];}"
    bloque = '''
  // Cargar nombres de Yahoo en background
  fetch('/names?symbols=' + C.map(i => i.symbol).join(','))
    .then(r => r.json())
    .then(n => { names = n; updateResumen(); renderCartera(); renderDiana(); })
    .catch(e => console.error('Error nombres:', e));
'''
    if target in html:
        html = html.replace(target, target + bloque)
        p.write_text(html, encoding="utf-8")
        print("OK fetch /names anadido")
    else:
        print("AVISO: no encontre el bucle prices target. Verifica manualmente.")
PYEOF
echo ""

# 4. Validar JS const C
node -e "
const fs = require('fs');
const html = fs.readFileSync('index.html', 'utf8');
const m = html.match(/const C=(\[.*?\]);/s);
if (m) {
  try {
    const C = eval('(' + m[1] + ')');
    console.log('OK const C parseable,', C.length, 'items');
  } catch (e) {
    console.log('ERROR:', e.message);
    process.exit(1);
  }
} else {
  console.log('ERROR: no const C');
  process.exit(1);
}
"
echo ""

# 5. Probar localmente que server.js arranca sin errores
node -e "require('./server.js')" 2>&1 &
NODEPID=$!
sleep 2
kill $NODEPID 2>/dev/null || true
echo "OK server.js sin errores de sintaxis"
echo ""

echo "============================================="
echo "Listo. Para subir:"
echo "  git add -A && git commit -m 'fix: server.js limpio + endpoint /names funcionando' && git push"
echo "============================================="
