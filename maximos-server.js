// ── MAXIMOS 52 SEMANAS EN EL SERVIDOR ────────────────────────────────
// Una vez al dia (hora de Madrid) pide a Yahoo el ultimo año de cada valor,
// saca el maximo INTRADIA y su fecha, y lo guarda en Supabase (alert_state,
// key 'maximos') para que sobreviva a los reinicios de Render.
// La app lo pide en /maximos: se responde al momento con lo que haya en
// memoria y, si esta viejo, se recalcula en segundo plano.
const https = require('https');
const fs = require('fs');
const path = require('path');

let cache = null;        // {fecha:'YYYY-MM-DD', calculado:ISO, datos:{symbol:{desde,fecha,valor}}}
let cargado = false;
let enCurso = false;

const hoyMadrid = () => new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Madrid' });

function leerC() {
  try {
    const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
    const m = html.match(/const C=(\[.*?\]);/s);
    return m ? JSON.parse(m[1]) : [];
  } catch (e) { return []; }
}

function pedirAnio(src) {
  return new Promise(resolve => {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(src)}?range=1y&interval=1d`;
    https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: 10000 }, r => {
      if (r.statusCode === 429) { r.resume(); return resolve('THROTTLED'); }
      let d = '';
      r.on('data', c => d += c);
      r.on('end', () => {
        try {
          const x = JSON.parse(d).chart.result[0];
          const gmt = (x.meta && x.meta.gmtoffset) || 0;
          const ts = x.timestamp || [], hi = (x.indicators.quote[0].high) || [];
          let mt = null, mh = null, t0 = null;
          for (let i = 0; i < ts.length; i++) {
            if (hi[i] == null) continue;
            if (t0 === null) t0 = ts[i];
            if (mh === null || hi[i] >= mh) { mh = hi[i]; mt = ts[i]; }   // empate: la mas reciente
          }
          if (mh === null) return resolve(null);
          const f = t => new Date((t + gmt) * 1000).toISOString().slice(0, 10);
          resolve({ desde: f(t0), fecha: f(mt), valor: Math.round(mh * 10000) / 10000 });
        } catch (e) { resolve(null); }
      });
    }).on('error', () => resolve(null)).on('timeout', function () { this.destroy(); resolve(null); });
  });
}

async function cargarDeSupabase() {
  if (cargado) return;
  cargado = true;
  try {
    const { supabase } = require('./supabase-client');
    const { data } = await supabase.from('alert_state').select('value').eq('key', 'maximos').single();
    if (data && data.value && data.value.datos) cache = data.value;
  } catch (e) {}
}

async function guardarEnSupabase() {
  try {
    const { supabase } = require('./supabase-client');
    await supabase.from('alert_state').upsert(
      { key: 'maximos', value: cache, updated_at: new Date().toISOString() }, { onConflict: 'key' });
  } catch (e) { console.log('maximos: no se pudo guardar en Supabase', e.message); }
}

async function refrescar() {
  if (enCurso) return;
  enCurso = true;
  try {
    await cargarDeSupabase();
    const C = leerC();
    if (!C.length) return;
    const hoy = hoyMadrid();
    const datos = Object.assign({}, cache && cache.datos);
    // Todo si el calculo no es de hoy; si es de hoy, solo los valores nuevos.
    const pendientes = C.filter(i => i.symbol && (!cache || cache.fecha !== hoy || !datos[i.symbol]));
    if (!pendientes.length) return;
    let ok = 0, frenado = false;
    for (let i = 0; i < pendientes.length && !frenado; i += 4) {
      const lote = pendientes.slice(i, i + 4);
      const res = await Promise.all(lote.map(it => pedirAnio(it.symbol_px || it.symbol)));
      res.forEach((r, k) => {
        if (r === 'THROTTLED') frenado = true;
        else if (r) { datos[lote[k].symbol] = r; ok++; }
      });
      await new Promise(s => setTimeout(s, 250));
    }
    // Solo se da el dia por hecho si ha salido casi todo; si no, se reintenta en la siguiente hora.
    const completo = !frenado && ok >= pendientes.length * 0.9;
    cache = { fecha: completo ? hoy : ((cache && cache.fecha) || ''), calculado: new Date().toISOString(), datos };
    await guardarEnSupabase();
    console.log(`✅ Maximos 52s: ${ok}/${pendientes.length}${frenado ? ' (Yahoo frena, se reintenta luego)' : ''}`);
  } catch (e) {
    console.log('maximos: error', e.message);
  } finally {
    enCurso = false;
  }
}

async function handleMaximos(req, res) {
  await cargarDeSupabase();
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify(cache || { datos: {} }));
  if (!cache || cache.fecha !== hoyMadrid()) refrescar();   // en segundo plano
}

module.exports = { handleMaximos, refrescar };
