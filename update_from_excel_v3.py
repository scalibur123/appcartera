#!/usr/bin/env python3
"""
update_from_excel_v3.py - SOLUCION DEFINITIVA

Lee el Excel y resuelve simbolos Yahoo automaticamente desde la columna B
(que tiene formato "Nombre (MIC:TICKER)" tipo "Repsol SA (BMEX:REP)").

ESTRATEGIA EN CASCADA:
  1. Si tickers_override.json tiene el ticker -> usar ese (override manual gana siempre)
  2. Leer columna B o AO buscando patron (MIC:TICKER) y mapear MIC -> sufijo Yahoo
  3. Si la columna B/AO esta vacia o #VALUE! -> usar moneda como heuristica:
     - USD -> ticker tal cual
     - EUR sin sufijo -> .MC (Madrid) por defecto
  4. Si nada funciona -> dejar ticker tal cual y avisar

NOTA IMPORTANTE: La columna B es una formula que da #VALUE! al leer con Python
si el Excel no se ha guardado con valores cacheados. SOLUCION: copiar la columna B
como VALOR a la columna AO (script export_mic_values.py lo hace automaticamente).
"""

import openpyxl
import json
import re
import sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
PROYECTO = HOME / "APPCARTERA_NUEVA"
EXCEL = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/INVERSION/PLUSVALIAS BOLSA 26.xlsm"
HOJA = "2026"
FILA_INI = 5
FILA_FIN = 258
INDEX_HTML = PROYECTO / "index.html"
TICKERS_JSON = PROYECTO / "tickers.json"
OVERRIDE_JSON = PROYECTO / "tickers_override.json"
MIC_NAMES_TXT = PROYECTO / "mic_nombres.txt"  # opcional: pegar ahi columna B manualmente

# === MAPA MIC -> SUFIJO YAHOO ===
MIC_TO_YAHOO_SFX = {
    "BMEX": ".MC",   # Madrid (Bolsas y Mercados Españoles)
    "XMAD": ".MC",   # Madrid (codigo alternativo)
    "XPAR": ".PA",   # Paris (Euronext Paris)
    "XAMS": ".AS",   # Amsterdam (Euronext Amsterdam)
    "XBRU": ".BR",   # Bruselas (Euronext Brussels)
    "XLIS": ".LS",   # Lisboa (Euronext Lisbon)
    "XHEL": ".HE",   # Helsinki (Nasdaq Helsinki)
    "XSTO": ".ST",   # Estocolmo
    "XCSE": ".CO",   # Copenhague
    "XOSL": ".OL",   # Oslo
    "XFRA": ".DE",   # Frankfurt
    "XETR": ".DE",   # Xetra (Frankfurt electronico)
    "XMIL": ".MI",   # Milan
    "XLON": ".L",    # Londres
    "XWBO": ".VI",   # Viena
    "XSWX": ".SW",   # Suiza (SIX)
    "XVTX": ".VX",   # Suiza Virt-x
    "XWAR": ".WA",   # Varsovia
    "XPRA": ".PR",   # Praga
    "XBUD": ".BD",   # Budapest
    "XATH": ".AT",   # Atenas
    "XIST": ".IS",   # Estambul
    "XTAE": ".TA",   # Tel Aviv
    # USA: sin sufijo
    "XNAS": "",      # Nasdaq
    "XNYS": "",      # NYSE
    "XASE": "",      # NYSE American (AMEX)
    "BATS": "",      # BATS / Cboe
    "ARCX": "",      # NYSE Arca
    "XOTC": "",      # OTC
    "PINX": "",      # Pink Sheets
    # Otros
    "XTSX": ".V",    # TSX Venture
    "XTSE": ".TO",   # Toronto
    "XHKG": ".HK",   # Hong Kong
    "XTKS": ".T",    # Tokio
    "XSHG": ".SS",   # Shanghai
    "XSHE": ".SZ",   # Shenzhen
}

REGEX_MIC = re.compile(r"\(([A-Z][A-Z0-9]{2,4}):([A-Z0-9]+)\)")


BANCO_NORMALIZE = {
    'r4': 'R4', 'R4': 'R4',
    'ing': 'ING', 'Ing': 'ING', 'ING': 'ING',
    'ibkr': 'IBKR', 'IBKR': 'IBKR', 'Ibkr': 'IBKR',
    'revolut': 'REVOLUT', 'Revolut': 'REVOLUT',
    'medio': 'MEDIOLANUM', 'MEDIO': 'MEDIOLANUM', 'Medio': 'MEDIOLANUM',
    'myinv': 'MYINV', 'Myinv': 'MYINV', 'MyInv': 'MYINV',
    'r4/ing': 'R4/ING', 'R4/ING': 'R4/ING', 'ing/r4': 'R4/ING',
    'medio/ing': 'MEDIO/ING', 'MEDIO/ING': 'MEDIO/ING', 'ing/medio': 'MEDIO/ING',
}

