const http = require('http');
const https = require('https');

const PORT = process.env.PORT || 3000;

function fetchYahoo(symbol) {
  return new Promise((resolve) => {
    const options = {
      hostname: 'query1.finance.yahoo.com',
      path: `/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=5d`,
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const d = JSON.parse(data);
          const meta = d?.chart?.result?.[0]?.meta;
          if (!meta) { resolve(null); return; }
          const price = meta.regularMarketPrice;
          const prev = meta.previousClose || price;
          const pct = prev > 0 ? ((price - prev) / prev * 100) : 0;
          resolve({ price, pct });
        } catch(e) { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(10000, () => { req.destroy(); resolve(null); });
    req.end();
  });
}

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');
  
  const url = new URL(req.url, `http://${req.headers.host}`);
  const symbols = url.searchParams.get('symbols')?.split(',') || [];

  const results = [];
  for (const sym of symbols) {
    const data = await fetchYahoo(sym);
    if (data) results.push({ symbol: sym, regularMarketPrice: data.price, regularMarketChangePercent: data.pct });
  }

  res.writeHead(200);
  res.end(JSON.stringify({ quoteResponse: { result: results } }));
});

server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
