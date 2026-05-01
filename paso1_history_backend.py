#!/usr/bin/env python3
"""
paso1_history_backend.py
Solo modifica server.js anadiendo el endpoint /history.
NO toca el frontend (index.html).
Verifica la sintaxis JS antes de guardar.
"""
from pathlib import Path
import subprocess

sp = Path.home() / "APPCARTERA_NUEVA" / "server.js"
s = sp.read_text(encoding="utf-8")

if "fetchYahooHistory" in s:
    print("AVISO: fetchYahooHistory ya existe, no anado nada")
else:
    funciones = '''
function fetchYahooHistory(symbol) {
  return new Promise((resolve) => {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=1mo&interval=1d`;
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
          if (!r) return resolve({ symbol, history: [] });
          const ts = r.timestamp || [];
          const closes = (r.indicators && r.indicators.quote && r.indicators.quote[0] && r.indicators.quote[0].close) || [];
          const out = [];
          for (let i = 0; i < ts.length; i++) {
            if (closes[i] != null) {
              const d = new Date(ts[i] * 1000);
              const ymd = d.toISOString().slice(0, 10);
              out.push({ date: ymd, close: closes[i] });
            }
          }
          resolve({ symbol, history: out });
        } catch (e) {
          resolve({ symbol, history: [] });
        }
      });
    });
    req.on('error', () => resolve({ symbol, history: [] }));
    req.on('timeout', () => { req.destroy(); resolve({ symbol, history: [] }); });
  });
}

async function fetchHistoryBatch(symbols) {
  const results = {};
  const BATCH_HIST = 10;
  for (let i = 0; i < symbols.length; i += BATCH_HIST) {
    const slice = symbols.slice(i, i + BATCH_HIST);
    const batch = await Promise.all(slice.map(fetchYahooHistory));
    for (const r of batch) {
      if (r.history.length) results[r.symbol] = r.history;
    }
  }
  return results;
}

async function handleHistory(req, res, symbolsParam) {
  const symbols = symbolsParam.split(',').map(s => s.trim()).filter(Boolean);
  const data = await fetchHistoryBatch(symbols);
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

'''
    if "async function handleSymbols" in s:
        s = s.replace("async function handleSymbols", funciones + "async function handleSymbols")
        print("OK funciones de historico anadidas")
    else:
        print("ERROR: no encontre 'async function handleSymbols' en server.js")
        exit(1)

if "/history" not in s:
    if "if (pathname === '/names' && symbols)" in s:
        s = s.replace(
            "if (pathname === '/names' && symbols)",
            "if (pathname === '/history' && symbols) return handleHistory(req, res, symbols);\n    if (pathname === '/names' && symbols)"
        )
        print("OK ruta /history anadida al router")
    else:
        print("ERROR: no encontre la ruta /names en server.js")
        exit(1)
else:
    print("AVISO: ruta /history ya existia")

# Guardar a archivo temporal y verificar sintaxis
tmp = sp.parent / "server.js.tmp"
tmp.write_text(s, encoding="utf-8")
r = subprocess.run(["node", "-c", str(tmp)], capture_output=True, text=True)
if r.returncode == 0:
    sp.write_text(s, encoding="utf-8")
    tmp.unlink()
    print("OK sintaxis JS valida, server.js guardado")
else:
    tmp.unlink()
    print("ERROR sintaxis JS, no he guardado nada")
    print(r.stderr)
    exit(1)

print("\nSiguiente: git add server.js && git commit && git push")
print("Despues verifica con:")
print('  curl -s "https://appcartera.onrender.com/history?symbols=AMD,FUBO" | python3 -m json.tool | head -40')
