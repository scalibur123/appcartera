#!/usr/bin/env python3
"""
AppCartera — Gráfico histórico evolución cartera 2026
Ejecutar: python3 ~/APPCARTERA_NUEVA/grafico_cartera.py
"""

import json, sys, warnings
from datetime import date, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

import openpyxl
import pandas as pd
import yfinance as yf

# ─── RUTAS ────────────────────────────────────────────────────────────────────
EXCEL_PATH    = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/INVERSION/PLUSVALIAS BOLSA 26.xlsm"
OVERRIDE_PATH = Path.home() / "APPCARTERA_NUEVA/tickers_override.json"
OUTPUT_HTML   = Path.home() / "APPCARTERA_NUEVA/grafico_cartera.html"
CACHE_PATH    = Path.home() / "APPCARTERA_NUEVA/grafico_cache.json"

START_DATE = date(2026, 1, 1)
END_DATE   = date.today()

# Anclas reales del valor total de cartera en EUR (verificadas manualmente)
ANCLAS = {
    date(2026, 1,  1): 2_131_928,
    date(2026, 1, 31): 2_123_523,
    date(2026, 2, 28): 2_091_636,
    date(2026, 3, 31): 2_243_323,
    date(2026, 4, 30): 2_327_337,
}

# Tickers especiales que no están en el override y no son USA
EXTRA_OVERRIDES = {
    "GLXY": "GLXY.TO",   # Galaxy Digital — Toronto
    "DOM":  "DOM.MC",    # ya en override pero por si acaso
    "SWIM": "SWIM",      # Latham Group USA — sin sufijo
    "AMV0": "AMV0.DE",   # ya en override
}

# ─── 1. LEER OVERRIDES ────────────────────────────────────────────────────────
def load_overrides() -> dict:
    overrides = dict(EXTRA_OVERRIDES)
    if OVERRIDE_PATH.exists():
        with open(OVERRIDE_PATH) as f:
            data = json.load(f)
        # filtrar claves que empiezan por _ (comentarios)
        overrides.update({k: v for k, v in data.items() if not k.startswith("_")})
    return overrides

