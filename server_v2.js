// server_v2.js - Backend con endpoint /audit
// Cambios vs server.js original:
//   - Mantiene servir index.html en /
//   - Mantiene proxy a Yahoo en /?symbols=...
//   - NUEVO: GET /audit -> devuelve JSON comparando precio_excel vs precio_yahoo
//   - NUEVO: GET /audit.html -> pagina visual con tabla ordenada por desviacion

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
            exchange: m.fullExchangeName || m.exchangeName
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

function loadTickerMap() {
  const p = path.join(__dirname, 'tickers.json');
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch (e) {
    return null;
  }
}

// ============== HANDLERS ==============

async function handleAudit(req, res) {
  const tickerMap = loadTickerMap();
  if (!tickerMap) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'tickers.json no encontrado. Ejecuta update_from_excel_v2.py' }));
    return;
  }

  const symbols = Object.values(tickerMap).map(v => v.yahoo);
  const yahooResults = await fetchYahooBatch(symbols);
  const yahooBySymbol = Object.fromEntries(yahooResults.map(r => [r.symbol, r]));

  // Buscar EUR/USD
  const fxData = await fetchYahoo('EURUSD=X');
  const eurusd = (fxData && fxData.price) || 1.17;

  const audit = [];
  for (const [ticker, info] of Object.entries(tickerMap)) {
    const sym = info.yahoo;
    const y = yahooBySymbol[sym] || yahooResults.find(r => r.symbol && r.symbol.toUpperCase() === sym.toUpperCase());
    const precioExcel = info.precio_excel;
    const precioYahoo = y && !y.error ? y.price : null;
    let desviacionPct = null;
    let estado = 'sin_precio';

    if (precioExcel != null && precioYahoo != null && precioExcel !== 0) {
      desviacionPct = Math.abs(precioYahoo - precioExcel) / precioExcel * 100;
      if (desviacionPct < 5) estado = 'ok';
      else if (desviacionPct < 15) estado = 'sospechoso';
      else estado = 'critico';
    } else if (y && y.error) {
      estado = 'error_yahoo';
    }

    // Impacto economico (sesgo de la app vs Excel)
    let impactoEur = 0;
    if (precioExcel != null && precioYahoo != null) {
      impactoEur = (precioYahoo - precioExcel) * info.titulos;
      if (info.moneda === 'USD') impactoEur /= eurusd;
    }

    audit.push({
      ticker,
      yahoo: sym,
      moneda: info.moneda,
      titulos: info.titulos,
      coste_eur: info.coste_eur,
      precio_excel: precioExcel,
      precio_yahoo: precioYahoo,
      desviacion_pct: desviacionPct,
      impacto_eur: impactoEur,
      estado,
      fuente: info.fuente_resolucion,
      exchange_yahoo: y ? y.exchange : null,
      currency_yahoo: y ? y.currency : null,
      error: y ? y.error : null
    });
  }

  // Ordenar por desviacion descendente, nulls al final
  audit.sort((a, b) => {
    if (a.desviacion_pct == null) return 1;
    if (b.desviacion_pct == null) return -1;
    return b.desviacion_pct - a.desviacion_pct;
  });

  const totalImpacto = audit.reduce((s, x) => s + (x.impacto_eur || 0), 0);
  const stats = {
    total: audit.length,
    ok: audit.filter(x => x.estado === 'ok').length,
    sospechoso: audit.filter(x => x.estado === 'sospechoso').length,
    critico: audit.filter(x => x.estado === 'critico').length,
    sin_precio: audit.filter(x => x.estado === 'sin_precio').length,
    error_yahoo: audit.filter(x => x.estado === 'error_yahoo').length,
    eurusd_actual: eurusd,
    impacto_total_eur: totalImpacto
  };

  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify({ stats, audit }, null, 2));
}

function handleAuditHtml(req, res) {
  const file = path.join(__dirname, 'audit.html');
  if (fs.existsSync(file)) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(fs.readFileSync(file));
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('audit.html no encontrado');
  }
}

async function handleSymbols(req, res, symbolsParam) {
  const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
  const results = await fetchYahooBatch(symbols);
  const out = {};
  for (const r of results) {
    if (r.symbol && !r.error) out[r.symbol] = { price: r.price, currency: r.currency };
    else if (r.symbol) out[r.symbol] = { error: r.error };
  }
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(out));
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
  // Servir archivos estaticos seguros (notifications.js, etc)
  const safe = urlPath.replace(/\.\./g, '');
  const file = path.join(__dirname, safe);
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
    return;
  }
  const ext = path.extname(file);
  const types = { '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.html': 'text/html', '.ico': 'image/x-icon' };
  res.writeHead(200, { 'Content-Type': (types[ext] || 'application/octet-stream') + '; charset=utf-8' });
  res.end(fs.readFileSync(file));
}

// ============== ROUTER ==============

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const pathname = url.pathname;
    const symbols = url.searchParams.get('symbols');

    // Logging minimo
    console.log(new Date().toISOString(), req.method, pathname);

    if (pathname === '/' && symbols) return handleSymbols(req, res, symbols);
    if (pathname === '/' || pathname === '/index.html') return handleIndex(req, res);
    if (pathname === '/audit') return handleAudit(req, res);
    if (pathname === '/audit.html') return handleAuditHtml(req, res);

    return handleStatic(req, res, pathname);
  } catch (e) {
    console.error('ERROR:', e);
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    res.end('Error: ' + e.message);
  }
});

server.listen(PORT, () => {
  console.log(`AppCartera v2 escuchando en puerto ${PORT}`);
  console.log(`  /          -> index.html`);
  console.log(`  /?symbols= -> proxy Yahoo`);
  console.log(`  /audit     -> JSON auditoria precios`);
  console.log(`  /audit.html-> pagina visual`);
});
