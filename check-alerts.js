const { sendNotification } = require('./notifications');
const { supabase } = require('./supabase-client');
const https = require('https');
const fs = require('fs');
const path = require('path');

function getToken() {
  const f = path.join(__dirname, 'fcm-token.txt');
  return fs.existsSync(f) ? fs.readFileSync(f, 'utf8').trim() : null;
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
          resolve({ price: r.meta.regularMarketPrice, high52: r.meta.fiftyTwoWeekHigh || null });
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
  const token = getToken();
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

    const enObjetivo = price >= item.objetivo;
    const dist = (item.objetivo - price) / item.objetivo;
    const pendiente = !enObjetivo && dist >= 0 && dist <= 0.07;
    const key = item.symbol + '_' + item.banco;

    next[key] = { enObjetivo, pendiente };

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

checkAlerts();
