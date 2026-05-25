#!/usr/bin/env python3
"""
fix_hoy_mercado.py
Corrige calcVarHoyMercado() para que HOY solo use el pct de valores
cuyo mercado está abierto en este momento:
  - EUR: lunes-viernes 07:00-15:30 UTC
  - USD: lunes-viernes 13:30-20:00 UTC
Si el mercado de un valor está cerrado, su pct no se suma a HOY.
"""

import sys
from pathlib import Path
from datetime import datetime

PROYECTO  = Path.home() / "APPCARTERA_NUEVA"
INDEX     = PROYECTO / "index.html"
PYTHON_SC = PROYECTO / "update_from_excel_v3.py"

# ── Bloque antiguo a buscar ────────────────────────────────────────────────────
ANTIGUO = (
    "  function calcVarHoyMercado(){\n"
    "    let v=0;\n"
    "    for(const i of C){\n"
    "      const p=prices[i.symbol];\n"
    "      if(!p||p.pct==null)continue;\n"
    "      const precioAyer=p.price/(1+p.pct/100);\n"
    "      const varPrecio=p.price-precioAyer;\n"
    "      const varEur=i.moneda==='USD'&&eurUsd?varPrecio*i.titulos/eurUsd:varPrecio*i.titulos;\n"
    "      v+=varEur;\n"
    "    }\n"
    "    return v;\n"
    "  }"
)

# ── Bloque nuevo ───────────────────────────────────────────────────────────────
NUEVO = (
    "  function mercadoAbierto(moneda){\n"
    "    const ahora=new Date();\n"
    "    const dia=ahora.getUTCDay();\n"
    "    if(dia===0||dia===6)return false;\n"
    "    const h=ahora.getUTCHours();\n"
    "    const m=ahora.getUTCMinutes();\n"
    "    const mins=h*60+m;\n"
    "    if(moneda==='USD') return mins>=810&&mins<1200;  // 13:30-20:00 UTC\n"
    "    return mins>=420&&mins<930;  // 07:00-15:30 UTC (EUR y resto)\n"
    "  }\n"
    "  function calcVarHoyMercado(){\n"
    "    let v=0;\n"
    "    for(const i of C){\n"
    "      const p=prices[i.symbol];\n"
    "      if(!p||p.pct==null)continue;\n"
    "      if(!mercadoAbierto(i.moneda))continue;\n"
    "      const precioAyer=p.price/(1+p.pct/100);\n"
    "      const varPrecio=p.price-precioAyer;\n"
    "      const varEur=i.moneda==='USD'&&eurUsd?varPrecio*i.titulos/eurUsd:varPrecio*i.titulos;\n"
    "      v+=varEur;\n"
    "    }\n"
    "    return v;\n"
    "  }"
)


def parchear_html():
    if not INDEX.exists():
        print(f"No encontrado: {INDEX}"); sys.exit(1)
    html = INDEX.read_text(encoding="utf-8")
    if "mercadoAbierto" in html:
        print("index.html: parche ya aplicado."); return
    if ANTIGUO not in html:
        print("index.html: no se encontro calcVarHoyMercado exacta.")
        print("  Es posible que el formato difiera — revisa manualmente.")
        sys.exit(1)
    nuevo = html.replace(ANTIGUO, NUEVO, 1)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = INDEX.parent / f"index.html.backup_hoy_{ts}"
    bak.write_text(html, encoding="utf-8")
    INDEX.write_text(nuevo, encoding="utf-8")
    print(f"OK index.html parcheado  (backup: {bak.name})")


