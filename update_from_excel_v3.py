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
    mensual_data = None
    plusv_hoy = 0
    plusv_semana = 0
    # Leer datos pestaña Mensual
    try:
        ws_m = wb['Mensual']
        bruto_anual = ws_m['R13'].value or 0
        neto_anual = ws_m['S13'].value or 0
        equiv_bruto = ws_m['S15'].value or 0
        neto_mensual = ws_m['J13'].value or 0
        # Plusvalías realizadas esta semana (no incluidas en F57 hasta el sábado)
        from datetime import date, timedelta
        hoy_d = date.today()
        lunes_d = hoy_d - timedelta(days=hoy_d.weekday())
        plusv_semana = 0
        ws_ej = wb['2026']
        for row in range(262, 401):
            fecha_v = ws_ej.cell(row=row, column=17).value
            plusv = ws_ej.cell(row=row, column=25).value
            if fecha_v and hasattr(fecha_v, 'date') and fecha_v.date() >= lunes_d and plusv:
                plusv_semana += plusv
        sueldo_mensual_bruto = ws_m['N13'].value or 0
        neto_anual_nomina = neto_mensual * 14

        def calcular_bruto_desde_neto(neto_anual):
            ss = 0.034
            tramos_e = [(12450,0.095),(7750,0.12),(15000,0.15),(24800,0.185),(120000,0.225),(9e9,0.235)]
            tramos_a = [(12450,0.105),(7750,0.12),(15000,0.14),(24800,0.175),(120000,0.2125),(9e9,0.2375)]
            min_ded = 5550 + 1200 + 700
            def neto_de_bruto(b):
                base = b*(1-ss) - min_ded
                ce = ca = 0; re_ = ra = base
                for lim,t in tramos_e:
                    if re_<=0: break
                    x=min(re_,lim); ce+=x*t; re_-=x
                for lim,t in tramos_a:
                    if ra<=0: break
                    x=min(ra,lim); ca+=x*t; ra-=x
                return b*(1-ss)-ce-ca
            lo,hi = neto_anual*0.8,neto_anual*2
            for _ in range(60):
                mid=(lo+hi)/2
                if neto_de_bruto(mid)<neto_anual: lo=mid
                else: hi=mid
            return round((lo+hi)/2)

        equiv_bruto_calculado = calcular_bruto_desde_neto(neto_anual_nomina)
        
        # Leer compras desglosadas (col D=ticker, I=fecha, K=titulos, N=coste_eur)
        compras_por_ticker = {}
        for row in range(5, 258):
            tckr_r = ws.cell(row=row, column=4).value
            fecha_i = ws.cell(row=row, column=9).value
            titulos_i = ws.cell(row=row, column=11).value
            coste_i = ws.cell(row=row, column=14).value
            if tckr_r and fecha_i and titulos_i and coste_i:
                tk = str(tckr_r).strip()
                if tk not in compras_por_ticker:
                    compras_por_ticker[tk] = []
                fecha_str = fecha_i.strftime('%d/%m/%Y') if hasattr(fecha_i, 'strftime') else str(fecha_i)[:10]
                precio_compra = round(coste_i / titulos_i, 4) if titulos_i else 0
                compras_por_ticker[tk].append({
                    'fecha': fecha_str,
                    'titulos': titulos_i,
                    'precio': precio_compra,
                    'coste': round(coste_i, 2)
                })

        def fmt_eur(v):
            return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        
        mensual_data = {
            'bruto_anual': fmt_eur(bruto_anual),
            'neto_anual': fmt_eur(neto_anual),
            'equiv_bruto': fmt_eur(equiv_bruto_calculado),
            'neto_nomina': fmt_eur(neto_anual_nomina),
            'sueldo_bruto': fmt_eur(sueldo_mensual_bruto),
            'sueldo_neto': fmt_eur(neto_mensual),
            'plusv_semana': round(plusv_semana, 2),
            'plusv_hoy': round(plusv_hoy, 2),
        }
    except Exception as e:
        print(f"Warning: no se pudo leer pestaña Mensual: {e}")
        mensual_data = None


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

    return [posiciones[t] for t in orden], sin_mic, mensual_data, compras_por_ticker


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


def construir_const_C_compacta(posiciones, ticker_map, compras_por_ticker={}):
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
            "compras": compras_por_ticker.get(tckr, []),
        }
        items.append(json.dumps(item_json, ensure_ascii=False, separators=(",", ":")))
    return "const C=[" + ",".join(items) + "];"


