const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const BATCH = 15;
const TIMEOUT = 8000;

// ============== UTIL ==============

function fetchYahoo(symbol) {
  return new Promise((resolve) => {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}`;
    const req = https.get(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' },
      timeout: TIMEOUT
    }, (res) => {
      let data = '';
      res.on('data', (c) => data += c);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          const r = json.chart && json.chart.result && json.chart.result[0];
          if (!r) return resolve({ symbol, error: 'no_result' });
          const m = r.meta || {};
          resolve({
            symbol: m.symbol || symbol,
            price: m.regularMarketPrice,
            currency: m.currency,
            exchange: m.fullExchangeName || m.exchangeName,
            changePct: (m.regularMarketChangePercent != null) ? m.regularMarketChangePercent : ((m.regularMarketPrice && m.chartPreviousClose) ? ((m.regularMarketPrice - m.chartPreviousClose) / m.chartPreviousClose) * 100 : 0),
            longName: m.longName || m.shortName || null,
            high52: m.fiftyTwoWeekHigh || null
          });
        } catch (e) {
          resolve({ symbol, error: 'parse_error' });
        }
      });
    });
    req.on('error', (e) => resolve({ symbol, error: e.message }));
    req.on('timeout', () => { req.destroy(); resolve({ symbol, error: 'timeout' }); });
  });
}

async function fetchYahooBatch(symbols) {
  const results = [];
  for (let i = 0; i < symbols.length; i += BATCH) {
    const slice = symbols.slice(i, i + BATCH);
    const batchResults = await Promise.all(slice.map(fetchYahoo));
    results.push(...batchResults);
  }
  // Segundo intento para los que han fallado o han venido sin precio. Un
  // timeout suelto dejaba la posicion sin cotizar y la app la contaba como 0.
  const fallidos = results.filter(r => r.error || r.price == null).map(r => r.symbol);
  if (fallidos.length) {
    console.log('Reintentando sin precio:', fallidos.join(', '));
    await new Promise(r => setTimeout(r, 600));
    const retry = await Promise.all(fallidos.map(fetchYahoo));
    for (const r of retry) {
      if (r.error || r.price == null) continue;
      const idx = results.findIndex(x => x.symbol === r.symbol);
      if (idx >= 0) results[idx] = r;
    }
  }
  return results;
}

// ============== NAMES ==============

function fetchYahooName(symbol) {
  return new Promise((resolve) => {
    const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(symbol)}`;
    const req = https.get(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' },
      timeout: TIMEOUT
    }, (res) => {
      let data = '';
      res.on('data', (c) => data += c);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          const r = json.quoteResponse && json.quoteResponse.result && json.quoteResponse.result[0];
          if (!r) return resolve({ symbol, name: null });
          const name = r.longName || r.shortName || r.displayName || null;
          resolve({ symbol, name });
        } catch (e) {
          resolve({ symbol, name: null });
        }
      });
    });
    req.on('error', () => resolve({ symbol, name: null }));
    req.on('timeout', () => { req.destroy(); resolve({ symbol, name: null }); });
  });
}

async function fetchNamesBatch(symbols) {
  const results = {};
  const BATCH_NAMES = 50;
  for (let i = 0; i < symbols.length; i += BATCH_NAMES) {
    const slice = symbols.slice(i, i + BATCH_NAMES);
    const batch = await Promise.all(slice.map(fetchYahooName));
    for (const r of batch) {
      if (r.name) results[r.symbol] = r.name;
    }
  }
  return results;
}

// ============== HANDLERS ==============

