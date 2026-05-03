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
            changePct: (m.regularMarketChangePercent != null) ? m.regularMarketChangePercent : ((m.regularMarketPrice && m.chartPreviousClose) ? ((m.regularMarketPrice - m.chartPreviousClose) / m.chartPreviousClose) * 100 : 0),
            longName: m.longName || m.shortName || null,
            high52: m.fiftyTwoWeekHigh || null
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
        regularMarketChangePercent: r.changePct,
        longName: r.longName,
        fiftyTwoWeekHigh: r.high52
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
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0' });
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


    if (pathname === "/save-token" && req.method === "POST") {
      let body = "";
      req.on("data", d => body += d);
      req.on("end", () => {
        try {
          const { token } = JSON.parse(body);
          require("fs").writeFileSync("./fcm-token.txt", token);
          res.writeHead(200); res.end("OK");
        } catch(e) { res.writeHead(500); res.end("Error"); }
      });
      return;
    }

    if (pathname === '/get-token' && req.method === 'GET') {
      const fs = require('fs');
      try {
        const token = fs.readFileSync('./fcm-token.txt', 'utf8').trim();
        res.writeHead(200); res.end(token);
      } catch(e) { res.writeHead(404); res.end('No token'); }
      return;
    }

    if (pathname === "/historico" && req.method === "GET") {
      const { supabase } = require("./supabase-client");
      supabase.from("historico_alertas").select("*").order("fecha", {ascending: false}).limit(100).then(({data, error}) => {
        if (error) { res.writeHead(500); res.end(JSON.stringify([])); return; }
        res.writeHead(200, {"Content-Type": "application/json"});
        res.end(JSON.stringify(data || []));
      });
      return;
    }
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

// Chequeo alertas cada 5 min
setInterval(() => { try { require("./check-alerts"); } catch(e) { console.error(e); } }, 5*60*1000);

// Mantener servidor activo
setInterval(() => {
  https.get('https://appcartera.onrender.com', () => {}).on('error', () => {});
}, 14 * 60 * 1000);
