#!/usr/bin/env python3
"""
validate.py

Valida que los simbolos Yahoo del tickers.json devuelven precios
COHERENTES con los precios del Excel (columna E).

Si hay tickers desviados >5%, los muestra ordenados por desviacion descendente.
Si hay >5 tickers desviados, devuelve exit code 1 (para abortar git push).

Uso:
    python3 validate.py            # validacion normal (5% umbral)
    python3 validate.py --strict   # umbral del 2%
    python3 validate.py --max=20   # solo testea 20 primeros (rapido)
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

HOME = Path.home()
PROYECTO = HOME / "APPCARTERA_NUEVA"
TICKERS_JSON = PROYECTO / "tickers.json"

UMBRAL_DESVIACION = 0.05  # 5%
MAX_DESVIADOS_OK = 5
TIMEOUT = 10


def yahoo_price(symbol):
    """Llama a Yahoo Finance v8 chart endpoint y devuelve dict con precio + meta."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read())
        result = data.get("chart", {}).get("result")
        if not result:
            return {"error": "no_result", "symbol": symbol}
        meta = result[0].get("meta", {})
        return {
            "symbol": meta.get("symbol", symbol),
            "price": meta.get("regularMarketPrice"),
            "currency": meta.get("currency"),
            "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def main():
    estricto = "--strict" in sys.argv
    umbral = 0.02 if estricto else UMBRAL_DESVIACION
    max_n = None
    for arg in sys.argv:
        if arg.startswith("--max="):
            max_n = int(arg.split("=")[1])

    if not TICKERS_JSON.exists():
        print(f"❌ No encuentro {TICKERS_JSON}. Ejecuta antes update_from_excel_v2.py")
        sys.exit(1)

    with open(TICKERS_JSON, "r", encoding="utf-8") as f:
        ticker_map = json.load(f)

    items = list(ticker_map.items())
    if max_n:
        items = items[:max_n]

    print(f"🔎 Validando {len(items)} tickers contra Yahoo (umbral {umbral*100:.0f}%)...")
    print(f"   (esto tarda ~{len(items)*0.3:.0f}s)\n")

    desviados = []
    errores = []
    ok = 0
    inicio = time.time()

    for i, (ticker, info) in enumerate(items):
        sym = info["yahoo"]
        precio_excel = info.get("precio_excel")
        moneda = info.get("moneda")

        res = yahoo_price(sym)
        if res.get("error"):
            errores.append({"ticker": ticker, "yahoo": sym, "error": res["error"]})
            continue

        precio_yahoo = res["price"]
        if precio_yahoo is None or precio_excel is None:
            errores.append({"ticker": ticker, "yahoo": sym, "error": "precio_nulo"})
            continue

        # Comparar con tolerancia (Yahoo devuelve en moneda local del valor)
        # El precio del Excel tambien esta en moneda local del valor
        desv = abs(precio_yahoo - precio_excel) / precio_excel if precio_excel else 1.0

        if desv > umbral:
            desviados.append({
                "ticker": ticker,
                "yahoo": sym,
                "moneda_excel": moneda,
                "moneda_yahoo": res.get("currency"),
                "precio_excel": precio_excel,
                "precio_yahoo": precio_yahoo,
                "desviacion_pct": desv * 100,
                "exchange_yahoo": res.get("exchange"),
                "fuente": info.get("fuente_resolucion"),
            })
        else:
            ok += 1

        # Progreso cada 25
        if (i + 1) % 25 == 0:
            print(f"   ... {i+1}/{len(items)} procesados", end="\r")

        # Rate limit suave para no provocar 429
        time.sleep(0.15)

    elapsed = time.time() - inicio
    print(f"\n⏱  Validacion completada en {elapsed:.1f}s\n")

    # === Reporte ===
    print(f"✅ OK:        {ok:>4}")
    print(f"⚠️  Desviados: {len(desviados):>4} (>{umbral*100:.0f}%)")
    print(f"❌ Errores:   {len(errores):>4}")

    if desviados:
        print(f"\n=== TICKERS DESVIADOS (ordenados por % desviacion desc) ===")
        print(f"{'ticker':<8} | {'yahoo':<12} | {'mon_x':<5} | {'mon_y':<5} | {'precio_excel':>12} | {'precio_yahoo':>12} | {'desv':>6} | {'fuente':<18} | exchange")
        print("-" * 130)
        desviados.sort(key=lambda x: -x["desviacion_pct"])
        for d in desviados:
            print(
                f"{d['ticker']:<8} | "
                f"{d['yahoo']:<12} | "
                f"{(d['moneda_excel'] or ''):<5} | "
                f"{(d['moneda_yahoo'] or ''):<5} | "
                f"{d['precio_excel']:>12.4f} | "
                f"{d['precio_yahoo']:>12.4f} | "
                f"{d['desviacion_pct']:>5.1f}% | "
                f"{(d['fuente'] or ''):<18} | "
                f"{d['exchange_yahoo'] or ''}"
            )

    if errores:
        print(f"\n=== TICKERS CON ERROR (Yahoo no devolvio precio) ===")
        for e in errores:
            print(f"  {e['ticker']:<8} -> {e['yahoo']:<12} :: {e['error']}")

    # Calcular impacto economico estimado
    if desviados:
        print(f"\n=== IMPACTO ESTIMADO EN PLUSVALIA TOTAL ===")
        impacto_total = 0
        for d in desviados:
            info = ticker_map[d["ticker"]]
            titulos = info["titulos"]
            diff = (d["precio_yahoo"] - d["precio_excel"]) * titulos
            # Convertir a EUR si es USD (asume 1.17)
            if d["moneda_excel"] == "USD":
                diff /= 1.17
            impacto_total += diff
        print(f"  Sesgo total estimado por precios desviados: {impacto_total:>+12,.2f} EUR")
        print(f"  (esto es lo que la app esta sobrevalorando/subvalorando vs Excel)")

    # === Recomendaciones ===
    if desviados:
        print(f"\n💡 ACCION:")
        print(f"   Anade a tickers_override.json los tickers desviados con su simbolo Yahoo correcto.")
        print(f"   Para encontrar el simbolo correcto, ve a https://finance.yahoo.com y busca el nombre del valor.")
        print(f"   Luego re-ejecuta:  python3 update_from_excel_v2.py && python3 validate.py")

    # Exit code: 0 si todo OK, 1 si hay demasiados desviados
    if len(desviados) > MAX_DESVIADOS_OK:
        print(f"\n❌ ABORTAR: {len(desviados)} desviados > umbral {MAX_DESVIADOS_OK}")
        sys.exit(1)
    elif desviados:
        print(f"\n⚠️  Hay desviados pero por debajo del umbral de aborto ({MAX_DESVIADOS_OK}).")
        sys.exit(0)
    else:
        print(f"\n✅ TODO LIMPIO. Puedes hacer git push con seguridad.")
        sys.exit(0)


if __name__ == "__main__":
    main()
