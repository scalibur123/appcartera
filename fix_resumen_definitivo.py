#!/usr/bin/env python3
"""
fix_resumen_definitivo.py
Aplica el nuevo cálculo de HOY/SEMANA/MES/ANUAL al index.html
y protege update_from_excel_v3.py para que el fix sobreviva cada `actualizar`.
"""

import sys
from pathlib import Path
from datetime import datetime

PROYECTO  = Path.home() / "APPCARTERA_NUEVA"
INDEX     = PROYECTO / "index.html"
PYTHON_SC = PROYECTO / "update_from_excel_v3.py"

NUEVO_BLOQUE_JS = (
    "const fmtR=(v)=>{const s=v<0;const abs=Math.abs(v);const parts=abs.toFixed(2).split('.');"
    "const int=parts[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.');return(s?'-':'+')+int+','+parts[1]+' \u20ac';};\n"
    "  const colorR=(v)=>v>=0?'var(--green)':'var(--red)';\n"
    "  const IRPF=0.20925;\n\n"
    "  function pintarBloque(idB,idN,val){\n"
    "    const valN=val*(1-IRPF);\n"
    "    const elB=document.getElementById(idB);\n"
    "    const elN=document.getElementById(idN);\n"
    "    if(elB) elB.innerHTML='<span style=\"color:'+colorR(val)+';font-size:20px;font-weight:500\">'+fmtR(val)+'</span>';\n"
    "    if(elN) elN.innerHTML='<span style=\"color:'+colorR(valN)+';font-size:20px;font-weight:500\">'+fmtR(valN)+'</span>';\n"
    "  }\n\n"
    "  function calcValorAhora(){\n"
    "    let v=0;\n"
    "    for(const i of C){const p=prices[i.symbol];if(p){const pe=i.moneda==='USD'&&eurUsd?p.price/eurUsd:p.price;v+=i.titulos*pe;}}\n"
    "    return v;\n"
    "  }\n\n"
    "  function ventasPeriodo(desde){\n"
    "    if(!window.VENTAS_ANUAL)return 0;\n"
    "    return VENTAS_ANUAL.filter(v=>v.fecha>=desde).reduce((s,v)=>s+v.bruto,0);\n"
    "  }\n\n"
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
    "  }\n\n"
    "  fetch('/snapshots').then(r=>r.json()).then(snaps=>{\n"
    "    if(!snaps||!snaps.length){console.warn('Sin snapshots');return;}\n"
    "    const ahora=new Date();\n"
    "    const hoy=ahora.toISOString().slice(0,10);\n"
    "    const lunesStr=(()=>{const d=new Date(ahora);d.setDate(d.getDate()-((d.getDay()+6)%7));return d.toISOString().slice(0,10);})();\n"
    "    const primerMes=hoy.slice(0,8)+'01';\n"
    "    const primerAnio=hoy.slice(0,4)+'-01-01';\n"
    "    function snapAntesDe(fechaRef){\n"
    "      const c=snaps.filter(s=>s.fecha<fechaRef).sort((a,b)=>b.fecha.localeCompare(a.fecha));\n"
    "      return c[0]||null;\n"
    "    }\n"
    "    const valorAhora=calcValorAhora();\n"
    "    const varHoyMercado=calcVarHoyMercado();\n"
    "    const ventasHoy=(window.VENTAS_ANUAL||[]).filter(v=>v.fecha===hoy).reduce((s,v)=>s+v.bruto,0);\n"
    "    pintarBloque('hoy-b','hoy-n',varHoyMercado+ventasHoy);\n"
    "    const sbs=snapAntesDe(lunesStr);\n"
    "    const sbm=snapAntesDe(primerMes);\n"
    "    const sba=snapAntesDe(primerAnio);\n"
    "    if(sbs) pintarBloque('sem-b','sem-n',(valorAhora-sbs.valor_total)+ventasPeriodo(lunesStr));\n"
    "    if(sbm) pintarBloque('mes-b','mes-n',(valorAhora-sbm.valor_total)+ventasPeriodo(primerMes));\n"
    "    if(sba) pintarBloque('anual-b','anual-n',(valorAhora-sba.valor_total)+ventasPeriodo(primerAnio));\n"
    "  }).catch(e=>{console.error('Error snapshots:',e);pintarBloque('hoy-b','hoy-n',calcVarHoyMercado());});"
)