FUNCION_PYTHON = '''
def asegurar_mercado_abierto(html):
    """Garantiza que calcVarHoyMercado solo usa pct de mercados abiertos ahora."""
    if 'mercadoAbierto' in html:
        return html
    ANTIGUO = (
        "  function calcVarHoyMercado(){\\n"
        "    let v=0;\\n"
        "    for(const i of C){\\n"
        "      const p=prices[i.symbol];\\n"
        "      if(!p||p.pct==null)continue;\\n"
        "      const precioAyer=p.price/(1+p.pct/100);\\n"
        "      const varPrecio=p.price-precioAyer;\\n"
        "      const varEur=i.moneda===\\'USD\\'&&eurUsd?varPrecio*i.titulos/eurUsd:varPrecio*i.titulos;\\n"
        "      v+=varEur;\\n"
        "    }\\n"
        "    return v;\\n"
        "  }"
    )
    NUEVO = (
        "  function mercadoAbierto(moneda){\\n"
        "    const ahora=new Date();\\n"
        "    const dia=ahora.getUTCDay();\\n"
        "    if(dia===0||dia===6)return false;\\n"
        "    const h=ahora.getUTCHours();\\n"
        "    const m=ahora.getUTCMinutes();\\n"
        "    const mins=h*60+m;\\n"
        "    if(moneda===\\'USD\\') return mins>=810&&mins<1200;\\n"
        "    return mins>=420&&mins<930;\\n"
        "  }\\n"
        "  function calcVarHoyMercado(){\\n"
        "    let v=0;\\n"
        "    for(const i of C){\\n"
        "      const p=prices[i.symbol];\\n"
        "      if(!p||p.pct==null)continue;\\n"
        "      if(!mercadoAbierto(i.moneda))continue;\\n"
        "      const precioAyer=p.price/(1+p.pct/100);\\n"
        "      const varPrecio=p.price-precioAyer;\\n"
        "      const varEur=i.moneda===\\'USD\\'&&eurUsd?varPrecio*i.titulos/eurUsd:varPrecio*i.titulos;\\n"
        "      v+=varEur;\\n"
        "    }\\n"
        "    return v;\\n"
        "  }"
    )
    if ANTIGUO in html:
        html = html.replace(ANTIGUO, NUEVO, 1)
        print('OK asegurar_mercado_abierto aplicado')
    return html

'''

LLAMADA = "    nuevo_html = asegurar_mercado_abierto(nuevo_html)\n"
ANCHOR  = "    nuevo_html = asegurar_resumen_snapshots(nuevo_html)\n"
ANCHOR2 = "    nuevo_html = asegurar_historico(nuevo_html)\n"


def parchear_python():
    if not PYTHON_SC.exists():
        print(f"No encontrado: {PYTHON_SC}"); sys.exit(1)
    src = PYTHON_SC.read_text(encoding="utf-8")
    if "asegurar_mercado_abierto" in src:
        print("update_from_excel_v3.py: funcion ya presente."); return
    if "def actualizar_index_html" not in src:
        print("No se encontro 'def actualizar_index_html'"); sys.exit(1)
    src = src.replace("def actualizar_index_html",
                      FUNCION_PYTHON + "def actualizar_index_html", 1)
    # Insertar llamada: preferiblemente antes de asegurar_resumen_snapshots,
    # si no, antes de asegurar_historico
    if ANCHOR in src:
        src = src.replace(ANCHOR, LLAMADA + ANCHOR, 1)
    elif ANCHOR2 in src:
        src = src.replace(ANCHOR2, LLAMADA + ANCHOR2, 1)
    else:
        print("AVISO: añade manualmente 'asegurar_mercado_abierto(nuevo_html)' en actualizar_index_html.")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = PYTHON_SC.parent / f"update_from_excel_v3.py.backup_hoy_{ts}"
    bak.write_text(PYTHON_SC.read_text(encoding="utf-8"), encoding="utf-8")
    PYTHON_SC.write_text(src, encoding="utf-8")
    print(f"OK update_from_excel_v3.py parcheado  (backup: {bak.name})")


def main():
    print("=" * 50)
    print("fix_hoy_mercado.py")
    print("=" * 50)
    parchear_html()
    parchear_python()
    print()
    print("Siguiente:")
    print("  git add index.html update_from_excel_v3.py")
    print("  git commit -m 'fix: HOY solo suma pct de mercados abiertos'")
    print("  git push")


if __name__ == "__main__":
    main()
