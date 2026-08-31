import shutil, sys
from datetime import datetime
from pathlib import Path

IX = Path.home() / "APPCARTERA_NUEVA" / "index.html"

P = [
("let eurUsd=null;",
 "let eurUsd=null;let eurUsdAyer=null;"),

("eurUsd=fxRes['EURUSD=X'].price;",
 "eurUsd=fxRes['EURUSD=X'].price;"
 "eurUsdAyer=(fxRes['EURUSD=X'].pct!=null)?eurUsd/(1+fxRes['EURUSD=X'].pct/100):eurUsd;"),

("  function calcVarHoyMercado(){\n    let v=0;",
 "  function sesionComenzada(m){const a=new Date();const d=a.getUTCDay();"
 "if(d===0||d===6)return false;const t=a.getUTCHours()*60+a.getUTCMinutes();"
 "return m==='USD'?t>=810:t>=420;}\n"
 "  function calcVarHoyMercado(){\n    let v=0;const fxH=eurUsd,fxA=eurUsdAyer||eurUsd;"),

("if(!p||p.pct==null)continue;", "if(!p)continue;"),

("if(!mercadoAbierto(i.moneda))continue;", "if(!sesionComenzada(i.moneda))continue;"),

("      const precioAyer=p.price/(1+p.pct/100);\n"
 "      const varPrecio=p.price-precioAyer;\n"
 "      const varEur=i.moneda==='USD'&&eurUsd?varPrecio*i.titulos/eurUsd:varPrecio*i.titulos;\n"
 "      v+=varEur;",
 "      const pc=(p.pct==null)?0:p.pct;\n"
 "      const pAyer=p.price/(1+pc/100);\n"
 "      if(i.moneda==='USD'&&fxH&&fxA)v+=i.titulos*(p.price/fxH-pAyer/fxA);\n"
 "      else v+=i.titulos*(p.price-pAyer);"),

("  let tVal=0,tCoste=0,tDia=0;",
 "  let tVal=0,tCoste=0,tDia=0,tFx=0;const fxH=eurUsd,fxA=eurUsdAyer||eurUsd;"),

("    const pe=i.moneda==='USD'&&eurUsd?px/eurUsd:px;\n"
 "    const val=i.titulos*pe;\n"
 "    const ayer=pct?val/(1+pct/100):val;\n"
 "    const dia=val-ayer;",
 "    const usd=i.moneda==='USD'&&fxH&&fxA;\n"
 "    const pxAyer=px/(1+pct/100);\n"
 "    const val=usd?i.titulos*px/fxH:i.titulos*px;\n"
 "    const ayer=usd?i.titulos*pxAyer/fxA:i.titulos*pxAyer;\n"
 "    const dia=val-ayer;\n"
 "    const fxEfecto=usd?i.titulos*px*(1/fxH-1/fxA):0;"),

("val:val,pct:pct,dia:dia,coste:i.coste_eur});",
 "val:val,pct:pct,dia:dia,fx:fxEfecto,coste:i.coste_eur});"),

("    tVal+=val;tCoste+=i.coste_eur;tDia+=dia;",
 "    tVal+=val;tCoste+=i.coste_eur;tDia+=dia;tFx+=fxEfecto;"),

("function tarjeta(bandera,val,dia,coste,n,clave){",
 "function tarjeta(bandera,val,dia,coste,n,clave,fx){"),

("+'<div style=\"font-size:11px;color:'+cl(rt)+';margin-top:4px\">rent. '+sg(rt)+fNum(rt)+'%</div></div>';",
 "+(Math.abs(fx||0)>=1?'<div style=\"font-size:10px;color:var(--muted)\">de los que '"
 "+sg(fx)+fE(fx)+' es divisa</div>':'')"
 "+'<div style=\"font-size:11px;color:'+cl(rt)+';margin-top:4px\">rent. '+sg(rt)+fNum(rt)+'%</div></div>';"),

("dia:b.v.reduce((a,x)=>a+x.dia,0), coste:b.v.reduce((a,x)=>a+x.coste,0), n:b.v.length};",
 "dia:b.v.reduce((a,x)=>a+x.dia,0), fx:b.v.reduce((a,x)=>a+x.fx,0), "
 "coste:b.v.reduce((a,x)=>a+x.coste,0), n:b.v.length};"),

("x.n+' val.',x.k)).join('')", "x.n+' val.',x.k,x.fx)).join('')"),

("C.length+' val.',null)", "C.length+' val.',null,tFx)"),
]

if not IX.exists():
    sys.exit("No encuentro " + str(IX))
h = IX.read_text(encoding="utf-8")
if "eurUsdAyer" in h:
    sys.exit("Ya estaba aplicado. No se toca nada.")
mal = [str(i + 1) for i, (v, _) in enumerate(P) if h.count(v) != 1]
if mal:
    sys.exit("index.html inesperado en los parches " + ",".join(mal) + ". No se ha tocado nada.")
c = IX.parent / ("index.html.backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
shutil.copy2(IX, c)
for v, n in P:
    h = h.replace(v, n, 1)
IX.write_text(h, encoding="utf-8")
print("OK: " + str(len(P)) + " cambios aplicados. Backup: " + c.name)
print("eurUsdAyer aparece " + str(h.count("eurUsdAyer")) + " veces (esperado 4)")