// ── FUERA DE MERCADO (pre-market y after-hours) ─────────────────────
// interval=5m es la clave: da el mismo precio que 1m con una quinta parte
// de las velas. Con 1d no llega el dato fuera de sesion.
function fetchFuera(symbol) {
  return new Promise((resolve) => {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}`
              + `?interval=5m&range=1d&includePrePost=true`;
    const req = https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: TIMEOUT }, (res2) => {
      let data = '';
      res2.on('data', c => data += c);
      res2.on('end', () => {
        if (res2.statusCode === 429) return resolve({ symbol, error: 'throttled' });
        try {
          const r = JSON.parse(data).chart.result[0];
          const m = r.meta || {};
          const cierre = m.regularMarketPrice;
          const cl = (r.indicators.quote[0].close || []).filter(x => x != null);
          const ultimo = cl.length ? cl[cl.length - 1] : null;
          if (!cierre || !ultimo) return resolve({ symbol, error: 'sin_datos' });
          resolve({
            symbol, cierre, fuera: ultimo,
            pct: ((ultimo - cierre) / cierre) * 100,
            longName: m.longName || m.shortName || null
          });
        } catch { resolve({ symbol, error: 'parse' }); }
      });
    });
    req.on('error', () => resolve({ symbol, error: 'red' }));
    req.on('timeout', () => { req.destroy(); resolve({ symbol, error: 'timeout' }); });
  });
}

// Buscador de valores por nombre o ticker. Va por el servidor porque el
// navegador no puede llamar a Yahoo directamente (CORS).
function handleBuscar(req, res, q) {
  const url = `https://query2.finance.yahoo.com/v1/finance/search`
            + `?q=${encodeURIComponent(q)}&quotesCount=15&newsCount=0`;
  https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: TIMEOUT }, (r) => {
    let d = '';
    r.on('data', c => d += c);
    r.on('end', () => {
      let out = [];
      try {
        const q2 = (JSON.parse(d).quotes || []);
        out = q2.filter(x => x.symbol && (x.quoteType === 'EQUITY' || x.quoteType === 'ETF'))
                .map(x => ({ symbol: x.symbol, nombre: x.longname || x.shortname || '',
                             bolsa: x.exchDisp || x.exchange || '', tipo: x.quoteType }));
      } catch {}
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ result: out }));
    });
  }).on('error', () => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ result: [], error: 'red' }));
  });
}

async function handleFuera(req, res, symbolsParam) {
  const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
  const out = [];
  let cortado = false;
  for (let i = 0; i < symbols.length && !cortado; i += BATCH) {
    const slice = symbols.slice(i, i + BATCH);
    const r = await Promise.all(slice.map(fetchFuera));
    // Si Yahoo estrangula, se abandona: insistir nos deja capados tambien
    // para las cotizaciones normales, que son lo que no puede fallar.
    if (r.some(x => x.error === 'throttled')) { cortado = true; }
    out.push(...r.filter(x => !x.error));
  }
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ result: out, throttled: cortado }));
}

async function handleSymbols(req, res, symbolsParam) {
  const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
  const results = await fetchYahooBatch(symbols);
  const out = {
    quoteResponse: {
      result: results.filter(r => !r.error).map(r => ({
        symbol: r.symbol,
        regularMarketPrice: r.price,
        regularMarketChangePercent: r.changePct,
        longName: r.longName,
        fiftyTwoWeekHigh: r.high52
      }))
    }
  };
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(out));
}

async function handleNames(req, res, symbolsParam) {
  const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
  const names = await fetchNamesBatch(symbols);
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(names));
}

function handleIndex(req, res) {
  const file = path.join(__dirname, 'index.html');
  if (fs.existsSync(file)) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0' });
    res.end(fs.readFileSync(file));
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('index.html no encontrado');
  }
}

function handleStatic(req, res, urlPath) {
  const safe = urlPath.replace(/\.\./g, '');
  const file = path.join(__dirname, safe);
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
    return;
  }
  const ext = path.extname(file);
  const types = {
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.html': 'text/html',
    '.ico': 'image/x-icon'
  };
  res.writeHead(200, { 'Content-Type': (types[ext] || 'application/octet-stream') + '; charset=utf-8' });
  res.end(fs.readFileSync(file));
}

// ============== VARIACIONES DIARIAS ==============

async function guardarVariacionDiaria(fecha, valorHoy) {
  try {
    const { supabase } = require('./supabase-client');
    // Obtener snapshot del día laboral anterior
    const { data } = await supabase
      .from('cartera_snapshots')
      .select('fecha,valor_total')
      .lt('fecha', fecha)
      .order('fecha', { ascending: false })
      .limit(1);
    if (!data || !data[0]) {
      console.log('variacion-diaria: no hay snapshot anterior para', fecha);
      return;
    }
    const valorAyer = data[0].valor_total;
    const variacion = Math.round((valorHoy - valorAyer) * 100) / 100;
    await supabase
      .from('variaciones_diarias')
      .upsert({ fecha, valor: variacion }, { onConflict: 'fecha' });
    console.log(`✅ Variación diaria guardada: ${fecha} = ${variacion.toFixed(2)}`);
  } catch (e) {
    console.error('Error guardarVariacionDiaria:', e.message);
  }
}