MARCA_INI = "// HOY se pinta en el bloque de variaciones-diarias"
MARCA_FIN = ".catch(e=>console.error('Error variaciones-diarias:',e));"

FUNCION_PYTHON = '''
def asegurar_resumen_snapshots(html):
    """Garantiza que HOY/SEMANA/MES/ANUAL usa /snapshots + VENTAS_ANUAL."""
    if 'snapAntesDe' in html:
        return html
    MARCA_INI = '// HOY se pinta en el bloque de variaciones-diarias'
    MARCA_FIN = ".catch(e=>console.error('Error variaciones-diarias:',e));"
    if MARCA_INI not in html or MARCA_FIN not in html:
        return html
    nuevo = (
        "const fmtR=(v)=>{const s=v<0;const abs=Math.abs(v);const parts=abs.toFixed(2).split('.');"
        "const int=parts[0].replace(/\\\\B(?=(\\\\d{3})+(?!\\\\d))/g,'.');return(s?'-':'+')+int+','+parts[1]+' \\u20ac';};"
        "\\n  const colorR=(v)=>v>=0?'var(--green)':'var(--red)';\\n  const IRPF=0.20925;\\n\\n"
        "  function pintarBloque(idB,idN,val){\\n"
        "    const valN=val*(1-IRPF);\\n"
        "    const elB=document.getElementById(idB);\\n"
        "    const elN=document.getElementById(idN);\\n"
        "    if(elB) elB.innerHTML='<span style=\\"color:'+colorR(val)+';font-size:20px;font-weight:500\\">'+fmtR(val)+'</span>';\\n"
        "    if(elN) elN.innerHTML='<span style=\\"color:'+colorR(valN)+';font-size:20px;font-weight:500\\">'+fmtR(valN)+'</span>';\\n"
        "  }\\n\\n"
        "  function calcValorAhora(){\\n"
        "    let v=0;\\n"
        "    for(const i of C){const p=prices[i.symbol];if(p){const pe=i.moneda==='USD'&&eurUsd?p.price/eurUsd:p.price;v+=i.titulos*pe;}}\\n"
        "    return v;\\n  }\\n\\n"
        "  function ventasPeriodo(desde){\\n"
        "    if(!window.VENTAS_ANUAL)return 0;\\n"
        "    return VENTAS_ANUAL.filter(v=>v.fecha>=desde).reduce((s,v)=>s+v.bruto,0);\\n"
        "  }\\n\\n"
        "  function calcVarHoyMercado(){\\n"
        "    let v=0;\\n"
        "    for(const i of C){\\n"
        "      const p=prices[i.symbol];\\n"
        "      if(!p||p.pct==null)continue;\\n"
        "      const precioAyer=p.price/(1+p.pct/100);\\n"
        "      const varPrecio=p.price-precioAyer;\\n"
        "      const varEur=i.moneda==='USD'&&eurUsd?varPrecio*i.titulos/eurUsd:varPrecio*i.titulos;\\n"
        "      v+=varEur;\\n    }\\n    return v;\\n  }\\n\\n"
        "  fetch('/snapshots').then(r=>r.json()).then(snaps=>{\\n"
        "    if(!snaps||!snaps.length){console.warn('Sin snapshots');return;}\\n"
        "    const ahora=new Date();\\n"
        "    const hoy=ahora.toISOString().slice(0,10);\\n"
        "    const lunesStr=(()=>{const d=new Date(ahora);d.setDate(d.getDate()-((d.getDay()+6)%7));return d.toISOString().slice(0,10);})();\\n"
        "    const primerMes=hoy.slice(0,8)+'01';\\n"
        "    const primerAnio=hoy.slice(0,4)+'-01-01';\\n"
        "    function snapAntesDe(fechaRef){\\n"
        "      const c=snaps.filter(s=>s.fecha<fechaRef).sort((a,b)=>b.fecha.localeCompare(a.fecha));\\n"
        "      return c[0]||null;\\n    }\\n"
        "    const valorAhora=calcValorAhora();\\n"
        "    const varHoyMercado=calcVarHoyMercado();\\n"
        "    const ventasHoy=(window.VENTAS_ANUAL||[]).filter(v=>v.fecha===hoy).reduce((s,v)=>s+v.bruto,0);\\n"
        "    pintarBloque('hoy-b','hoy-n',varHoyMercado+ventasHoy);\\n"
        "    const sbs=snapAntesDe(lunesStr);\\n"
        "    const sbm=snapAntesDe(primerMes);\\n"
        "    const sba=snapAntesDe(primerAnio);\\n"
        "    if(sbs) pintarBloque('sem-b','sem-n',(valorAhora-sbs.valor_total)+ventasPeriodo(lunesStr));\\n"
        "    if(sbm) pintarBloque('mes-b','mes-n',(valorAhora-sbm.valor_total)+ventasPeriodo(primerMes));\\n"
        "    if(sba) pintarBloque('anual-b','anual-n',(valorAhora-sba.valor_total)+ventasPeriodo(primerAnio));\\n"
        "  }).catch(e=>{console.error('Error snapshots:',e);pintarBloque('hoy-b','hoy-n',calcVarHoyMercado());});"
    )
    ini = html.index(MARCA_INI)
    fin = html.index(MARCA_FIN) + len(MARCA_FIN)
    html = html[:ini] + nuevo + html[fin:]
    print('OK asegurar_resumen_snapshots aplicado')
    return html

'''