# ─── 2. LEER EXCEL ────────────────────────────────────────────────────────────
def read_excel(path: Path, overrides: dict):
    print(f"📂 Leyendo Excel...")
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    ws = wb["2026"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # ── Posiciones abiertas: filas 5-257 (índices 4-256) ──
    positions = []
    for r in rows[4:257]:
        ticker_raw = r[3]   # Col D
        moneda     = r[6]   # Col G
        broker     = r[7]   # Col H
        fecha_raw  = r[8]   # Col I — fecha compra
        shares     = r[18]  # Col S — títulos ACTUALES (ya neteados de ventas parciales)
        cost_eur   = r[13]  # Col N — coste en EUR

        if not ticker_raw or not shares:
            continue
        try:
            shares = float(shares)
        except (TypeError, ValueError):
            continue
        if shares <= 0.001:
            continue

        ticker_raw = str(ticker_raw).strip().upper()
        moneda     = str(moneda).strip().upper() if moneda else "EUR"
        broker     = str(broker).strip().lower() if broker else ""

        # Resolver símbolo Yahoo
        yahoo_tk = overrides.get(ticker_raw, ticker_raw)

        # Fecha de compra
        if fecha_raw is None:
            fecha_compra = START_DATE
        elif hasattr(fecha_raw, 'date'):
            fecha_compra = fecha_raw.date()   # datetime → date
        elif isinstance(fecha_raw, date):
            fecha_compra = fecha_raw
        elif isinstance(fecha_raw, str):
            try:
                fecha_compra = pd.to_datetime(fecha_raw).date()
            except Exception:
                fecha_compra = START_DATE
        else:
            fecha_compra = START_DATE

        # Si la compra es después de hoy, ignorar
        if fecha_compra > END_DATE:
            continue

        try:
            cost_eur = float(cost_eur) if cost_eur else 0.0
        except (TypeError, ValueError):
            cost_eur = 0.0

        positions.append({
            "ticker_raw":   ticker_raw,
            "ticker_yahoo": yahoo_tk,
            "moneda":       moneda,
            "broker":       broker,
            "fecha_compra": fecha_compra,
            "shares":       shares,
            "cost_eur":     cost_eur,
        })

    # ── Ventas: filas 259-390 (índices 258-389) ──
    # fila 258 es separador, empezamos en 259
    sales = []
    for r in rows[258:390]:
        ticker_raw  = r[3]   # Col D
        moneda      = r[6]   # Col G
        shares_sold = r[10]  # Col K — títulos vendidos
        fecha_raw   = r[16]  # Col Q — fecha venta

        if not ticker_raw or not shares_sold:
            continue
        try:
            shares_sold = float(shares_sold)
        except (TypeError, ValueError):
            continue
        if shares_sold <= 0.001:
            continue

        ticker_raw = str(ticker_raw).strip().upper()
        moneda     = str(moneda).strip().upper() if moneda else "EUR"
        yahoo_tk   = overrides.get(ticker_raw, ticker_raw)

        if fecha_raw is None:
            continue
        elif hasattr(fecha_raw, 'date'):
            fecha_venta = fecha_raw.date()   # datetime → date
        elif isinstance(fecha_raw, date):
            fecha_venta = fecha_raw
        elif isinstance(fecha_raw, str):
            try:
                fecha_venta = pd.to_datetime(fecha_raw).date()
            except Exception:
                continue
        else:
            continue

        if fecha_venta < START_DATE or fecha_venta > END_DATE:
            continue

        importe_eur = r[21] if len(r) > 21 else None  # Col V
        try:
            importe_eur = float(importe_eur) if importe_eur else 0.0
        except (TypeError, ValueError):
            importe_eur = 0.0

        sales.append({
            "ticker_yahoo": yahoo_tk,
            "moneda":       moneda,
            "shares_sold":  shares_sold,
            "fecha_venta":  fecha_venta,
            "importe_eur":  importe_eur,
        })

    df_pos   = pd.DataFrame(positions)
    df_sales = pd.DataFrame(sales) if sales else pd.DataFrame(
        columns=["ticker_yahoo", "moneda", "shares_sold", "fecha_venta"])

    print(f"   → {len(df_pos)} líneas de posición, {len(df_sales)} ventas en 2026")
    return df_pos, df_sales

# ─── 3. CONSTRUIR SHARES DIARIAS ─────────────────────────────────────────────
# NOTA IMPORTANTE: Col S ya tiene los títulos netos actuales.
# Para el historial, necesitamos reconstruir el pasado usando las ventas.
# Lógica: en cada fecha d,
#   shares_en_d = shares_actuales + ventas_posteriores_a_d - compras_posteriores_a_d
# Pero como no tenemos historial de compras previas detallado,
# usamos la aproximación práctica:
#   shares_en_d = sum(compras hasta d) - sum(ventas hasta d)
# donde "compras" = la posición actual (Col S) + ventas que ocurrieron DESPUÉS de hoy
# Esta es la forma más honesta sin datos históricos de cada compra.

def build_daily_shares(df_pos: pd.DataFrame, df_sales: pd.DataFrame) -> pd.DataFrame:
    print("🗓️  Construyendo historial diario de posiciones...")

    date_range = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
    all_dates  = [d.date() for d in date_range]

    records = []
    tickers = df_pos["ticker_yahoo"].unique()

    for tk in tickers:
        sub    = df_pos[df_pos["ticker_yahoo"] == tk]
        moneda = sub["moneda"].iloc[0]

        # Shares actuales netas (Col S) — punto de partida = hoy
        shares_hoy = sub["shares"].sum()

        # Ventas de este ticker que ocurrieron desde START_DATE hasta hoy
        if not df_sales.empty:
            ventas_tk = df_sales[df_sales["ticker_yahoo"] == tk].copy()
            ventas_tk = ventas_tk.sort_values("fecha_venta")
        else:
            ventas_tk = pd.DataFrame(columns=["fecha_venta", "shares_sold"])

        # Total vendido en 2026
        total_vendido_2026 = ventas_tk["shares_sold"].sum() if not ventas_tk.empty else 0.0

        # Shares al inicio de 2026 = shares_hoy + total_vendido_2026
        shares_inicio = shares_hoy + total_vendido_2026

        # Para cada día, shares = shares_inicio - ventas_acumuladas_hasta_ese_día
        for d in all_dates:
            vendido_hasta_d = ventas_tk[ventas_tk["fecha_venta"] <= d]["shares_sold"].sum() \
                if not ventas_tk.empty else 0.0
            net = shares_inicio - vendido_hasta_d

            if net > 0.001:
                records.append({
                    "date":         d,
                    "ticker_yahoo": tk,
                    "moneda":       moneda,
                    "shares":       net,
                })

    df = pd.DataFrame(records)
    print(f"   → {len(df):,} registros (fecha × ticker)")
    return df

# ─── 4. DESCARGAR PRECIOS ─────────────────────────────────────────────────────
def download_prices(tickers: list, start: date, end: date) -> pd.DataFrame:
    print(f"\n📡 Descargando precios históricos ({len(tickers)} tickers)...")

    # Siempre incluir EUR/USD
    all_tickers = sorted(set(tickers) | {"EURUSD=X"})

    start_str = start.strftime("%Y-%m-%d")
    end_str   = (end + timedelta(days=4)).strftime("%Y-%m-%d")

    frames = []
    failed = []
    chunk_size = 40

    for i in range(0, len(all_tickers), chunk_size):
        chunk = all_tickers[i:i+chunk_size]
        try:
            raw = yf.download(
                chunk,
                start=start_str,
                end=end_str,
                progress=False,
                auto_adjust=True,
                threads=True,
            )
            if raw.empty:
                failed.extend(chunk)
                continue

            if isinstance(raw.columns, pd.MultiIndex):
                close = raw["Close"].copy()
            else:
                # Un solo ticker
                close = raw[["Close"]].rename(columns={"Close": chunk[0]})

            frames.append(close)
            n_ok = len(chunk) - sum(1 for c in chunk if c not in close.columns or close[c].isna().all())
            print(f"   ✓ Bloque {i//chunk_size+1}: {n_ok}/{len(chunk)} OK")

        except Exception as e:
            print(f"   ✗ Error bloque {i//chunk_size+1}: {e}")
            failed.extend(chunk)

    if not frames:
        sys.exit("❌ Sin datos de precios. Revisa conexión a internet.")

    prices = pd.concat(frames, axis=1)
    # Asegurar índice como date
    prices.index = pd.to_datetime(prices.index).date
    prices = prices[prices.index <= end]

    # Forward-fill: fines de semana y festivos heredan el precio del día anterior
    prices = prices.ffill().bfill()

    if failed:
        print(f"   ⚠️  Sin datos: {failed}")

    print(f"   → Matriz: {prices.shape[0]} días × {prices.shape[1]} tickers")
    return prices

# ─── 5. CALCULAR VALOR DIARIO ─────────────────────────────────────────────────
def compute_daily_value(df_shares: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    print("\n🔢 Calculando valor diario...")

    eurusd_col = prices.get("EURUSD=X")  # USD por EUR (ej: 1.08)

    all_dates = sorted(df_shares["date"].unique())
    daily = {}

    for d in all_dates:
        day = df_shares[df_shares["date"] == d]

        # Tipo de cambio del día
        if eurusd_col is not None and d in eurusd_col.index:
            fx = float(eurusd_col.loc[d])
            if pd.isna(fx) or fx <= 0:
                fx = 1.09
        else:
            fx = 1.09  # fallback razonable para 2026

        total = 0.0
        for _, row in day.iterrows():
            tk     = row["ticker_yahoo"]
            moneda = row["moneda"]
            shares = row["shares"]

            if tk not in prices.columns:
                continue
            if d not in prices.index:
                continue

            price = float(prices.loc[d, tk])
            if pd.isna(price) or price <= 0:
                continue

            # Convertir a EUR según moneda
            if moneda == "USD":
                price_eur = price / fx
            elif moneda == "GBP":
                # Algunos .L cotizan en peniques (GBX): si precio > 100, dividir entre 100
                gbp_eur = fx * 0.86  # aproximación GBP/EUR
                if tk.endswith(".L") and price > 100:
                    price_eur = (price / 100) / gbp_eur
                else:
                    price_eur = price / gbp_eur
            elif moneda == "CHF":
                price_eur = price / (fx * 0.94)
            elif moneda == "CAD":
                price_eur = price / (fx * 1.36)
            else:
                # EUR — directo
                price_eur = price

            total += shares * price_eur

        daily[d] = total

    series = pd.Series(daily, name="valor_eur")
    series.index = pd.to_datetime(series.index)
    series = series.sort_index()

    # Eliminar días con valor 0 (no hay datos de precio ese día)
    series = series[series > 0]

    # Suavizar spikes puntuales (>35% variación diaria = precio erróneo)
    pct = series.pct_change().abs()
    mask = pct > 0.35
    if mask.any():
        print(f"   ⚠️  Interpolando {mask.sum()} spikes (>35% variación)")
        series = series.where(~mask).interpolate(method="time")

    return series

# ─── 6. CALCULAR LIQUIDEZ DIARIA ─────────────────────────────────────────────

LIQ_INICIO = 143_955  # 1 enero 2026: ING 73.011 + R4 69.135 + IBKR 1.809

def compute_daily_liquidity(df_pos: pd.DataFrame, df_sales: pd.DataFrame, dates_index: pd.DatetimeIndex) -> pd.Series:
    """
    Reconstruye la liquidez diaria exacta desde el Excel.
    Liquidez(día) = LIQ_INICIO + ventas_acumuladas - compras_acumuladas
    """
    print("\n💰 Calculando liquidez diaria...")

    all_dates = [d.date() for d in dates_index]

    # Compras realizadas en 2026
    compras_2026 = df_pos[df_pos["fecha_compra"] >= START_DATE][["fecha_compra", "cost_eur"]].copy()

    # Ventas en 2026
    if not df_sales.empty and "importe_eur" in df_sales.columns:
        ventas_2026 = df_sales[["fecha_venta", "importe_eur"]].copy()
    else:
        ventas_2026 = pd.DataFrame(columns=["fecha_venta", "importe_eur"])

    liq_diaria = {}
    liq = float(LIQ_INICIO)

    for d in all_dates:
        # Ventas del día: suman liquidez
        v_dia = ventas_2026[ventas_2026["fecha_venta"] == d]["importe_eur"].sum() if not ventas_2026.empty else 0
        # Compras del día: restan liquidez
        c_dia = compras_2026[compras_2026["fecha_compra"] == d]["cost_eur"].sum() if not compras_2026.empty else 0
        liq = liq + float(v_dia) - float(c_dia)
        liq_diaria[d] = round(max(liq, 0), 2)

    series = pd.Series(liq_diaria, name="liquidez_eur")
    series.index = pd.to_datetime(series.index)
    print(f"   → Inicio: {LIQ_INICIO:,.0f}€  |  Hoy: {liq:,.0f}€")
    return series


# ─── 7. GENERAR HTML ──────────────────────────────────────────────────────────

def generate_html(series: pd.Series, liq_series: pd.Series, anclas: dict, output: Path):
    print(f"\n📊 Generando gráfico HTML...")

    dates_str  = [d.strftime("%Y-%m-%d") for d in series.index.date]
    values     = [round(v, 2) for v in series.values.tolist()]
    n          = len(dates_str)

    # Alinear liquidez con el índice de títulos
    liq_aligned = liq_series.reindex(series.index, method="ffill").fillna(LIQ_INICIO)
    liq_values  = [round(v, 2) for v in liq_aligned.values.tolist()]

    # Total = títulos + liquidez
    total_values = [round(v + l, 2) for v, l in zip(values, liq_values)]

    # Anclas ordenadas (solo títulos — lo que tenemos verificado)
    ancla_dates  = [d.strftime("%Y-%m-%d") for d in sorted(anclas)]
    ancla_values = [anclas[d] for d in sorted(anclas)]

    v_inicio  = float(anclas.get(START_DATE, values[0]))
    v_actual  = float(values[-1])
    liq_actual = float(liq_values[-1])
    total_actual = v_actual + liq_actual

    variacion_titulos = v_actual - v_inicio
    pct_titulos = variacion_titulos / v_inicio * 100 if v_inicio else 0

    total_inicio = v_inicio + LIQ_INICIO
    variacion_total = total_actual - total_inicio
    pct_total = variacion_total / total_inicio * 100 if total_inicio else 0

    v_max = max(values); d_max = dates_str[values.index(v_max)]
    v_min = min(values); d_min = dates_str[values.index(v_min)]

    color_t = "#22c55e" if variacion_titulos >= 0 else "#ef4444"
    color_tot = "#22c55e" if variacion_total >= 0 else "#ef4444"
    signo_t   = "+" if variacion_titulos >= 0 else ""
    signo_tot = "+" if variacion_total >= 0 else ""

    def fmt(v): return f"{v:,.0f} €".replace(",", ".")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AppCartera — Evolución 2026</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0f1117;color:#e2e8f0;padding:24px}}
h1{{font-size:20px;font-weight:700;color:#f8fafc;margin-bottom:4px}}
.sub{{font-size:12px;color:#64748b;margin-bottom:20px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin-bottom:20px}}
.card{{background:#1e2130;border:1px solid #2d3148;border-radius:10px;padding:14px 18px}}
.card.highlight{{border-color:#3b82f6;background:#1a2035}}
.label{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:5px}}
.val{{font-size:20px;font-weight:700;color:#f8fafc}}
.val.pos{{color:#22c55e}}.val.neg{{color:#ef4444}}.val.blue{{color:#60a5fa}}
.sub2{{font-size:11px;color:#94a3b8;margin-top:2px}}
#chart{{background:#1e2130;border:1px solid #2d3148;border-radius:10px;padding:8px}}
.foot{{text-align:center;margin-top:14px;font-size:11px;color:#334155}}
</style>
</head>
<body>
<h1>📈 AppCartera — Evolución del valor total</h1>
<p class="sub">Desde 1 enero 2026 hasta hoy · Precios históricos Yahoo Finance · {END_DATE.strftime("%d/%m/%Y")}</p>
<div class="grid">
  <div class="card highlight">
    <div class="label">Total cartera hoy</div>
    <div class="val blue">{fmt(total_actual)}</div>
    <div class="sub2">Títulos + liquidez</div>
  </div>
  <div class="card">
    <div class="label">Títulos hoy</div>
    <div class="val">{fmt(v_actual)}</div>
    <div class="sub2">{signo_t}{fmt(variacion_titulos)} ({signo_t}{pct_titulos:.1f}% en 2026)</div>
  </div>
  <div class="card">
    <div class="label">Liquidez hoy</div>
    <div class="val">{fmt(liq_actual)}</div>
    <div class="sub2">ING + R4 + IBKR</div>
  </div>
  <div class="card">
    <div class="label">Variación total 2026</div>
    <div class="val {'pos' if variacion_total>=0 else 'neg'}">{signo_tot}{fmt(variacion_total)}</div>
    <div class="sub2">{signo_tot}{pct_total:.1f}% · inicio {fmt(total_inicio)}</div>
  </div>
  <div class="card">
    <div class="label">Máximo títulos 2026</div>
    <div class="val">{fmt(v_max)}</div>
    <div class="sub2">{d_max}</div>
  </div>
  <div class="card">
    <div class="label">Mínimo títulos 2026</div>
    <div class="val">{fmt(v_min)}</div>
    <div class="sub2">{d_min}</div>
  </div>
</div>
<div id="chart"></div>
<p class="foot">AppCartera · github.com/scalibur123/appcartera · Liquidez interpolada linealmente ene→hoy</p>
<script>
const dates={json.dumps(dates_str)};
const vals={json.dumps(values)};
const liq={json.dumps(liq_values)};
const total={json.dumps(total_values)};
const adates={json.dumps(ancla_dates)};
const avals={json.dumps(ancla_values)};

const trazaTitulos={{
  x:dates, y:vals, type:"scatter", mode:"lines", name:"Títulos",
  line:{{color:"{color_t}",width:2.5,shape:"spline",smoothing:0.4}},
  fill:"tozeroy", fillcolor:"{color_t}12",
  hovertemplate:"<b>%{{x}}</b><br>Títulos: %{{y:,.0f}} €<extra></extra>"
}};
const trazaLiq={{
  x:dates, y:liq, type:"scatter", mode:"lines", name:"Liquidez",
  line:{{color:"#94a3b8",width:1.5,dash:"dot"}},
  hovertemplate:"<b>%{{x}}</b><br>Liquidez: %{{y:,.0f}} €<extra></extra>"
}};
const trazaTotal={{
  x:dates, y:total, type:"scatter", mode:"lines", name:"Total (títulos+liquidez)",
  line:{{color:"#60a5fa",width:2.5,shape:"spline",smoothing:0.4}},
  hovertemplate:"<b>%{{x}}</b><br>Total: %{{y:,.0f}} €<extra></extra>"
}};
const trazaAnclas={{
  x:adates, y:avals, type:"scatter", mode:"markers", name:"Anclas reales (títulos)",
  marker:{{color:"#f59e0b",size:10,symbol:"diamond",line:{{color:"#fbbf24",width:1.5}}}},
  hovertemplate:"<b>%{{x}}</b><br>Ancla real: %{{y:,.0f}} €<extra></extra>"
}};
const layout={{
  paper_bgcolor:"transparent", plot_bgcolor:"transparent",
  font:{{family:"-apple-system,sans-serif",color:"#94a3b8"}},
  xaxis:{{gridcolor:"#1e293b",linecolor:"#334155",tickformat:"%b %Y",dtick:"M1",showgrid:true}},
  yaxis:{{gridcolor:"#1e293b",linecolor:"#334155",tickformat:",.0f",ticksuffix:" €",showgrid:true,range:[1700000,2500000]}},
  legend:{{bgcolor:"#1e2130",bordercolor:"#2d3148",borderwidth:1,font:{{size:12}},x:0.01,y:0.99,xanchor:"left",yanchor:"top"}},
  margin:{{t:20,b:60,l:110,r:20}}, height:480,
  hovermode:"x unified",
  hoverlabel:{{bgcolor:"#1e2130",bordercolor:"#334155",font:{{size:13,color:"#f8fafc"}}}}
}};
Plotly.newPlot("chart",[trazaTitulos,trazaLiq,trazaTotal,trazaAnclas],layout,{{responsive:true,displaylogo:false,modeBarButtonsToRemove:["lasso2d","select2d"]}});
</script>
</body>
</html>"""

    output.write_text(html, encoding="utf-8")
    print(f"   ✓ Guardado: {output}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  AppCartera — Gráfico histórico 2026")
    print("=" * 55)

    overrides = load_overrides()
    print(f"📋 Overrides: {len(overrides)} entradas")

    if not EXCEL_PATH.exists():
        sys.exit(f"❌ Excel no encontrado:\n   {EXCEL_PATH}")

    df_pos, df_sales = read_excel(EXCEL_PATH, overrides)

    if df_pos.empty:
        sys.exit("❌ Sin posiciones en el Excel.")

    # Mostrar tickers sin override (solo informativos)
    tickers_excel  = set(df_pos["ticker_raw"].unique())
    sin_override   = [t for t in tickers_excel if t not in overrides and df_pos[df_pos["ticker_raw"]==t]["moneda"].iloc[0]=="EUR"]
    if sin_override:
        print(f"\n⚠️  Tickers EUR sin override (se usarán tal cual): {sin_override}")

    df_shares = build_daily_shares(df_pos, df_sales)

    all_tickers = df_shares["ticker_yahoo"].unique().tolist()
    prices      = download_prices(all_tickers, START_DATE, END_DATE)

    series = compute_daily_value(df_shares, prices)

    if series.empty:
        sys.exit("❌ Sin datos de valor calculado.")

    # Resumen
    print(f"\n📊 Resumen:")
    print(f"   Primer dato : {series.index[0].date()} → {series.iloc[0]:,.0f} €")
    print(f"   Último dato : {series.index[-1].date()} → {series.iloc[-1]:,.0f} €")
    print(f"   Rango       : {series.min():,.0f} – {series.max():,.0f} €")

    # Comparar con anclas
    print(f"\n🎯 Comparación con anclas reales:")
    for d, v_real in sorted(ANCLAS.items()):
        ts = pd.Timestamp(d)
        if ts in series.index:
            v_calc = float(series.loc[ts])
        else:
            closest = min(series.index, key=lambda x: abs(x - ts))
            v_calc  = float(series.loc[closest])
        diff = v_calc - v_real
        pct  = diff / v_real * 100
        ico  = "✅" if abs(pct) < 5 else ("⚠️ " if abs(pct) < 15 else "❌")
        print(f"   {ico} {d}  real={v_real:>12,.0f}€  calc={v_calc:>12,.0f}€  dif={diff:>+10,.0f}€ ({pct:+.1f}%)")

    liq_series = compute_daily_liquidity(df_pos, df_sales, series.index)
    generate_html(series, liq_series, ANCLAS, OUTPUT_HTML)

    print(f"\n✅ Listo. Abre con:")
    print(f"   open {OUTPUT_HTML}")
    print("=" * 55)


if __name__ == "__main__":
    main()
