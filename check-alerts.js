const { sendNotification } = require('./notifications');
const { supabase } = require('./supabase-client');
const https = require('https');
const fs = require('fs');
const path = require('path');

const TOKEN_FILE = path.join(__dirname, 'fcm-token.txt');

async function getToken() {
  // 1) Supabase (persiste entre deploys y reinicios de Render)
  try {
    const { data } = await supabase.from('alert_state').select('value').eq('key', 'fcm_token').single();
    if (data && data.value && data.value.token) {
      try { fs.writeFileSync(TOKEN_FILE, data.value.token); } catch (e) {}
      return data.value.token;
    }
  } catch (e) {}
  // 2) Fallback: fichero local (se borra en cada deploy)
  try {
    if (fs.existsSync(TOKEN_FILE)) {
      const t = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
      if (t) return t;
    }
  } catch (e) {}
  return null;
}

async function getStateFromDB(key) {
  const { data, error } = await supabase.from('alert_state').select('value').eq('key', key).single();
  if (error || !data) return null;
  return data.value;
}

async function saveStateToDB(key, value) {
  await supabase.from('alert_state').upsert({ key, value, updated_at: new Date().toISOString() }, { onConflict: 'key' });
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
          const p = r.meta.regularMarketPrice; const prev = r.meta.chartPreviousClose || r.meta.previousClose || p; const pct = prev ? ((p - prev) / prev) * 100 : 0;
          resolve({ price: p, high52: r.meta.fiftyTwoWeekHigh || null, pct });
        } catch { resolve(null); }
      });
    }).on('error', () => resolve(null));
  });
}

async function guardar(ticker, banco, evento, precio, objetivo) {
  await supabase.from('historico_alertas').insert({
    ticker, banco, evento,
    precio: parseFloat(precio.toFixed(2)),
    objetivo: parseFloat(objetivo)
  });
}

async function checkAlerts() {
  const token = await getToken();
  if (!token) return console.log('No hay token FCM');

  const C = getC();
  const hoy = new Date().toISOString().slice(0, 10);

  // Cargar estado previo desde Supabase
  const prev = await getStateFromDB('alert_state') || {};
  const diaRaw = await getStateFromDB('dia_state');
  let dia = (diaRaw && diaRaw.fecha === hoy) ? diaRaw : { fecha: hoy, obj_ent: 0, obj_sal: 0, pen_ent: 0, pen_sal: 0 };

  const next = {};
  const firstRun = Object.keys(prev).length === 0;

  for (const item of C) {
    if (!item.objetivo) continue;
    const result = await fetchPrice(item.symbol);
    const price = result ? result.price : null;
    const high52 = result ? result.high52 : null;
    if (!price) continue;

    const pctDia = result ? result.pct : 0;
    const enObjetivo = price >= item.objetivo;
    const dist = (item.objetivo - price) / item.objetivo;
    const pendiente = !enObjetivo && dist >= 0 && dist <= 0.07;
    const key = item.symbol + '_' + item.banco;

    const yaNotifSubida = prev[key] ? (prev[key].subida5notif || false) : false;
    next[key] = { enObjetivo, pendiente, subida5notif: yaNotifSubida || (pctDia >= 5) };

    if (firstRun) continue;
    if (!prev[key]) continue;

    if (enObjetivo && !prev[key].enObjetivo) {
      dia.obj_ent++;
      await guardar(item.tckr, item.banco, 'en_objetivo', price, item.objetivo);
      await sendNotification(token, `🎯 ${item.tckr} en objetivo`, `Precio ${price.toFixed(2)} ≥ Obj ${item.objetivo}`);
    }
    if (!enObjetivo && prev[key].enObjetivo) {
      dia.obj_sal++;
      await guardar(item.tckr, item.banco, 'salio_objetivo', price, item.objetivo);
      await sendNotification(token, `⬇️ ${item.tckr} salió de objetivo`, `Precio ${price.toFixed(2)} < Obj ${item.objetivo}`);
    }
    const salioAhora = !enObjetivo && prev[key].enObjetivo;
    if (pendiente && !prev[key].pendiente && !salioAhora) {
      dia.pen_ent++;
      await guardar(item.tckr, item.banco, 'pendiente', price, item.objetivo);
      await sendNotification(token, `⚠️ ${item.tckr} cerca del objetivo`, `A menos del 7% — Precio ${price.toFixed(2)}`);
    }
    if (!pendiente && prev[key].pendiente && !enObjetivo) {
      dia.pen_sal++;
      await guardar(item.tckr, item.banco, 'salio_pendiente', price, item.objetivo);
      await sendNotification(token, `↩️ ${item.tckr} salió de pendientes`, `Precio ${price.toFixed(2)}`);
    }

    // Alerta subida >5% en el día (una sola vez)
    if (pctDia >= 5 && !yaNotifSubida) {
      await guardar(item.tckr, item.banco, 'subida_5pct', price, item.objetivo || 0);
      await sendNotification(token, `😊 ${item.tckr} sube +${pctDia.toFixed(1)}% hoy`, `Precio ${price.toFixed(2)} · +${pctDia.toFixed(2)}%`);
      next[key].subida5notif = true;
    }

    // Alerta máximo 52 semanas
    if (high52 && price) {
      const distMax = (high52 - price) / high52;
      const cercaMax = distMax >= 0 && distMax <= 0.03;
      const keyMax = key + '_max52';
      next[keyMax] = { cercaMax };
      if (prev[keyMax] !== undefined && cercaMax && prev[keyMax].cercaMax === false) {
        await guardar(item.tckr, item.banco, 'cerca_max52', price, high52);
        await sendNotification(token, `📈 ${item.tckr} cerca del máximo anual`, `Precio ${price.toFixed(2)} cerca del max 52s: ${high52.toFixed(2)}`);
      }
    }
  }

  await saveStateToDB('alert_state', next);
  await saveStateToDB('dia_state', dia);

  if (firstRun) {
    console.log('✅ Primera ejecución: estado inicial guardado en Supabase, sin notificaciones');
  } else {
    console.log('✅ Chequeo completado');
  }
}

