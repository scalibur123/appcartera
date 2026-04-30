const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const CACHE_FILE = path.join(__dirname, 'price-cache.json');

function loadCache() {
  try { return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8')); } catch { return {}; }
}

function saveCache(cache) {
  try { fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2)); } catch (e) { }
}

function fetchYahoo(symbol, retries = 2) {
  return new Promise((resolve) => {
    const attempt = (left) => {
      const options = {
        hostname: 'query1.finance.yahoo.com',
        path: `/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=5d`,
        method: 'GET',
        headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
      };
      const req = https.request(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const d = JSON.parse(data);
            const meta = d?.chart?.result?.[0]?.meta;
            if (meta && meta.regularMarketPrice) {
              resolve({ price: meta.regularMarketPrice, pct: 0 });
            } else {
              if (left > 0) { setTimeout(() => attempt(left - 1), 500); } else { resolve(null); }
            }
          } catch (e) {
            if (left > 0) { setTimeout(() => attempt(left - 1), 500); } else { resolve(null); }
          }
        });
      });
      req.on('error', () => {
        if (left > 0) { setTimeout(() => attempt(left - 1), 500); } else { resolve(null); }
      });
      req.setTimeout(4000, () => { req.destroy(); if (left > 0) { setTimeout(() => attempt(left - 1), 500); } else { resolve(null); } });
      req.end();
    };
    attempt(retries);
  });
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const url = new URL(req.url, `http://${req.headers.host}`);
  const symbolsParam = url.searchParams.get('symbols');

  if (symbolsParam) {
    res.setHeader('Content-Type', 'application/json');
    const symbols = symbolsParam.split(',').filter(s => s);
    const cache = loadCache();

    // Peticiones en PARALELO para evitar timeout
    const fetched = await Promise.all(symbols.map(sym => fetchYahoo(sym)));

    const results = [];
    for (let i = 0; i < symbols.length; i++) {
      const sym = symbols[i];
      const price = fetched[i];
      if (price && price.price > 0) {
        cache[sym] = { price: price.price, timestamp: Date.now() };
        results.push({ symbol: sym, regularMarketPrice: price.price, regularMarketChangePercent: 0 });
      } else if (cache[sym]) {
        results.push({ symbol: sym, regularMarketPrice: cache[sym].price, regularMarketChangePercent: 0 });
      }
    }
    saveCache(cache);
    res.writeHead(200);
    res.end(JSON.stringify({ quoteResponse: { result: results } }));
    return;
  }

  if (url.pathname === '/' || url.pathname === '/index.html') {
    fs.readFile(path.join(__dirname, 'index.html'), 'utf8', (err, data) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Error cargando index.html');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(data);
    });
    return;
  }

  const filePath = path.join(__dirname, url.pathname);
  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const ext = path.extname(filePath).toLowerCase();
    const mimeTypes = {
      '.js': 'application/javascript',
      '.css': 'text/css',
      '.json': 'application/json',
      '.html': 'text/html',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.svg': 'image/svg+xml'
    };
    const contentType = mimeTypes[ext] || 'text/plain';
    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end('Not found');
        return;
      }
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(data);
    });
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
});

server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