// ============== ROUTER ==============

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const pathname = url.pathname;
    // La app multiusuario se sirve desde otro origen y necesita llamar aqui.
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
    const symbols = url.searchParams.get('symbols');

    console.log(new Date().toISOString(), req.method, pathname);

    if (pathname === "/save-token" && req.method === "POST") {
      let body = "";
      req.on("data", d => body += d);
      req.on("end", async () => {
        try {
          const { token } = JSON.parse(body);
          if (!token) { res.writeHead(400); res.end("Sin token"); return; }
          // Cache local (se pierde en cada deploy) + persistencia en Supabase
          try { fs.writeFileSync(path.join(__dirname, "fcm-token.txt"), token); } catch(e) {}
          const { supabase } = require("./supabase-client");
          await supabase.from("alert_state").upsert({
            key: "fcm_token",
            value: { token, updated_at: new Date().toISOString() },
            updated_at: new Date().toISOString()
          }, { onConflict: "key" });
          console.log("Token FCM guardado en Supabase");
          res.writeHead(200); res.end("OK");
        } catch(e) { console.error("Error save-token:", e.message); res.writeHead(500); res.end("Error"); }
      });
      return;
    }

    if (pathname === '/get-token' && req.method === 'GET') {
      try {
        const { supabase } = require('./supabase-client');
        const { data } = await supabase.from('alert_state').select('value').eq('key', 'fcm_token').single();
        if (data && data.value && data.value.token) {
          res.writeHead(200); res.end(data.value.token);
          return;
        }
      } catch(e) {}
      try {
        const token = fs.readFileSync(path.join(__dirname, 'fcm-token.txt'), 'utf8').trim();
        if (token) { res.writeHead(200); res.end(token); return; }
      } catch(e) {}
      res.writeHead(404); res.end('No token');
      return;
    }

    if (pathname === "/historico" && req.method === "GET") {
      const { supabase } = require("./supabase-client");
      supabase.from("historico_alertas").select("*").order("fecha", {ascending: false}).limit(100).then(({data, error}) => {
        if (error) { res.writeHead(500); res.end(JSON.stringify([])); return; }
        res.writeHead(200, {"Content-Type": "application/json"});
        res.end(JSON.stringify(data || []));
      });
      return;
    }

    if (pathname === '/earnings' && req.method === 'GET') {
      const { supabase } = require('./supabase-client');
      const hoy = new Date().toISOString().slice(0,10);
      supabase.from('earnings').select('*').gte('fecha', hoy).order('fecha').then(({data,error}) => {
        if (error) { res.writeHead(500); res.end(JSON.stringify([])); return; }
        res.writeHead(200, {'Content-Type': 'application/json'});
        res.end(JSON.stringify(data || []));
      });
      return;
    }

    if (pathname === '/estado-dia' && req.method === 'GET') {
      const { supabase } = require('./supabase-client');
      const hoy = new Date().toISOString().slice(0,10);
      supabase.from('alert_state').select('value').eq('key','dia_state').single().then(({data,error})=>{
        const d = (data && data.value && data.value.fecha===hoy) ? data.value : {fecha:hoy,obj_ent:0,obj_sal:0,pen_ent:0,pen_sal:0};
        res.writeHead(200,{'Content-Type':'application/json'});
        res.end(JSON.stringify(d));
      }).catch(()=>{
        res.writeHead(200,{'Content-Type':'application/json'});
        res.end(JSON.stringify({fecha:hoy,obj_ent:0,obj_sal:0,pen_ent:0,pen_sal:0}));
      });
      return;
    }

    if (pathname === '/bases' && req.method === 'GET') {
      const { supabase } = require('./supabase-client');
      Promise.all([
        supabase.from('alert_state').select('value').eq('key','base_semana').single(),
        supabase.from('alert_state').select('value').eq('key','base_mes').single(),
        supabase.from('alert_state').select('value').eq('key','base_anual').single(),
      ]).then(([s,m,a])=>{
        res.writeHead(200,{'Content-Type':'application/json'});
        res.end(JSON.stringify({
          semana: s.data?.value?.valor || 0,
          mes: m.data?.value?.valor || 0,
          anual: a.data?.value?.valor || 0,
          fecha: s.data?.value?.fecha || ''
        }));
      }).catch(()=>{ res.writeHead(500); res.end('{}'); });
      return;
    }

    if (pathname === '/snapshots' && req.method === 'GET') {
      const { supabase } = require('./supabase-client');
      supabase.from('cartera_snapshots').select('fecha,valor_total').order('fecha').then(({data,error}) => {
        if (error) { res.writeHead(500); res.end(JSON.stringify([])); return; }
        res.writeHead(200, {'Content-Type': 'application/json'});
        res.end(JSON.stringify(data || []));
      });
      return;
    }

    // ── NUEVO: variaciones diarias para HOY/SEMANA/MES/ANUAL ──
    if (pathname === '/variaciones-diarias' && req.method === 'GET') {
      const { supabase } = require('./supabase-client');
      const primerAnio = new Date().toISOString().slice(0, 4) + '-01-01';
      supabase
        .from('variaciones_diarias')
        .select('fecha,valor')
        .gte('fecha', primerAnio)
        .order('fecha')
        .then(({ data, error }) => {
          if (error) { res.writeHead(500); res.end(JSON.stringify([])); return; }
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(data || []));
        });
      return;
    }

    if (pathname === '/names' && symbols) return handleNames(req, res, symbols);
    if (pathname === '/buscar' && url.searchParams.get('q'))
      return handleBuscar(req, res, url.searchParams.get('q'));
    if (pathname === '/fuera' && symbols) return handleFuera(req, res, symbols);
    if (pathname === '/' && symbols) return handleSymbols(req, res, symbols);
    if (pathname === '/' || pathname === '/index.html') return handleIndex(req, res);

    return handleStatic(req, res, pathname);
  } catch (e) {
    console.error('ERROR:', e);
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    res.end('Error: ' + e.message);
  }
});

