#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_historico.py

NO modifica nada. Solo comprueba si es posible reconstruir el historico
completo de plusvalias latentes desde enero, respondiendo a 3 preguntas:

  1. ¿Tiene el Excel fecha de compra, titulos y coste en TODAS las posiciones?
  2. ¿Guardan las filas de VENTA el coste y los titulos vendidos?
  3. ¿Devuelve Yahoo cierres historicos desde enero para los ~200 tickers?

Si las tres salen bien, el historico se puede rehacer de golpe.
Si alguna falla, se dice cual y se para.

Uso:  python3 verificar_historico.py
"""

import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import openpyxl

EXCEL = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/INVERSION/PLUSVALIAS BOLSA 26_sinmacros_Claude.xlsm"
INDEX = Path("index.html")
HOJA = "2026"

MARCA_INI = "ejecuciones"
MARCA_FIN = "final app cartera diseno"

FECHA_OBJETIVO = "2026-01-02"   # primer dia habil del año


def sin_acentos(s):
    rep = {'á':'a','é':'e','í':'i','ó':'o','ú':'u','ü':'u','ñ':'n',
           'Á':'a','É':'e','Í':'i','Ó':'o','Ú':'u','Ü':'u','Ñ':'n'}
    t = "".join(rep.get(c, c) for c in str(s)).lower()
    return " ".join(t.split())


def barra(txt):
    print("\n" + "=" * 74)
    print(txt)
    print("=" * 74)


# ══════════════════════════════════════════════════════════════════════
def main():
    if not EXCEL.exists():
        print(f"❌ Excel no encontrado: {EXCEL}")
        return

    wb = openpyxl.load_workbook(open(str(EXCEL), "rb"), read_only=True, data_only=True)
    ws = wb[HOJA]

    filas = {}
    fila_ini = fila_fin = None
    for r, row in enumerate(ws.iter_rows(min_row=1, max_row=1500, max_col=40, values_only=True), start=1):
        filas[r] = row
        for v in row:
            if isinstance(v, str):
                t = sin_acentos(v)
                if MARCA_INI in t and fila_ini is None and r >= 50:
                    fila_ini = r
                if MARCA_FIN in t and fila_ini and r > fila_ini and fila_fin is None:
                    fila_fin = r

    if not fila_ini:
        print("❌ No se encuentra la marca 'ejecuciones'. Paro.")
        return

    pos_ini, pos_fin = 5, fila_ini - 1
    ven_ini = fila_ini + 1
    ven_fin = (fila_fin - 1) if fila_fin else 1500
    print(f"📐 POSICIONES {pos_ini}-{pos_fin} · VENTAS {ven_ini}-{ven_fin}")

    def cel(r, c):   # c en base 1
        row = filas.get(r)
        return row[c - 1] if row and len(row) >= c else None

    # ── PREGUNTA 1: posiciones abiertas ───────────────────────────────
    barra("PREGUNTA 1 · ¿Estan completas las POSICIONES ABIERTAS?")
    abiertas, sin_fecha, sin_coste, sin_titulos = [], [], [], []
    for r in range(pos_ini, pos_fin + 1):
        tck = cel(r, 4)
        if not tck or not str(tck).strip():
            continue
        tck = str(tck).strip()
        f_compra = cel(r, 9)    # col I
        titulos = cel(r, 11)    # col K
        coste = cel(r, 14)      # col N
        if not isinstance(titulos, (int, float)) and not isinstance(coste, (int, float)):
            continue
        abiertas.append(tck)
        if not isinstance(f_compra, datetime):
            sin_fecha.append((r, tck, repr(f_compra)[:22]))
        if not isinstance(coste, (int, float)):
            sin_coste.append((r, tck, repr(coste)[:22]))
        if not isinstance(titulos, (int, float)):
            sin_titulos.append((r, tck, repr(titulos)[:22]))

    print(f"  Posiciones abiertas          : {len(abiertas)}")
    print(f"  SIN fecha de compra (col I)  : {len(sin_fecha)}")
    print(f"  SIN coste (col N)            : {len(sin_coste)}")
    print(f"  SIN titulos (col K)          : {len(sin_titulos)}")
    for etq, lst in (("fecha", sin_fecha), ("coste", sin_coste), ("titulos", sin_titulos)):
        for r, t, v in lst[:10]:
            print(f"    ⚠️  fila {r:>4} {t:<8} {etq}={v}")
        if len(lst) > 10:
            print(f"    ... y {len(lst)-10} mas")

    fechas_ok = [cel(r, 9) for r in range(pos_ini, pos_fin + 1)
                 if isinstance(cel(r, 9), datetime)]
    if fechas_ok:
        print(f"  Compra mas antigua           : {min(fechas_ok):%d/%m/%Y}")
        print(f"  Compra mas reciente          : {max(fechas_ok):%d/%m/%Y}")

    # ── PREGUNTA 2: filas de venta ────────────────────────────────────
    barra("PREGUNTA 2 · ¿Que guardan las filas de VENTA?")
    ventas = [r for r in range(ven_ini, ven_fin + 1)
              if cel(r, 4) and isinstance(cel(r, 17), datetime)
              and isinstance(cel(r, 25), (int, float)) and cel(r, 25) != 0]
    print(f"  Filas de venta detectadas    : {len(ventas)}")
    print("\n  VOLCADO COMPLETO de las 3 ultimas ventas (para mapear columnas):")
    letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for r in ventas[-3:]:
        print(f"\n  ── fila {r} ──")
        for c in range(1, 27):
            v = cel(r, c)
            if v is None:
                continue
            if isinstance(v, datetime):
                v = f"{v:%d/%m/%Y}"
            elif isinstance(v, float):
                v = f"{v:,.2f}"
            print(f"     {letras[c-1]:>2} ({c:>2}) = {str(v)[:40]}")

    vendidos = sorted({str(cel(r, 4)).strip() for r in ventas})
    print(f"\n  Tickers distintos vendidos este año: {len(vendidos)}")

    # ── PREGUNTA 3: Yahoo historico ───────────────────────────────────
    barra("PREGUNTA 3 · ¿Da Yahoo cierres historicos desde enero?")
    if not INDEX.exists():
        print("❌ index.html no encontrado en el directorio actual. Paro aqui.")
        return
    h = INDEX.read_text(encoding="utf-8")
    m = re.search(r"const C=(\[.*?\]);", h, re.DOTALL)
    if not m:
        print("❌ No se encuentra const C en index.html. Paro aqui.")
        return
    C = json.loads(m.group(1))
    simbolos = sorted({i["symbol"] for i in C}) + ["EURUSD=X"]
    print(f"  Simbolos a probar            : {len(simbolos)} (incluye EUR/USD)")
    print("  Descargando 1 año de cierres... (1-2 minutos)\n")

    ok, sin_datos, sin_enero = [], [], []
    for n, s in enumerate(simbolos, 1):
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
               f"{urllib.parse.quote(s)}?interval=1d&range=1y")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                d = json.loads(resp.read().decode())
            res = d.get("chart", {}).get("result")
            ts = res[0].get("timestamp") if res else None
            cl = res[0]["indicators"]["quote"][0].get("close") if res else None
            if not ts or not cl:
                sin_datos.append(s)
                continue
            dias = {datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"): c
                    for t, c in zip(ts, cl) if c is not None}
            if not any(f <= FECHA_OBJETIVO for f in dias):
                sin_enero.append((s, min(dias) if dias else "-"))
            ok.append((s, len(dias), min(dias), max(dias)))
        except Exception as e:
            sin_datos.append(f"{s} ({type(e).__name__})")
        if n % 25 == 0:
            print(f"    {n}/{len(simbolos)}...")
        time.sleep(0.25)

    print(f"\n  ✅ Con historico             : {len(ok)}/{len(simbolos)}")
    print(f"  ❌ Sin datos                 : {len(sin_datos)}")
    for s in sin_datos[:20]:
        print(f"       {s}")
    print(f"  ⚠️  Sin cierres hasta {FECHA_OBJETIVO}: {len(sin_enero)}")
    for s, primera in sin_enero[:20]:
        print(f"       {s:<12} empieza en {primera}")
    if ok:
        media = sum(x[1] for x in ok) / len(ok)
        print(f"  Media de sesiones por ticker : {media:.0f}")

    # ── VEREDICTO ─────────────────────────────────────────────────────
    barra("VEREDICTO")
    p1 = not sin_fecha and not sin_coste and not sin_titulos
    p3 = len(sin_datos) == 0 and len(sin_enero) == 0
    print(f"  1. Excel completo            : {'SI' if p1 else 'NO'}")
    print(f"  2. Ventas (ver volcado arriba, lo miro yo)")
    print(f"  3. Yahoo historico completo  : {'SI' if p3 else 'NO'}")
    print()
    if p1 and p3:
        print("  ✅ Se puede reconstruir el historico entero desde enero.")
    else:
        print("  ⚠️  Hay huecos. Mira los detalles de arriba antes de seguir.")
    print("\n  Copia y pegame TODA la salida.")


if __name__ == "__main__":
    main()
