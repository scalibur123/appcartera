#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
actualizar_maximos.py

Regenera maximos.json desde Yahoo (chart, range=1y, interval=1d) usando los
maximos INTRADIA de cada sesion, que es el mismo dato que devuelve
fiftyTwoWeekHigh. Asi el valor guardado y el que pinta la app coinciden, y la
fecha del maximo es la real, no la del historico reconstruido.

Si un simbolo falla (throttling, suspension, delisting) se CONSERVA su entrada
anterior: nunca se borra nada.
"""

import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROYECTO = Path(os.environ.get("APPC", str(Path.home() / "APPCARTERA_NUEVA")))
F_MAX = PROYECTO / "maximos.json"
F_TICKERS = PROYECTO / "tickers.json"

UA = "Mozilla/5.0"
TIMEOUT = 12
HILOS = 6
PAUSA = 0.15


def pedir_yahoo(simbolo):
    """Devuelve el JSON de chart 1y/1d, o None si falla."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(simbolo) + "?range=1y&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def extraer_maximo(payload):
    """De un payload de chart saca {desde, fecha, valor} con el maximo intradia."""
    if not payload:
        return None
    res = (payload.get("chart") or {}).get("result") or []
    if not res:
        return None
    r = res[0]
    ts = r.get("timestamp") or []
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    highs = q.get("high") or []
    if not ts or not highs:
        return None
    pares = [(t, h) for t, h in zip(ts, highs) if h is not None]
    if not pares:
        return None
    fechas = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
              for t, _ in pares]
    t_max, v_max = max(pares, key=lambda p: p[1])
    return {"desde": fechas[0],
            "fecha": datetime.fromtimestamp(t_max, timezone.utc).strftime("%Y-%m-%d"),
            "valor": round(float(v_max), 4)}


def procesar(simbolo):
    d = extraer_maximo(pedir_yahoo(simbolo))
    if d is None:
        time.sleep(0.5)
        d = extraer_maximo(pedir_yahoo(simbolo))
    time.sleep(PAUSA)
    return simbolo, d


def main():
    if not F_MAX.exists():
        sys.exit(f"No existe {F_MAX}")
    viejo = json.loads(F_MAX.read_text(encoding="utf-8"))

    simbolos = set(viejo.keys())
    if F_TICKERS.exists():
        tk = json.loads(F_TICKERS.read_text(encoding="utf-8"))
        for v in tk.values():
            if isinstance(v, dict) and v.get("yahoo"):
                simbolos.add(v["yahoo"])
    simbolos = sorted(simbolos)
    print(f"Consultando {len(simbolos)} simbolos a Yahoo (1y, diario)...")

    nuevo = dict(viejo)
    ok, fallos, cambios, nuevos = 0, [], [], []
    with ThreadPoolExecutor(max_workers=HILOS) as ex:
        for simbolo, d in ex.map(procesar, simbolos):
            if d is None:
                fallos.append(simbolo)
                continue
            ok += 1
            ant = viejo.get(simbolo)
            if ant is None:
                nuevos.append(simbolo)
            elif ant.get("fecha") != d["fecha"] or abs(ant.get("valor", 0) - d["valor"]) > 0.001:
                cambios.append((simbolo, ant.get("fecha"), ant.get("valor"),
                                d["fecha"], d["valor"]))
            nuevo[simbolo] = d

    backup = F_MAX.parent / ("maximos.json.backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    backup.write_text(json.dumps(viejo, ensure_ascii=False, indent=1), encoding="utf-8")
    F_MAX.write_text(json.dumps(nuevo, ensure_ascii=False), encoding="utf-8")

    print(f"\nOK: {ok}  |  fallidos (entrada anterior conservada): {len(fallos)}"
          f"  |  simbolos en fichero: {len(nuevo)}")
    if fallos:
        print("Fallidos: " + ", ".join(fallos))
    if nuevos:
        print("Nuevos: " + ", ".join(nuevos))
    if cambios:
        print(f"\nMaximos que cambian ({len(cambios)}):")
        for s, fa, va, fn, vn in sorted(cambios):
            print(f"  {s:<12} {fa} {va}  ->  {fn} {vn}")
    print(f"\nBackup: {backup.name}")
    print("Ahora ejecuta: actualizar")


if __name__ == "__main__":
    main()