LLAMADA = "    nuevo_html = asegurar_resumen_snapshots(nuevo_html)\n"
ANCHOR  = "    nuevo_html = asegurar_historico(nuevo_html)\n"


def parchear_html():
    if not INDEX.exists():
        print(f"No encontrado: {INDEX}"); sys.exit(1)
    html = INDEX.read_text(encoding="utf-8")
    if "snapAntesDe" in html:
        print("index.html: parche ya aplicado."); return
    if MARCA_INI not in html or MARCA_FIN not in html:
        print("index.html: no se encontro el bloque antiguo.")
        print(f"  Busca: '{MARCA_INI}'")
        sys.exit(1)
    ini = html.index(MARCA_INI)
    fin = html.index(MARCA_FIN) + len(MARCA_FIN)
    nuevo = html[:ini] + NUEVO_BLOQUE_JS + html[fin:]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = INDEX.parent / f"index.html.backup_preresumen_{ts}"
    bak.write_text(html, encoding="utf-8")
    INDEX.write_text(nuevo, encoding="utf-8")
    print(f"OK index.html parcheado  (backup: {bak.name})")


def parchear_python():
    if not PYTHON_SC.exists():
        print(f"No encontrado: {PYTHON_SC}"); sys.exit(1)
    src = PYTHON_SC.read_text(encoding="utf-8")
    if "asegurar_resumen_snapshots" in src:
        print("update_from_excel_v3.py: funcion ya presente."); return
    if "def actualizar_index_html" not in src:
        print("No se encontro 'def actualizar_index_html'"); sys.exit(1)
    src = src.replace("def actualizar_index_html",
                      FUNCION_PYTHON + "def actualizar_index_html", 1)
    if ANCHOR in src:
        src = src.replace(ANCHOR, LLAMADA + ANCHOR, 1)
    else:
        print("AVISO: no se encontro 'asegurar_historico', añade la llamada manualmente.")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = PYTHON_SC.parent / f"update_from_excel_v3.py.backup_{ts}"
    bak.write_text(PYTHON_SC.read_text(encoding="utf-8"), encoding="utf-8")
    PYTHON_SC.write_text(src, encoding="utf-8")
    print(f"OK update_from_excel_v3.py parcheado  (backup: {bak.name})")


def main():
    print("=" * 50)
    print("fix_resumen_definitivo.py")
    print("=" * 50)
    parchear_html()
    parchear_python()
    print()
    print("Siguiente:")
    print("  git add index.html update_from_excel_v3.py")
    print("  git commit -m 'fix: HOY/SEMANA/MES/ANUAL via snapshots+ventas'")
    print("  git push")


if __name__ == "__main__":
    main()
