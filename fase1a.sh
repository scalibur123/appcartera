#!/bin/bash
# fase1a.sh - Solo Diana objetivos. Sin tocar nombres. Sin push automatico.

set -e
cd ~/APPCARTERA_NUEVA

echo "============================================="
echo "  FASE 1A - Solo Diana objetivos"
echo "============================================="
echo ""

# 1. Generar update_from_excel_v4a.py
cat > update_from_excel_v4a.py << 'PY_EOF'
#!/usr/bin/env python3
"""
update_from_excel_v4a.py - FASE 1A
Solo añade campo `objetivo` desde pestaña DIANA col AC.
NO toca nombres.
Mantiene mismo formato que v3 + un campo extra.
"""
import openpyxl, json, re, sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
PROYECTO = HOME / "APPCARTERA_NUEVA"
RUTAS_EXCEL = [
    PROYECTO / "PLUSVALIAS BOLSA 26_APP.xlsm",
    HOME / "AppCartera_Data" / "PLUSVALIAS BOLSA 26_APP.xlsm",
]
EXCEL = None
for r in RUTAS_EXCEL:
    if r.exists():
        EXCEL = r
        break
if EXCEL is None:
    print("ERROR: Excel no encontrado")
    sys.exit(1)

INDEX_HTML = PROYECTO / "index.html"
TICKERS_JSON = PROYECTO / "tickers.json"
OVERRIDE_JSON = PROYECTO / "tickers_override.json"

MIC_TO_YAHOO_SFX = {
    "BMEX": ".MC", "XPAR": ".PA", "XAMS": ".AS", "XBRU": ".BR",
    "XLIS": ".LS", "XHEL": ".HE", "XFRA": ".DE", "XETR": ".DE",
    "XMIL": ".MI", "XNAS": "", "XNYS": "", "XASE": "",
}

def cargar_overrides():
    if OVERRIDE_JSON.exists():
        with open(OVERRIDE_JSON, "r") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    return {}

def resolver_simbolo(ticker, moneda, overrides):
    if ticker in overrides:
        return overrides[ticker]
    if "." in ticker or "=" in ticker:
        return ticker
    if moneda == "USD":
        return ticker
    if moneda == "EUR":
        return ticker + ".MC"
    return ticker

def leer_objetivos_diana(wb):
    if "DIANA" not in wb.sheetnames:
        return {}
    ws = wb["DIANA"]
    objetivos = {}
    for row in range(12, ws.max_row + 1):
        ticker = ws[f"B{row}"].value
        objetivo = ws[f"AC{row}"].value
        if ticker and isinstance(ticker, str) and isinstance(objetivo, (int, float)):
            objetivos[ticker.strip()] = round(float(objetivo), 4)
    return objetivos

def main():
    print(f"Leyendo: {EXCEL}")
    wb = openpyxl.load_workbook(EXCEL, data_only=True, keep_vba=False)
    ws = wb["2026"]

    objetivos = leer_objetivos_diana(wb)
    print(f"OK {len(objetivos)} objetivos en Diana")

    overrides = cargar_overrides()
    posiciones = {}
    orden = []
    for row in range(5, 259):
        ticker = ws[f"D{row}"].value
        if not ticker or not str(ticker).strip():
            continue
        ticker = str(ticker).strip()
        if ticker not in posiciones:
            posiciones[ticker] = {
                "tckr": ticker,
                "titulos": 0,
                "coste_eur": 0,
                "moneda": ws[f"G{row}"].value,
                "objetivo": objetivos.get(ticker),
            }
            orden.append(ticker)
        posiciones[ticker]["titulos"] += ws[f"K{row}"].value or 0
        posiciones[ticker]["coste_eur"] += ws[f"N{row}"].value or 0

    con_objetivo = sum(1 for t in orden if posiciones[t]["objetivo"] is not None)
    print(f"OK {len(orden)} tickers cargados, {con_objetivo} con objetivo")

    # Construir const C
    items = []
    ticker_map = {}
    for t in orden:
        p = posiciones[t]
        sym = resolver_simbolo(t, p["moneda"], overrides)
        coste = round(p["coste_eur"], 4)
        titulos = p["titulos"]
        precio_medio = round(coste / titulos, 4) if titulos else 0
        item = {
            "tckr": t,
            "nombre": "#VALUE!",  # mantenemos el placeholder por compatibilidad
            "titulos": float(titulos),
            "coste_eur": coste,
            "precio_medio": precio_medio,
            "moneda": p["moneda"],
            "banco": "-",
            "objetivo": p["objetivo"],
            "symbol": sym,
        }
        items.append(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
        ticker_map[t] = {"yahoo": sym, "objetivo": p["objetivo"], "coste_eur": coste, "titulos": titulos, "moneda": p["moneda"]}

    const_C = "const C=[" + ",".join(items) + "];"

    # Sustituir en index.html
    html = INDEX_HTML.read_text(encoding="utf-8")
    pattern = re.compile(r"const\s+C\s*=\s*\[.*?\]\s*;", re.DOTALL)
    if not pattern.search(html):
        print("ERROR: no se encontro const C")
        sys.exit(1)
    nuevo = pattern.sub(const_C, html, count=1)

    # Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = INDEX_HTML.parent / f"index.html.backup_{timestamp}"
    backup.write_text(html, encoding="utf-8")
    INDEX_HTML.write_text(nuevo, encoding="utf-8")
    print(f"OK index.html actualizado (backup: {backup.name})")

    with open(TICKERS_JSON, "w") as f:
        json.dump(ticker_map, f, indent=2, ensure_ascii=False)
    print(f"OK tickers.json actualizado")

    print(f"\nLISTO. Para probar en local:")
    print(f"   node server.js")
    print(f"   Abre http://localhost:3000 en Chrome")
    print(f"   Si todo bien:  git add -A && git commit -m 'feat: Diana objetivos' && git push")

if __name__ == "__main__":
    main()
PY_EOF

echo "OK update_from_excel_v4a.py creado"
echo ""

# 2. Ejecutar
python3 update_from_excel_v4a.py

echo ""
echo "============================================="
echo "SIGUIENTE: probar en LOCAL antes de subir"
echo "============================================="
echo ""
echo "Ejecuta en otra terminal:"
echo "   cd ~/APPCARTERA_NUEVA && node server.js"
echo ""
echo "Y abre en Chrome:  http://localhost:3000"
echo ""
echo "Verifica que Diana muestra valores con objetivos."
echo "Si funciona, ME LO DICES y solo entonces subimos a GitHub."
echo "Si NO funciona, no se sube nada y restauramos."
