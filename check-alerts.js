const { sendNotification } = require('./notifications');
const { supabase } = require('./supabase-client');
const https = require('https');
const fs = require('fs');
const path = require('path');

function getToken() {
  const f = path.join(__dirname, 'fcm-token.txt');
  return fs.existsSync(f) ? fs.readFileSync(f, 'utf8').trim() : null;
}

function getPrevState() {
  const f = path.join(__dirname, 'alert-state.json');
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : {};
}

function saveState(state) {
  fs.writeFileSync(path.join(__dirname, 'alert-state.json'), JSON.stringify(state));
}

function getC() {
  const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
  const m = html.match(/const C=(\[.*?\]);/s);
  return m ? JSON.parse(m[1]) : [];
}

async function fetchPrice(symbol) {
  return new Promise((resolve) => {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}`;
    https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: 8000 }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          const r = JSON.parse(data).chart.result[0];
          resolve(r.meta.regularMarketPrice);
        } catch { resolve(null); }
      });
    }).on('error', () => resolve(null));
  });
}

    async function guardar(ticker, banco, evento, precio, objetivo) {
      await supabase.from('historico_alertas').insert({ticker, banco, evento, precio: parseFloat(precio.toFixed(2)), objetivo: parseFloat(objetivo)});
    }
async function checkAlerts() {
  const token = getToken();
  if (!token) return console.log('No hay token FCM');
  
  const C = getC();
  const prev = getPrevState();
  const next = {};

  for (const item of C) {
    if (!item.objetivo) continue;
    const price = await fetchPrice(item.symbol);
    if (!price) continue;
    
    const enObjetivo = price >= item.objetivo;
    const dist = (item.objetivo - price) / item.objetivo;
    const pendiente = !enObjetivo && dist >= 0 && dist <= 0.07;
    const key = item.symbol + '_' + item.banco;
    
    next[key] = { enObjetivo, pendiente };
    
    if (!prev[key]) continue;
    
    if (enObjetivo && !prev[key].enObjetivo)
      await guardar(item.tckr, item.banco, 'en_objetivo', price, item.objetivo); await sendNotification(token, `🎯 ${item.tckr} en objetivo`, `Precio ${price.toFixed(2)} ≥ Obj ${item.objetivo}`);
    if (!enObjetivo && prev[key].enObjetivo)
      await guardar(item.tckr, item.banco, 'salio_objetivo', price, item.objetivo); await sendNotification(token, `⬇️ ${item.tckr} salió de objetivo`, `Precio ${price.toFixed(2)} < Obj ${item.objetivo}`);
    if (pendiente && !prev[key].pendiente)
      await guardar(item.tckr, item.banco, 'pendiente', price, item.objetivo); await sendNotification(token, `⚠️ ${item.tckr} cerca del objetivo`, `A menos del 7% — Precio ${price.toFixed(2)}`);
    if (!pendiente && prev[key].pendiente && !enObjetivo)
      await guardar(item.tckr, item.banco, 'salio_pendiente', price, item.objetivo); await sendNotification(token, `↩️ ${item.tckr} salió de pendientes`, `Precio ${price.toFixed(2)}`);
  }
  
  saveState(next);
  console.log('✅ Chequeo completado');
}

checkAlerts();