server.listen(PORT, () => {
  console.log(`AppCartera escuchando en puerto ${PORT}`);
});

// Chequeo alertas cada 5 min (con candado: no se solapan dos pasadas)
let alertasEnCurso = false;
async function lanzarChequeoAlertas() {
  if (alertasEnCurso) {
    console.log('Chequeo de alertas aun en curso, se omite esta pasada');
    return;
  }
  alertasEnCurso = true;
  try {
    const { checkAlerts } = require("./check-alerts");
    await checkAlerts();
  } catch(e) {
    console.error('Error chequeo alertas:', e.message);
  } finally {
    alertasEnCurso = false;
  }
}
setTimeout(lanzarChequeoAlertas, 60000);
setInterval(lanzarChequeoAlertas, 5*60*1000);

// Fuera de mercado: cada 15 min, y el propio modulo decide si esta en franja.
let fueraEnCurso = false;
setInterval(async () => {
  if (fueraEnCurso) return;
  fueraEnCurso = true;
  try { await require("./check-alerts").checkFueraMercado(); }
  catch (e) { console.error("Error fuera de mercado:", e.message); }
  finally { fueraEnCurso = false; }
}, 15*60*1000);

// Actualizar bases cada sabado a las 18:00 (mercado cerrado)
setInterval(()=>{
  const ahora = new Date();
  if(ahora.getDay()===5 && ahora.getUTCHours()===21 && ahora.getUTCMinutes()>=30 && ahora.getUTCMinutes()<31){
    const {supabase} = require('./supabase-client');
    const hoy = ahora.toISOString().slice(0,10);
    supabase.from('cartera_snapshots').select('fecha,valor_total').order('fecha').then(({data})=>{
      if(!data||data.length<2) return;
      const snaps = data.sort((a,b)=>b.fecha.localeCompare(a.fecha));
      const snapHoy = snaps[0];
      const lunesStr = (()=>{const d=new Date();d.setDate(d.getDate()-((d.getDay()+6)%7));return d.toISOString().slice(0,10);})();
      const snapViernesAnterior = snaps.find(s=>s.fecha<lunesStr);
      const snap31dic = snaps.find(s=>s.fecha==='2025-12-31');
      const primerMes = hoy.slice(0,8)+'01';
      const snap1mes = snaps.filter(s=>s.fecha<primerMes).sort((a,b)=>b.fecha.localeCompare(a.fecha))[0];
      if(!snapHoy||!snapViernesAnterior||!snap31dic) return;
      const semana = snapHoy.valor_total - snapViernesAnterior.valor_total;
      const mes = snap1mes ? snapHoy.valor_total - snap1mes.valor_total : 0;
      const anual = snapHoy.valor_total - snap31dic.valor_total;
      Promise.all([
        supabase.from('alert_state').upsert({key:'base_semana',value:{valor:semana,fecha:hoy},updated_at:new Date().toISOString()},{onConflict:'key'}),
        supabase.from('alert_state').upsert({key:'base_mes',value:{valor:mes,fecha:hoy},updated_at:new Date().toISOString()},{onConflict:'key'}),
        supabase.from('alert_state').upsert({key:'base_anual',value:{valor:anual,fecha:hoy},updated_at:new Date().toISOString()},{onConflict:'key'}),
      ]).then(()=>console.log('✅ Bases actualizadas automaticamente:', {semana,mes,anual}));
    });
  }
}, 60000);