// ── ALERTAS FUERA DE MERCADO ────────────────────────────────────────
// Solo en las franjas donde el movimiento es real: after-hours americano
// (22:00-00:30 en España) y pre-market (11:00-15:30). Fuera de ahí no se
// hace ni una peticion. Una notificacion por valor y dia.
function franjaFuera() {
  const ahora = new Date();
  const min = ahora.getUTCHours() * 60 + ahora.getUTCMinutes();
  // UTC: after 20:00-22:30 · pre 09:00-13:30 (España = UTC+2 en verano)
  if (min >= 1200 && min <= 1350) return 'after';
  if (min >= 540 && min <= 810) return 'pre';
  return null;
}

async function checkFueraMercado() {
  const franja = franjaFuera();
  if (!franja) return;

  const token = await getToken();
  if (!token) return;

  const C = getC().filter(i => !i.symbol.includes('.'));
  if (!C.length) return;

  const hoy = new Date().toISOString().slice(0, 10);
  const prevRaw = await getStateFromDB('fuera_state');
  const prev = (prevRaw && prevRaw.fecha === hoy) ? prevRaw : { fecha: hoy, avisados: [] };
  const avisados = new Set(prev.avisados || []);

  const https2 = require('https');
  function pedir(sim) {
    return new Promise(resolve => {
      const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sim)}`
                + `?interval=5m&range=1d&includePrePost=true`;
      https2.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: 8000 }, r => {
        if (r.statusCode === 429) { r.resume(); return resolve('THROTTLED'); }
        let d = '';
        r.on('data', c => d += c);
        r.on('end', () => {
          try {
            const x = JSON.parse(d).chart.result[0];
            const cierre = x.meta.regularMarketPrice;
            const cl = (x.indicators.quote[0].close || []).filter(v => v != null);
            const ult = cl.length ? cl[cl.length - 1] : null;
            if (!cierre || !ult) return resolve(null);
            resolve({ cierre, fuera: ult, pct: ((ult - cierre) / cierre) * 100 });
          } catch { resolve(null); }
        });
      }).on('error', () => resolve(null));
    });
  }

  let enviadas = 0;
  for (const item of C) {
    if (avisados.has(item.symbol)) continue;
    const r = await pedir(item.symbol);
    if (r === 'THROTTLED') {
      console.log('Yahoo estrangula: se abandona la franja');
      break;                      // insistir nos capa tambien los precios
    }
    if (!r || Math.abs(r.pct) < 3) continue;
    const flecha = r.pct >= 0 ? '🔺' : '🔻';
    const etq = franja === 'after' ? 'after-hours' : 'pre-market';
    await sendNotification(token,
      `${flecha} ${item.tckr} ${r.pct >= 0 ? '+' : ''}${r.pct.toFixed(1)}% ${etq}`,
      `Cierre ${r.cierre.toFixed(2)} → ${r.fuera.toFixed(2)}`);
    avisados.add(item.symbol);
    enviadas++;
    await new Promise(s => setTimeout(s, 300));
  }

  if (enviadas) {
    await saveStateToDB('fuera_state', { fecha: hoy, avisados: [...avisados] });
    console.log(`✅ ${enviadas} alertas fuera de mercado (${franja})`);
  }
}

module.exports = { checkAlerts, checkFueraMercado };

// Permite seguir ejecutándolo a mano: node check-alerts.js
if (require.main === module) {
  checkAlerts();
}
