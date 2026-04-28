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

function fetchYahoo(symbol, retries = 3) {
  return new Promise((resolve) => {
    const attempt = () => {
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
              if (retries > 0) { setTimeout(attempt, 1000); } else { resolve(null); }
            }
          } catch (e) {
            if (retries > 0) { setTimeout(attempt, 1000); } else { resolve(null); }
          }
        });
      });
      req.on('error', () => {
        if (retries > 0) { setTimeout(attempt, 1000); } else { resolve(null); }
      });
      req.setTimeout(5000, () => { req.destroy(); if (retries > 0) { setTimeout(attempt, 1000); } else { resolve(null); } });
      req.end();
    };
    attempt();
  });
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');
  const url = new URL(req.url, `http://${req.headers.host}`);
  const symbols = (url.searchParams.get('symbols') || '').split(',').filter(s => s);
  const cache = loadCache();
  const results = [];
  for (const sym of symbols) {
    const price = await fetchYahoo(sym);
    if (price && price.price > 0) {
      cache[sym] = { price: price.price, timestamp: Date.now() };
      saveCache(cache);
      results.push({ symbol: sym, regularMarketPrice: price.price, regularMarketChangePercent: 0 });
    } else if (cache[sym]) {
      results.push({ symbol: sym, regularMarketPrice: cache[sym].price, regularMarketChangePercent: 0 });
    }
  }
  res.writeHead(200);
  res.end(JSON.stringify({ quoteResponse: { result: results } }));
});

server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
