const http = require('http');
const https = require('https');
const PORT = process.env.PORT || 3000;
function fetchPrice(symbol) {
  return new Promise((resolve) => {
    const options = {
      hostname: 'yahoo-finance15.p.rapidapi.com',
      path: `/api/v1/markets/quote?ticker=${encodeURIComponent(symbol)}&type=STOCKS`,
      method: 'GET',
      headers: {
        'x-rapidapi-host': 'yahoo-finance15.p.rapidapi.com',
        'x-rapidapi-key': 'ba9393540amshbc3200b2d733825p16e540jsnd9c3f984b71f'
      }
    };
    https.request(options, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const obj = JSON.parse(data);
          const body = obj.body;
          if (body && body.primaryData) {
            const price = parseFloat(body.primaryData.lastSalePrice.replace(/[^\d.]/g, ''));
            resolve({ price: price });
          } else {
            resolve(null);
          }
        } catch(e) {
          resolve(null);
        }
      });
    }).on('error', () => resolve(null)).end();
  });
}
const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');
  const url = new URL(req.url, `http://${req.headers.host}`);
  const symbols = (url.searchParams.get('symbols') || '').split(',').filter(s => s);
  const results = [];
  for (const sym of symbols) {
    const data = await fetchPrice(sym);
    if (data) {
      results.push({ symbol: sym, regularMarketPrice: data.price, regularMarketChangePercent: 0 });
    }
  }
  res.writeHead(200);
  res.end(JSON.stringify({ quoteResponse: { result: results } }));
});
server.listen(PORT, () => console.log(`Server running on port ${PORT}`));