def asegurar_historico(html):
    """Añade pestaña Historico y funcion loadHistorico si no están"""
    if 'loadHistorico' not in html:
        html = html.replace(
            "<button class=\"nav-btn\" onclick=\"showTab('mensual',this)\">Mensual</button>",
            "<button class=\"nav-btn\" onclick=\"showTab('mensual',this)\">Mensual</button>\n  <button class=\"nav-btn\" onclick=\"showTab('historico',this);loadHistorico()\">Historico</button>"
        )
        historico_section = '''<div id="historico" class="section">
  <div style="padding:16px">
    <h2 style="margin-bottom:12px;font-size:16px;color:var(--muted)">Historico de alertas</h2>
    <div id="hist-list">Cargando...</div>
  </div>
</div>'''
        load_fn = """
window.loadHistorico = async function() {
  const el = document.getElementById('hist-list');
  try {
    const r = await fetch('/historico');
    const data = await r.json();
    if (data.length === 0) { el.innerHTML = '<p style="color:var(--muted)">Sin registros aun.</p>'; return; }
    el.innerHTML = data.map(d => {
      const fecha = new Date(d.fecha).toLocaleString('es-ES');
      const color = d.evento.includes('salio') ? 'var(--red)' : 'var(--green)';
      return '<div style="padding:10px;border-bottom:1px solid var(--border)"><span style="color:'+color+';font-weight:600">' + d.ticker + '</span> <span style="color:var(--muted);font-size:12px">' + d.banco + '</span><br><span style="font-size:13px">' + d.evento + ' - ' + d.precio + '</span><br><span style="color:var(--muted);font-size:11px">' + fecha + '</span></div>';
    }).join('');
  } catch(e) { el.innerHTML = 'Error cargando historico'; }
};
"""
        html = html.replace('</body>', historico_section + '\n</body>')
        html = html.replace('</script>\n</body>', load_fn + '</script>\n</body>')
    return html


def leer_rendimiento_cartera():
    import openpyxl
    from datetime import datetime
    wb = openpyxl.load_workbook(open(str(EXCEL), 'rb'), read_only=True, data_only=True)
    ws = wb['Semanal']
    meses = {'Enero':1,'Febrero':2,'Marzo':3,'Abril':4,'Mayo':5,'Junio':6,
             'Julio':7,'Agosto':8,'Septiembre':9,'Octubre':10,'Noviembre':11,'Diciembre':12}
    mes_hoy = datetime.now().month
    total_mes = 0
    total_anual = ws['F57'].value or 0
    for row in ws.iter_rows(min_row=4, max_row=60, values_only=True):
        if row[3] is not None and isinstance(row[5], (int,float)) and row[5] != 0:
            if meses.get(row[3], 0) == mes_hoy:
                total_mes = row[5]
    ws_irpf = wb['IRPF']
    tipo_irpf = ws_irpf.cell(35, 6).value or 0.20925
    return {'mes': total_mes, 'mes_n': total_mes*(1-tipo_irpf), 'anual': total_anual, 'anual_n': total_anual*(1-tipo_irpf)}

