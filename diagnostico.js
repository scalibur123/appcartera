const fs = require('fs'), path = require('path');
const BASE = '/Users/mabascal/APPCARTERA_NUEVA';

// Cargar .env
fs.readFileSync(path.join(BASE, '.env'), 'utf8').split('\n').forEach(l => {
  const i = l.indexOf('=');
  if (i > 0) process.env[l.slice(0, i).trim()] = l.slice(i + 1).trim();
});

const https = require('https');
const { createClient } = require('@supabase/supabase-js');
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

// Verificar const C
const html = fs.readFileSync(path.join(BASE, 'index.html'), 'utf8');
const m = html.match(/const C=(\[.*?\]);/s);
if (!m) { console.log('ERROR: NO SE ENCONTRO const C'); process.exit(); }
const C = JSON.parse(m[1]);
console.log('Tickers encontrados:', C.length);
console.log('Primeros 3:', C.slice(0, 3).map(x => x.tckr + ' / ' + x.symbol));

// Verificar price-cache.json
try {
  const cache = JSON.parse(fs.readFileSync(path.join(BASE, 'price-cache.json'), 'utf8'));
  console.log('price-cache.json OK, entradas:', Object.keys(cache).length);
} catch(e) {
  console.log('ERROR leyendo price-cache.json:', e.message);
}

// Probar Finnhub con primer ticker
const ticker = C[0];
const cleanSymbol = ticker.symbol.replace(/\.[A-Z]+$/, '');
const apikey = process.env.FINNHUB_KEY || 'd84nlnpr01qutij9ijr0d84nlnpr01qutij9ijrg';
const url = `https://finnhub.io/api/v1/stock/price-target?symbol=${encodeURIComponent(cleanSymbol)}&token=${apikey}`;
console.log('Probando Finnhub con:', cleanSymbol, '→', url);

https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
  let data = '';
  res.on('data', c => data += c);
  res.on('end', () => {
    console.log('Respuesta Finnhub:', data.slice(0, 300));
    process.exit();
  });
}).on('error', e => { console.log('Error Finnhub:', e.message); process.exit(); });
