const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const PORT = process.env.PORT || 3000;
const CACHE_FILE = path.join(__dirname, 'price-cache.json');
const POLYGON_KEY = 'EKlEqJSMfkDTjzO9k_Y1qUuUCCpp_ll';
function loadCache() {
  try { return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8')); } catch { return {}; }
}
function saveCache(cache) {
  try { fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2)); } catch (e) { console.error('Error:', e.message); }
}
function tryPolygon(symbol) {
  return new Promise((resolve) => {
    const url = `https://api.polygon.io/v1/last/quote/stocks/${encodeURIComponent(symbol)}?apiKey=${POLYGON_KEY}`;
    https.get(url, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const obj = JSON.parse(data);
          if (obj && obj.results && obj.results.last_quote > 0) {
            resolve(obj.results.last_quote);
          } else {
            resolve(null);
          }
        } catch (e) { resolve(null); }
      });
    }).on('error', () => resolve(null)).setTimeout(5000, function() { this.destroy(); resolve(null); });
  });
}
async function fetchPrice(symbol, cache) {
  const price = await tryPolygon(symbol);
  if (price && price > 0) {
    cache[symbol] = { price: price, timestamp: Date.now() };
    saveCache(cache);
    return price;
  }
  if (cache[symbol]) { return cache[symbol].price; }
  return null;
}
const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');
  const url = new URL(req.url, `http://${req.headers.host}`);
  const symbols = (url.searchParams.get('symbols') || '').split(',').filter(s => s);
  const cache = loadCache();
  const results = [];
  for (const sym of symbols) {
    const price = await fetchPrice(sym, cache);
    if (price) results.push({ symbol: sym, regularMarketPrice: price, regularMarketChangePercent: 0 });
  }
  res.writeHead(200);
  res.end(JSON.stringify({ quoteResponse: { result: results } }));
});
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