def leer_ganancias_realizadas():
    import openpyxl
    from datetime import datetime, timedelta
    wb = openpyxl.load_workbook(open(str(EXCEL), "rb"), read_only=True, data_only=True)
    hoy = datetime.now()
    inicio_semana = (hoy - timedelta(days=hoy.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    inicio_mes = hoy.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    r = {"sem_b":0,"sem_n":0,"mes_b":0,"mes_n":0,"ani_b":0,"ani_n":0}

    ws = wb["2026"]
    for row in ws.iter_rows(min_row=262, max_row=400, values_only=True):
        fecha, bruta, neta = row[16], row[24], row[25]
        if not fecha or not isinstance(fecha, datetime) or not bruta or not neta: continue
        if fecha.year != hoy.year: continue
        r["ani_b"] += bruta; r["ani_n"] += neta
        if fecha >= inicio_mes: r["mes_b"] += bruta; r["mes_n"] += neta
        if fecha >= inicio_semana: r["sem_b"] += bruta; r["sem_n"] += neta

    ws2 = wb["dividendos 26"]
    for row in ws2.iter_rows(min_row=5, max_row=500, values_only=True):
        fecha, bruta, neta = row[0], row[7], row[8]
        if not fecha or not isinstance(fecha, datetime) or not bruta or not neta: continue
        if fecha.year != hoy.year: continue
        r["ani_b"] += bruta; r["ani_n"] += neta
        if fecha >= inicio_mes: r["mes_b"] += bruta; r["mes_n"] += neta
        if fecha >= inicio_semana: r["sem_b"] += bruta; r["sem_n"] += neta

    return r


def leer_ventas():
    """Lee las ventas del año desde pestaña 2026, filas 258-380.
    Col D=ticker, Col Q(17)=fecha venta, Col Y(25)=plusvalia bruta, Col Z(26)=plusvalia neta.
    """
    wb = openpyxl.load_workbook(open(str(EXCEL), 'rb'), read_only=True, data_only=True)
    ws = wb['2026']
    ventas = []
    for row in range(258, 381):
        ticker  = ws.cell(row=row, column=4).value   # col D
        fecha   = ws.cell(row=row, column=17).value  # col Q
        bruto   = ws.cell(row=row, column=25).value  # col Y
        neto    = ws.cell(row=row, column=26).value  # col Z
        if not ticker or not fecha or not bruto or not neto:
            continue
        if not isinstance(fecha, datetime):
            continue
        ventas.append({
            'ticker': str(ticker).strip(),
            'fecha':  fecha.strftime('%Y-%m-%d'),
            'bruto':  round(float(bruto), 2),
            'neto':   round(float(neto), 2),
        })
    ventas.sort(key=lambda x: x['fecha'])
    print(f"✅ {len(ventas)} ventas leidas del Excel")
    return ventas


def actualizar_index_html(const_C_linea, mensual_data=None, ganancias_data=None, rendimiento_data=None, ventas_data=None):
    if not INDEX_HTML.exists():
        print(f"❌ index.html no encontrado: {INDEX_HTML}")
        sys.exit(1)
    html = INDEX_HTML.read_text(encoding="utf-8")
    pattern = re.compile(r"const\s+C\s*=\s*\[.*?\]\s*;", re.DOTALL)
    if not pattern.search(html):
        print("❌ No se encontro 'const C=[...]' en index.html")
        sys.exit(1)
    nuevo_html = pattern.sub(const_C_linea, html, count=1)
    fecha_hoy = datetime.now().strftime("%-d %b %Y").replace("Jan","ene").replace("Feb","feb").replace("Mar","mar").replace("Apr","abr").replace("May","may").replace("Jun","jun").replace("Jul","jul").replace("Aug","ago").replace("Sep","sep").replace("Oct","oct").replace("Nov","nov").replace("Dec","dic")
    nuevo_html = re.sub(r"Datos del Excel del [^.]+\.", f"Datos del Excel del {fecha_hoy}.", nuevo_html)
    version = datetime.now().strftime("%Y%m%d%H%M%S")
    nuevo_html = re.sub(r'content="[0-9.]+"(?=[^>]*name="app-version"|(?<=app-version")[^>]*)>', f'content="{version}">', nuevo_html)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = INDEX_HTML.parent / f"index.html.backup_{timestamp}"
    backup.write_text(html, encoding="utf-8")

    # Actualizar HTML pestaña Mensual
    if mensual_data:
        import re as re2
        nuevo_html = re2.sub(
            r'(Bruto</span><span class="mensual-val green">)[^<]*(</span>)',
            f'\g<1>{mensual_data["bruto_anual"]}\g<2>',
            nuevo_html
        )
        nuevo_html = re2.sub(
            r'(<span class="plusv-label">Neto</span><span class="mensual-val green">)[^<]*(</span>)',
            f'\g<1>{mensual_data["neto_anual"]}\g<2>',
            nuevo_html
        )
        nuevo_html = re2.sub(
            r'(Equivale a</span><span class="mensual-val green">)[^<]*(</span>)',
            f'\g<1>{mensual_data["equiv_bruto"]} brutos\g<2>',
            nuevo_html
        )
        nuevo_html = re2.sub(
            r'(id="sueldo-bruto-val">)[^<]*(</span>)',
            f'\g<1>{mensual_data["sueldo_bruto"]}\g<2>',
            nuevo_html
        )
        nuevo_html = re2.sub(
            r'(id="sueldo-neto-val">)[^<]*(</span>)',
            f'\g<1>{mensual_data["sueldo_neto"]}\g<2>',
            nuevo_html
        )
        # Inyectar PLUSV_SEMANA
        nuevo_html = re.sub(
            r'var PLUSV_SEMANA=[0-9.]+;',
            f'var PLUSV_SEMANA={mensual_data["plusv_semana"]};',
            nuevo_html
        )
        if 'var PLUSV_SEMANA=' not in nuevo_html:
            nuevo_html = nuevo_html.replace(
                'var RENDIMIENTO_MES=',
                f'var PLUSV_HOY={mensual_data["plusv_hoy"]};var PLUSV_SEMANA={mensual_data["plusv_semana"]};var RENDIMIENTO_MES='
            )
        nuevo_html = re.sub(r'var PLUSV_HOY=[0-9.]+;', f'var PLUSV_HOY={mensual_data["plusv_hoy"]};', nuevo_html)


    if ganancias_data:
        def fmtg(v):
            color = "var(--green)" if v >= 0 else "var(--red)"
            signo = "+" if v >= 0 else ""
            num = f"{abs(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
            return f'<span style="color:{color};font-size:20px;font-weight:500">{signo}{num} \u20ac</span>'
        def bloque(titulo, bruto, neto, id_b=None, id_n=None):
            ib = f' id="{id_b}"' if id_b else ''
            ib_n = f' id="{id_n}"' if id_n else ''
            return (
                f'<div style="padding:10px 0;border-bottom:1px solid var(--border)">' +
                f'<div style="font-size:11px;font-weight:700;color:var(--muted);letter-spacing:1px;margin-bottom:6px">{titulo}</div>' +
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px">' +
                f'<span style="font-size:12px;color:var(--muted)">bruto</span><span{ib} style="font-size:20px;font-weight:500">{fmtg(bruto)}</span></div>' +
                f'<div style="display:flex;justify-content:space-between;align-items:baseline">' +
                f'<span style="font-size:12px;color:var(--muted)">neto</span><span{ib_n} style="font-size:20px;font-weight:500">{fmtg(neto)}</span></div>' +
                f'</div>'
            )
        card = (
            '<div class="card" id="card-ganancias">' +
            '<div class="card-label">Cartera · Valores</div>' +
            bloque("HOY", 0, 0, id_b="hoy-b", id_n="hoy-n") +
            bloque("ESTA SEMANA", ganancias_data["sem_b"], ganancias_data["sem_n"], id_b="sem-b", id_n="sem-n") +
            bloque("ESTE MES", ganancias_data["mes_b"], ganancias_data["mes_n"], id_b="mes-b", id_n="mes-n") +
            bloque("ANUAL", ganancias_data["ani_b"], ganancias_data["ani_n"], id_b="anual-b", id_n="anual-n") +
            '</div>'
        )
        END_MARKER = '<!--/card-ganancias-->'
        card_con_marker = card + END_MARKER
        if 'id="card-ganancias"' in nuevo_html:
            start = nuevo_html.find('<div class="card" id="card-ganancias">')
            end = nuevo_html.find(END_MARKER)
            if end != -1:
                nuevo_html = nuevo_html[:start] + card_con_marker + nuevo_html[end+len(END_MARKER):]
            else:
                nuevo_html = nuevo_html[:start] + card_con_marker + nuevo_html[start:]
                nuevo_html = nuevo_html.replace(card_con_marker + card_con_marker, card_con_marker)
        else:
            nuevo_html = nuevo_html.replace('<p class="note">', card_con_marker + '\n  <p class="note">')

    if rendimiento_data:
        # Inyectar como variables JS
        js_vars = f'<script>var RENDIMIENTO_MES={rendimiento_data["mes"]};var RENDIMIENTO_MES_N={rendimiento_data["mes_n"]};var RENDIMIENTO_ANUAL={rendimiento_data["anual"]};var RENDIMIENTO_ANUAL_N={rendimiento_data["anual_n"]};</script>'
        if 'var RENDIMIENTO_MES=' in nuevo_html:
            import re as re4
            nuevo_html = re4.sub(r'<script>var RENDIMIENTO_MES=.*?;</script>', js_vars, nuevo_html)
        else:
            nuevo_html = nuevo_html.replace('</body>', js_vars + '</body>')

    if False and rendimiento_data:
        def fmtr(v):
            color = "var(--green)" if v >= 0 else "var(--red)"
            signo = "+" if v >= 0 else ""
            num = f"{abs(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
            return f'<span style="color:{color};font-size:20px;font-weight:500">{signo}{num} \u20ac</span>'
        import re as re3
        nuevo_html = re3.sub(
            r'ESTE MES</div>.*?bruto</span><span[^>]*>[^<]*</span>',
            lambda m: m.group(0)[:m.group(0).rfind('<span')] + fmtr(rendimiento_data["mes"]),
            nuevo_html, flags=re3.DOTALL, count=1
        )
        nuevo_html = re3.sub(
            r'ANUAL</div>.*?bruto</span><span[^>]*>[^<]*</span>',
            lambda m: m.group(0)[:m.group(0).rfind('<span')] + fmtr(rendimiento_data["anual"]),
            nuevo_html, flags=re3.DOTALL, count=1
        )

    # === PESTAÑA VENTAS ===
    if ventas_data is not None:
        ventas_js = f'var VENTAS_ANUAL={json.dumps(ventas_data, ensure_ascii=False)};'
        # Inyectar o actualizar variable JS
        if 'var VENTAS_ANUAL=' in nuevo_html:
            nuevo_html = re.sub(r'var VENTAS_ANUAL=\[.*?\];', ventas_js, nuevo_html, flags=re.DOTALL)
        else:
            nuevo_html = nuevo_html.replace('</body>', f'<script>{ventas_js}</script>\n</body>')

        # Añadir boton en nav si no existe
        if "showTab('ventas'" not in nuevo_html:
            nuevo_html = nuevo_html.replace(
                "<button class=\"nav-btn\" onclick=\"showTab('mensual',this)\">Mensual</button>",
                "<button class=\"nav-btn\" onclick=\"showTab('mensual',this)\">Mensual</button>\n  <button class=\"nav-btn\" onclick=\"showTab('ventas',this);renderVentas()\">Ventas</button>"
            )

        # Añadir seccion HTML si no existe
        if 'id="ventas"' not in nuevo_html:
            ventas_section = '<div id="ventas" class="section"><div style="padding:16px" id="ventas-content">Cargando...</div></div>'
            nuevo_html = nuevo_html.replace('</body>', ventas_section + '\n</body>')

        # Añadir funcion JS si no existe
        if 'function renderVentas' not in nuevo_html:
            ventas_fn = """
window.renderVentas = function() {
  const el = document.getElementById('ventas-content');
  if (!window.VENTAS_ANUAL || !VENTAS_ANUAL.length) {
    el.innerHTML = '<p style="color:var(--muted)">Sin ventas registradas.</p>';
    return;
  }
  const nombresMes = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
  const meses = {};
  VENTAS_ANUAL.forEach(v => {
    const d = new Date(v.fecha);
    const key = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0');
    if (!meses[key]) meses[key] = { nombre: nombresMes[d.getMonth()], ventas: [], bruto: 0, neto: 0 };
    meses[key].ventas.push(v);
    meses[key].bruto += v.bruto;
    meses[key].neto  += v.neto;
  });
  function fmt(v) {
    const color = v >= 0 ? 'var(--green)' : 'var(--red)';
    const signo = v >= 0 ? '+' : '';
    const num = Math.abs(v).toLocaleString('es-ES', {minimumFractionDigits:2, maximumFractionDigits:2});
    return '<span style="color:' + color + '">' + signo + num + ' \u20ac</span>';
  }
  function fmtFecha(iso) {
    const d = new Date(iso);
    return d.getDate() + '/' + (d.getMonth()+1) + '/' + d.getFullYear();
  }
  let html = '';
  // Total anual arriba
  const totalB = VENTAS_ANUAL.reduce((s,v) => s+v.bruto, 0);
  const totalN = VENTAS_ANUAL.reduce((s,v) => s+v.neto, 0);
  html += '<div style="padding:10px 0 16px;border-bottom:2px solid var(--border);margin-bottom:16px">';
  html += '<div style="font-size:11px;font-weight:700;color:var(--muted);letter-spacing:1px;margin-bottom:6px">TOTAL ANUAL</div>';
  html += '<div style="display:flex;justify-content:space-between"><span style="font-size:13px;color:var(--muted)">Bruto</span>' + fmt(totalB) + '</div>';
  html += '<div style="display:flex;justify-content:space-between"><span style="font-size:13px;color:var(--muted)">Neto</span>' + fmt(totalN) + '</div>';
  html += '</div>';
  // Por meses (mas reciente primero)
  Object.keys(meses).sort().reverse().forEach(key => {
    const m = meses[key];
    html += '<div style="margin-bottom:20px">';
    html += '<div style="display:flex;justify-content:space-between;align-items:baseline;padding:6px 0;border-bottom:2px solid var(--border);margin-bottom:6px">';
    html += '<span style="font-weight:700;font-size:15px;color:var(--text)">' + m.nombre + '</span>';
    html += '<span style="font-size:12px;color:var(--muted)">' + fmt(m.bruto) + ' / ' + fmt(m.neto) + '</span>';
    html += '</div>';
    // Ventas del mes (mas reciente primero)
    m.ventas.slice().reverse().forEach(v => {
      html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 4px;border-bottom:1px solid var(--border)">';
      html += '<div><span style="font-weight:600;font-size:14px">' + v.ticker + '</span>';
      html += '<span style="font-size:11px;color:var(--muted);margin-left:8px">' + fmtFecha(v.fecha) + '</span></div>';
      html += '<div style="text-align:right;font-size:13px">' + fmt(v.bruto) + '<br><span style="font-size:11px;color:var(--muted)">neto ' + fmt(v.neto) + '</span></div>';
      html += '</div>';
    });
    html += '</div>';
  });
  el.innerHTML = html;
};
"""
            nuevo_html = nuevo_html.replace('</script>\n</body>', ventas_fn + '</script>\n</body>')

    nuevo_html = asegurar_historico(nuevo_html)
    INDEX_HTML.write_text(nuevo_html, encoding="utf-8")
    print(f"✅ index.html actualizado. Backup: {backup.name}")



def actualizar_earnings_local():
    import os
    # Cargar .env si existe
    env_file = PROYECTO / '.env'
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
    import json, csv, io
    from urllib.request import Request, urlopen
    from datetime import datetime
    from supabase import create_client
    sb_url = os.environ.get('SUPABASE_URL', 'https://ntvupakoulwiffvdcfox.supabase.co')
    sb_key = os.environ.get('SUPABASE_KEY', '')
    if not sb_key:
        print('⚠️  Sin SUPABASE_KEY, earnings omitidos'); return
    sb = create_client(sb_url, sb_key)
    tickers_data = json.loads((PROYECTO / 'tickers.json').read_text())
    sufijos = ['.MC','.AS','.DE','.PA','.MI','.BR','.LS']
    symbols = set()
    for s in tickers_data.keys():
        t = s.upper()
        for sf in sufijos: t = t.replace(sf,'')
        symbols.add(t)
    url = 'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey=9JNVRNFZ3D5VBP5E'
    data = urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'})).read().decode()
    reader = csv.DictReader(io.StringIO(data))
    hoy = datetime.now().strftime('%Y-%m-%d')
    count = 0
    for row in reader:
        sym = row['symbol'].strip().upper()
        if sym not in symbols: continue
        fecha = row['reportDate'].strip()
        if fecha < hoy: continue
        est = row.get('estimate','').strip()
        momento = row.get('timeOfTheDay','').strip()
        sb.table('earnings').upsert({'symbol':sym,'nombre':row.get('name','').strip(),'fecha':fecha,'estimacion':float(est) if est else None,'momento':momento or None},on_conflict='symbol,fecha').execute()
        count += 1
    print(f'✅ Earnings actualizados: {count} valores')

def main():
    print(f"📂 Leyendo Excel: {EXCEL}")
    posiciones, sin_mic, mensual_data, compras_por_ticker = leer_excel_con_mic()
    ganancias_data = leer_ganancias_realizadas()
    rendimiento_data = leer_rendimiento_cartera()
    ventas_data = leer_ventas()
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

    const_C = construir_const_C_compacta(posiciones, ticker_map, compras_por_ticker)
    actualizar_index_html(const_C, mensual_data, ganancias_data=ganancias_data, rendimiento_data=rendimiento_data, ventas_data=ventas_data)

    print("\n🎯 LISTO. Siguiente paso:")
    print("   python3 validate.py")
    try:
        actualizar_earnings_local()
    except Exception as e:
        print(f"⚠️  Earnings: {e}")


if __name__ == "__main__":
    main()
# version updater - añadido automaticamente