// Reset base_semana cada lunes a las 8:00
setInterval(()=>{
  const ahora = new Date();
  if(ahora.getDay()===1 && ahora.getUTCHours()===5 && ahora.getUTCMinutes()<1){
    const {supabase} = require('./supabase-client');
    const hoy = ahora.toISOString().slice(0,10);
    supabase.from('alert_state').upsert({
      key:'base_semana',
      value:{valor:0, fecha:hoy},
      updated_at: new Date().toISOString()
    },{onConflict:'key'}).then(()=>console.log('✅ base_semana reseteada a 0'));
  }
}, 60000);

// Snapshot diario + variación diaria
function guardarSnapshotSiToca(){
  var ahora=new Date();
  var hora=ahora.getHours();
  var min=ahora.getMinutes();
  var dia=ahora.getDay();
  if(dia===0||dia===6)return;
  if(hora!==21||min<30||min>35)return;
  var fecha=ahora.toISOString().slice(0,10);
  var f=require("fs"),p=require("path");
  try{
    var prices=JSON.parse(f.readFileSync(p.join(__dirname,"price-cache.json"),"utf8"));
    var html=f.readFileSync(p.join(__dirname,"index.html"),"utf8");
    var m=html.match(/const C=(\[.*?\]);/s);
    if(!m)return;
    var C=JSON.parse(m[1]);
    var eu=prices["EURUSD=X"];
    var eurUsd=eu?eu.price:1;
    var total=0;
    for(var i of C){
      var pr=prices[i.symbol];
      if(pr){var pe=i.moneda==="USD"&&eurUsd?pr.price/eurUsd:pr.price;total+=i.titulos*pe;}
    }
    var sb=require("./supabase-client").supabase;
    sb.from("cartera_snapshots").upsert({fecha:fecha,valor_total:Math.round(total*100)/100},{onConflict:"fecha"}).then(function(r){
      if(r.error){
        console.error(r.error.message);
      } else {
        console.log("Snapshot:",fecha,total.toFixed(2));
        // ── NUEVO: guardar variación diaria (cotización) ──
        guardarVariacionDiaria(fecha, Math.round(total*100)/100);
      }
    });
  }catch(e){console.error(e.message);}
}
setInterval(guardarSnapshotSiToca,60000);

// Actualizar earnings una vez al dia
async function actualizarEarnings() {
  const apikey = process.env.ALPHAVANTAGE_KEY;
  if (!apikey) return console.log("No hay ALPHAVANTAGE_KEY");
  const tickersRaw = JSON.parse(require("fs").readFileSync(require("path").join(__dirname,"tickers.json"),"utf8"));
  const symbols = new Set(Object.keys(tickersRaw).map(s=>s.replace(/\.MC$|\.AS$|\.DE$|\.PA$|\.MI$|\.BR$|\.LS$/,"").toUpperCase()));
  return new Promise((resolve)=>{
    const url = "https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey="+apikey;
    https.get(url,{headers:{"User-Agent":"Mozilla/5.0"}},(res)=>{
      let d="";
      res.on("data",c=>d+=c);
      res.on("end",async ()=>{
        try{
          const lines=d.trim().split("\n").slice(1);
          const {supabase}=require("./supabase-client");
          let count=0;
          for(const line of lines){
            const parts=line.split(",");
            if(parts.length<4)continue;
            const sym=parts[0].trim().toUpperCase();
            if(!symbols.has(sym))continue;
            const nombre=parts[1].trim();
            const fecha=parts[2].trim();
            const estimacion=parseFloat(parts[4])||null;
            const momento=parts[6]?parts[6].trim():null;
            await supabase.from("earnings").upsert({symbol:sym,nombre,fecha,estimacion,momento},{onConflict:"symbol,fecha"});
            count++;
          }
          console.log("Earnings actualizados:",count,"valores de",lines.length,"lineas, symbols:",symbols.size);
        }catch(e){console.error("Error earnings:",e.message);}
        resolve();
      });
    }).on("error",(e)=>{ console.error("Error earnings fetch:",e.message); resolve(); });
  });
}
// Ejecutar al inicio y luego cada 24h
setTimeout(actualizarEarnings, 30000);
setInterval(actualizarEarnings, 24*60*60*1000);

// Mantener servidor activo
setInterval(() => {
  https.get('https://appcartera.onrender.com', () => {}).on('error', () => {});
}, 14 * 60 * 1000);