def normalizar_banco(b):
    if not b: return '-'
    b = str(b).strip()
    return BANCO_NORMALIZE.get(b, b.upper())


def cargar_overrides():
    if OVERRIDE_JSON.exists():
        with open(OVERRIDE_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    return {}


def cargar_mic_externos():
    """
    Si existe mic_nombres.txt en el proyecto, lo lee como respaldo.
    Es un fichero con una linea por ticker: "Nombre (MIC:TICKER)".
    El orden NO importa. Construye un dict ticker -> mic.
    """
    if not MIC_NAMES_TXT.exists():
        return {}
    mapa = {}
    with open(MIC_NAMES_TXT, "r", encoding="utf-8") as f:
        for linea in f:
            m = REGEX_MIC.search(linea)
            if m:
                mic, tckr = m.group(1), m.group(2)
                mapa[tckr] = mic
    return mapa


def leer_diana(wb, tickers_vivos):
    if 'DIANA' not in wb.sheetnames:
        return {}
    ws = wb['DIANA']
    objetivos = {}
    for row in range(12, 221):
        ticker = ws[f'B{row}'].value
        objetivo = ws[f'AC{row}'].value
        if not ticker or not isinstance(ticker, str): continue
        ticker = ticker.strip()
        if ticker not in tickers_vivos: continue
        if ticker in objetivos: continue
        if not isinstance(objetivo, (int, float)): continue
        objetivos[ticker] = round(float(objetivo), 4)
    return objetivos

def leer_excel_con_mic():
    """
    Lee Excel agrupando por ticker. Intenta extraer MIC de:
      - columna B (formato "Nombre (MIC:TICKER)")
      - columna AO (si la macro VBA copio los valores ahi)
      - mic_nombres.txt (fallback manual)
    """
    if not EXCEL.exists():
        print(f"❌ Excel no encontrado: {EXCEL}")
        sys.exit(1)

    # Cargar dos versiones: una con valores cacheados y otra con formulas
    wb = openpyxl.load_workbook(EXCEL, data_only=True, keep_vba=False)
    ws = wb[HOJA]

    mic_externo = cargar_mic_externos()
    if mic_externo:
        print(f"📄 Cargados {len(mic_externo)} mapeos MIC desde {MIC_NAMES_TXT.name}")

    posiciones = {}
    orden = []
    sin_mic = []

    for row in range(FILA_INI, FILA_FIN + 1):
        ticker = ws[f"D{row}"].value
        if not ticker or not str(ticker).strip():
            continue
        ticker = str(ticker).strip()
        titulos = ws[f"K{row}"].value or 0
        coste_eur = ws[f"N{row}"].value or 0
        moneda = ws[f"G{row}"].value
        precio_excel = ws[f"E{row}"].value

        # Intentar extraer MIC: B -> AO -> mic_nombres.txt
        mic = None
        nombre_completo = None

        for col_letter in ["B", "AO"]:
            v = ws[f"{col_letter}{row}"].value
            if v and isinstance(v, str) and "#" not in v:
                m = REGEX_MIC.search(v)
                if m:
                    mic = m.group(1)
                    nombre_completo = v.strip()
                    break

        if not mic and ticker in mic_externo:
            mic = mic_externo[ticker]

        if ticker not in posiciones:
            posiciones[ticker] = {
                "tckr": ticker,
                "nombre": nombre_completo or ticker,
                "titulos": 0,
                "coste_eur": 0,
                "moneda": moneda,
                "precio_excel": precio_excel,
                "mic": mic,
                "banco": normalizar_banco(ws[f"H{row}"].value),
                "objetivo": None,
            }
            orden.append(ticker)
            if not mic:
                sin_mic.append(ticker)

        posiciones[ticker]["titulos"] += titulos
        posiciones[ticker]["coste_eur"] += coste_eur
        # Si en una fila posterior aparece el MIC, actualizar
        if mic and not posiciones[ticker]["mic"]:
            posiciones[ticker]["mic"] = mic
            posiciones[ticker]["nombre"] = nombre_completo or ticker
            if ticker in sin_mic:
                sin_mic.remove(ticker)

    # Leer objetivos de pestana DIANA
    tickers_vivos = set(posiciones.keys())
    objetivos = leer_diana(wb, tickers_vivos)
    for t, obj in objetivos.items():
        if t in posiciones:
            posiciones[t]['objetivo'] = obj
    print(f'OK {len(objetivos)} objetivos leidos de pestana DIANA')

    # DEBUG
    fubo = posiciones.get('FUBO')
    abeo = posiciones.get('ABEO')
    if fubo: print(f'DEBUG FUBO en posiciones: objetivo={fubo.get("objetivo")}, banco={fubo.get("banco")}')
    if abeo: print(f'DEBUG ABEO en posiciones: objetivo={abeo.get("objetivo")}, banco={abeo.get("banco")}')

    return [posiciones[t] for t in orden], sin_mic


def resolver_simbolo_yahoo(p, overrides):
    """Resuelve simbolo Yahoo en cascada: override > mic > moneda > tal cual."""
    ticker = p["tckr"]

    # 1. Override manual
    if ticker in overrides:
        return overrides[ticker], "override"

    # 2. Si el ticker ya tiene sufijo punto, usar tal cual
    if "." in ticker or "=" in ticker:
        return ticker, "ya_tenia_sufijo"

    # 3. MIC desde Excel
    mic = p.get("mic")
    if mic and mic in MIC_TO_YAHOO_SFX:
        sfx = MIC_TO_YAHOO_SFX[mic]
        return ticker + sfx, f"mic_{mic}"

    # 4. MIC desconocido -> avisar pero seguir
    if mic:
        return ticker, f"mic_desconocido_{mic}"

    # 5. Heuristica por moneda
    if p.get("moneda") == "USD":
        return ticker, "fallback_usd_directo"
    if p.get("moneda") == "EUR":
        return ticker + ".MC", "fallback_madrid"

    return ticker, "sin_resolver"


def construir_const_C_compacta(posiciones, ticker_map):
    items = []
    for p in posiciones:
        tckr = p["tckr"]
        sym = ticker_map[tckr]["yahoo"]
        coste = round(p["coste_eur"], 4)
        titulos = round(p["titulos"], 4) if p["titulos"] != int(p["titulos"]) else int(p["titulos"])
        precio_medio = round(coste / titulos, 4) if titulos else 0
        nombre = p.get("nombre", tckr)
        if "(" in nombre:
            nombre = nombre.split("(")[0].strip()
        if not nombre or "#" in nombre:
            nombre = tckr
        item_json = {
            "tckr": tckr,
            "nombre": nombre,
            "titulos": float(titulos),
            "coste_eur": coste,
            "precio_medio": precio_medio,
            "moneda": p["moneda"],
            "banco": p.get("banco", "-"),
            "objetivo": p.get("objetivo"),
            "symbol": sym,
        }
        items.append(json.dumps(item_json, ensure_ascii=False, separators=(",", ":")))
    return "const C=[" + ",".join(items) + "];"


def actualizar_index_html(const_C_linea):
    if not INDEX_HTML.exists():
        print(f"❌ index.html no encontrado: {INDEX_HTML}")
        sys.exit(1)
    html = INDEX_HTML.read_text(encoding="utf-8")
    pattern = re.compile(r"const\s+C\s*=\s*\[.*?\]\s*;", re.DOTALL)
    if not pattern.search(html):
        print("❌ No se encontro 'const C=[...]' en index.html")
        sys.exit(1)
    nuevo_html = pattern.sub(const_C_linea, html, count=1)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = INDEX_HTML.parent / f"index.html.backup_{timestamp}"
    backup.write_text(html, encoding="utf-8")
    INDEX_HTML.write_text(nuevo_html, encoding="utf-8")
    print(f"✅ index.html actualizado. Backup: {backup.name}")


def main():
    print(f"📂 Leyendo Excel: {EXCEL}")
    posiciones, sin_mic = leer_excel_con_mic()
    print(f"✅ {len(posiciones)} tickers unicos cargados")

    overrides = cargar_overrides()
    print(f"✅ {len(overrides)} overrides manuales")

    # Resolver simbolos
    ticker_map = {}
    stats = {}
    for p in posiciones:
        sym, fuente = resolver_simbolo_yahoo(p, overrides)
        ticker_map[p["tckr"]] = {
            "yahoo": sym,
            "mic": p.get("mic"),
            "moneda": p["moneda"],
            "titulos": float(p["titulos"]),
            "coste_eur": round(p["coste_eur"], 4),
            "precio_excel": p["precio_excel"] if isinstance(p["precio_excel"], (int, float)) else None,
            "fuente_resolucion": fuente,
        }
        stats[fuente] = stats.get(fuente, 0) + 1

    print(f"\n📊 Resolucion de simbolos:")
    for fuente, n in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   {fuente:<25} {n}")

    if sin_mic:
        print(f"\n⚠️  {len(sin_mic)} tickers SIN MIC en Excel:")
        for t in sin_mic[:20]:
            print(f"     - {t}")
        if len(sin_mic) > 20:
            print(f"     ... y {len(sin_mic)-20} mas")
        print(f"   Estos usaran fallback (USD directo o .MC). Si descuadran, anade")
        print(f"   liena tipo 'Nombre (MIC:TICKER)' a {MIC_NAMES_TXT.name}")

    with open(TICKERS_JSON, "w", encoding="utf-8") as f:
        json.dump(ticker_map, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Guardado {TICKERS_JSON}")

    const_C = construir_const_C_compacta(posiciones, ticker_map)
    actualizar_index_html(const_C)

    print("\n🎯 LISTO. Siguiente paso:")
    print("   python3 validate.py")


if __name__ == "__main__":
    main()
