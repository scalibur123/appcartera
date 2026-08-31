#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnostico_semana.py
---------------------
Explica por que la tarjeta MERCADOS (variacion de hoy) y el bloque ESTA SEMANA
de la tarjeta Resumen no dan la misma cifra.

Descompone la diferencia entre la latente de la base semanal y la latente de
ahora en tres partes:

  1. VARIACION DE PRECIO   -> lo unico que mide la tarjeta Mercados
  2. EFECTO DIVISA         -> EUR/USD; Mercados no lo ve, ESTA SEMANA si
  3. DESFASE DE LA BASE    -> diferencia entre la latente guardada en
                              serie_latentes.json para el dia base y la latente
                              recalculada ahora con el cierre definitivo de Yahoo

Uso:
    cd ~/APPCARTERA_NUEVA
    python3 diagnostico_semana.py
    python3 diagnostico_semana.py 2026-08-28     # forzar dia base
"""

import json
import os
import sys
from datetime import date, timedelta

try:
    import yfinance as yf
except ImportError:
    sys.exit("Falta yfinance.  Instala con:  pip3 install yfinance")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
F_TICKERS = os.path.join(BASE_DIR, "tickers.json")
F_SERIE = os.path.join(BASE_DIR, "serie_latentes.json")
F_CIERRES = os.path.join(BASE_DIR, "cierres_historicos.json")


def eur(x):
    return f"{x:>14,.2f} EUR".replace(",", "@").replace(".", ",").replace("@", ".")


def cargar(path, obligatorio=True):
    if not os.path.exists(path):
        if obligatorio:
            sys.exit(f"No encuentro {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def lunes_de_esta_semana():
    hoy = date.today()
    return hoy - timedelta(days=hoy.weekday())


def dia_base(serie, lunes_str):
    """Misma logica que latenteAntesDe() en index.html: ultimo dia de la serie
    ANTERIOR al lunes de esta semana."""
    previas = sorted([f for f in serie.keys() if f < lunes_str])
    return previas[-1] if previas else None


def cierre_en_o_antes(serie_close, fecha_str):
    """Ultimo cierre disponible en o antes de fecha_str."""
    if serie_close is None or len(serie_close) == 0:
        return None
    validos = [(d.strftime("%Y-%m-%d"), float(v))
               for d, v in serie_close.items()
               if d.strftime("%Y-%m-%d") <= fecha_str]
    return validos[-1] if validos else None


def descargar(simbolos):
    """Descarga cierres de los ultimos 15 dias. Devuelve dict simbolo -> Series."""
    out = {}
    lote = 40
    for i in range(0, len(simbolos), lote):
        trozo = simbolos[i:i + lote]
        try:
            data = yf.download(trozo, period="15d", interval="1d",
                               group_by="ticker", auto_adjust=False,
                               progress=False, threads=True)
        except Exception as e:
            print(f"  aviso: fallo el lote {i//lote + 1}: {e}")
            continue
        for s in trozo:
            try:
                if len(trozo) == 1:
                    serie = data["Close"].dropna()
                else:
                    serie = data[s]["Close"].dropna()
                if len(serie):
                    out[s] = serie
            except Exception:
                pass
        print(f"  lote {i//lote + 1}: {len(out)} simbolos con datos acumulados")
    return out


def main():
    tickers = cargar(F_TICKERS)
    serie_json = cargar(F_SERIE)
    cierres_cache = cargar(F_CIERRES, obligatorio=False)

    serie = serie_json.get("serie", {})
    lunes = lunes_de_esta_semana().isoformat()

    base = sys.argv[1] if len(sys.argv) > 1 else dia_base(serie, lunes)
    if not base:
        sys.exit("No hay ningun dia en serie_latentes.json anterior al lunes.")

    latente_guardada = serie.get(base)

    print("=" * 68)
    print("  DIAGNOSTICO  ESTA SEMANA  vs  MERCADOS")
    print("=" * 68)
    print(f"  Hoy                : {date.today().isoformat()}")
    print(f"  Lunes de la semana : {lunes}")
    print(f"  Dia base usado     : {base}   (la app muestra 'desde {base[8:]} ...')")
    print(f"  serie_latentes.json generado: {serie_json.get('generado', '?')}")
    if latente_guardada is not None:
        print(f"  Latente guardada para {base}: {eur(latente_guardada)}")
    print()

    posiciones = [(t, v) for t, v in tickers.items()
                  if isinstance(v, dict) and v.get("yahoo") and v.get("titulos")]
    simbolos = sorted({v["yahoo"] for _, v in posiciones})
    print(f"Descargando {len(simbolos)} simbolos de Yahoo...")
    closes = descargar(simbolos)

    print("Descargando EUR/USD...")
    fx_serie = None
    try:
        fx_raw = yf.download("EURUSD=X", period="15d", interval="1d",
                             auto_adjust=False, progress=False)
        fx_serie = fx_raw["Close"].dropna()
        if hasattr(fx_serie, "columns"):
            fx_serie = fx_serie.iloc[:, 0]
    except Exception as e:
        print(f"  aviso: no se pudo bajar EURUSD=X: {e}")

    fx_base_par = cierre_en_o_antes(fx_serie, base)
    fx_base = fx_base_par[1] if fx_base_par else None
    fx_hoy = float(fx_serie.iloc[-1]) if fx_serie is not None and len(fx_serie) else None
    if not fx_base or not fx_hoy:
        sys.exit("Sin tipo de cambio; no se puede separar el efecto divisa.")

    print(f"  EUR/USD {base}: {fx_base:.4f}   |   ahora: {fx_hoy:.4f}   "
          f"({(fx_hoy/fx_base - 1) * 100:+.2f}%)")
    print()

    val_base_fxbase = 0.0   # valor el dia base, al cambio del dia base
    val_hoy_fxbase = 0.0    # valor de hoy, al cambio del dia base  -> aisla precio
    val_hoy_fxhoy = 0.0     # valor de hoy, al cambio de hoy        -> real
    coste_total = 0.0
    sin_dato = []
    detalle = []

    for tckr, v in posiciones:
        sym = v["yahoo"]
        tit = float(v["titulos"])
        coste = float(v.get("coste_eur") or 0)
        usd = v.get("moneda") == "USD"

        s = closes.get(sym)
        par_base = cierre_en_o_antes(s, base)
        p_hoy = float(s.iloc[-1]) if s is not None and len(s) else None

        # Fallback al cache de cierres historicos para el dia base
        if par_base is None and sym in cierres_cache:
            c = cierres_cache.get(sym) or {}
            if isinstance(c, dict):
                fechas = sorted([f for f in c.keys() if f <= base])
                if fechas:
                    par_base = (fechas[-1], float(c[fechas[-1]]))

        if par_base is None or p_hoy is None:
            sin_dato.append((tckr, sym, coste))
            continue

        f_base_real, p_base = par_base
        coste_total += coste

        vb = tit * p_base / fx_base if usd else tit * p_base
        vh_fxb = tit * p_hoy / fx_base if usd else tit * p_hoy
        vh_fxh = tit * p_hoy / fx_hoy if usd else tit * p_hoy

        val_base_fxbase += vb
        val_hoy_fxbase += vh_fxb
        val_hoy_fxhoy += vh_fxh

        detalle.append({
            "t": tckr, "sym": sym, "usd": usd,
            "f_base": f_base_real, "p_base": p_base, "p_hoy": p_hoy,
            "d_precio": vh_fxb - vb,
            "d_divisa": vh_fxh - vh_fxb,
            "desfase_fecha": f_base_real != base,
        })

    d_precio = val_hoy_fxbase - val_base_fxbase
    d_divisa = val_hoy_fxhoy - val_hoy_fxbase
    d_total = val_hoy_fxhoy - val_base_fxbase

    latente_hoy = val_hoy_fxhoy - coste_total
    latente_base_recalc = val_base_fxbase - coste_total

    print("-" * 68)
    print("  DESGLOSE  (solo posiciones abiertas, sin ventas ni dividendos)")
    print("-" * 68)
    print(f"  Valor {base} (cambio de ese dia) : {eur(val_base_fxbase)}")
    print(f"  Valor ahora  (cambio de ahora)   : {eur(val_hoy_fxhoy)}")
    print()
    print(f"  1) Variacion de precio           : {eur(d_precio)}   <- esto mide MERCADOS")
    print(f"  2) Efecto divisa EUR/USD         : {eur(d_divisa)}   <- MERCADOS no lo ve")
    print(f"     ------------------------------------------------")
    print(f"     Suma                          : {eur(d_total)}")
    print()

    if latente_guardada is not None:
        desfase = latente_base_recalc - latente_guardada
        print(f"  3) Base guardada para {base}    : {eur(latente_guardada)}")
        print(f"     Base recalculada ahora        : {eur(latente_base_recalc)}")
        print(f"     Desfase de la base            : {eur(desfase)}")
        if abs(desfase) > 300:
            print("     >> La base guardada NO es el cierre definitivo.")
            print("        Ejecuta 'actualizar' para regenerarla (ese dia aun no esta congelado).")
        print()
        print(f"  ESTA SEMANA que pinta la app  = latente ahora - base guardada")
        print(f"                                = {eur(latente_hoy)} - {eur(latente_guardada)}")
        print(f"                                = {eur(latente_hoy - latente_guardada)}")
        print("                                  (+ ventas brutas y dividendos brutos de la semana)")
        print()

    if sin_dato:
        c = sum(x[2] for x in sin_dato)
        print(f"  Sin datos de Yahoo ({len(sin_dato)} valores, {eur(c)} de coste):")
        print("   ", ", ".join(f"{t}({s})" for t, s, _ in sin_dato[:25]))
        print()

    desfasados = [d for d in detalle if d["desfase_fecha"]]
    if desfasados:
        print(f"  Valores cuyo cierre base no es del {base} sino anterior "
              f"({len(desfasados)}):")
        print("   ", ", ".join(f"{d['t']}[{d['f_base']}]" for d in desfasados[:25]))
        print()

    print("-" * 68)
    print("  15 valores que mas aportan a la variacion desde la base")
    print("-" * 68)
    detalle.sort(key=lambda d: abs(d["d_precio"] + d["d_divisa"]), reverse=True)
    print(f"  {'TICKER':<10}{'precio base':>13}{'precio hoy':>13}"
          f"{'d.precio':>13}{'d.divisa':>12}")
    for d in detalle[:15]:
        print(f"  {d['t']:<10}{d['p_base']:>13.4f}{d['p_hoy']:>13.4f}"
              f"{d['d_precio']:>13,.0f}{d['d_divisa']:>12,.0f}")
    print()
    print("=" * 68)


if __name__ == "__main__":
    main()
