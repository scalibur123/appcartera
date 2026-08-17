from pathlib import Path
import sys, re, datetime
P = Path("index.html")
if not P.exists(): sys.exit("ERROR: no encuentro index.html")
s0 = P.read_text(encoding="utf-8")
tabs = sorted(set(re.findall(r"showTab\('([a-z]+)'", s0)))
if len(tabs) < 10: sys.exit(f"ERROR: index.html incompleto, solo {len(tabs)} pestanas: {tabs}. Abortado.")
s = s0; fallos = []
A1 = """  let b=0;
  for(const i of C){const p=prices[i.symbol];if(p){const pe=i.moneda==='USD'&&eurUsd?p.price/eurUsd:p.price;b+=i.titulos*pe-i.coste_eur;}}"""
B1 = """  let b=0, costeSinPrecio=0, sinPrecio=[];
  for(const i of C){const p=prices[i.symbol];
    if(p){const pe=i.moneda==='USD'&&eurUsd?p.price/eurUsd:p.price;b+=i.titulos*pe-i.coste_eur;}
    else{costeSinPrecio+=i.coste_eur;sinPrecio.push(i.tckr);}}
  (function(){
    const costeTot=C.reduce((a,i)=>a+i.coste_eur,0);
    if(costeSinPrecio<=0.005*costeTot)return;
    console.warn('Sin precio: '+sinPrecio.join(', '));
    const card=document.getElementById('card-ganancias');
    if(!card||document.getElementById('aviso-precios'))return;
    const d=document.createElement('div');d.id='aviso-precios';
    d.style.cssText='background:#4a2c00;color:#ffb84d;padding:8px;border-radius:8px;font-size:12px;margin-bottom:8px';
    d.textContent='\\u26a0 Sin precio para '+sinPrecio.length+' valores ('+
      Math.round(costeSinPrecio).toLocaleString('es-ES')+' \\u20ac de coste). Cifras incompletas.';
    card.parentNode.insertBefore(d,card);
  })();"""
if "costeSinPrecio" in s: print("1. aviso sin precio: ya estaba")
elif A1 in s: s = s.replace(A1, B1, 1); print("1. aviso sin precio: OK")
else: fallos.append("1. no localizo el calculo de b")
A2 = """  function pintarBloque(idB,idN,val){"""
B2 = """  function pintarBloque(idB,idN,val,nota){"""
A2b = """    if(elB) elB.innerHTML='<span style="color:'+colorR(val)+';font-size:20px;font-weight:500">'+fmtR(val)+'</span>';"""
B2b = """    const suf = nota ? '<span style="font-size:11px;color:var(--muted);font-weight:400"> '+nota+'</span>' : '';
    if(elB) elB.innerHTML='<span style="color:'+colorR(val)+';font-size:20px;font-weight:500">'+fmtR(val)+'</span>'+suf;"""
A2c = """        pintarBloque(cfg[0],cfg[1],(latenteAhora-base.latente)+ventasPeriodo(cfg[2])+divPeriodo(cfg[2]));"""
B2c = """        const MESES=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
        const pf=base.fecha.split('-');
        const nota='desde '+parseInt(pf[2],10)+' '+MESES[parseInt(pf[1],10)-1];
        pintarBloque(cfg[0],cfg[1],(latenteAhora-base.latente)+ventasPeriodo(cfg[2])+divPeriodo(cfg[2]),nota);"""
if "function pintarBloque(idB,idN,val,nota)" in s: print("2. fecha base: ya estaba")
elif A2 in s and A2b in s and A2c in s:
    s = s.replace(A2, B2, 1).replace(A2b, B2b, 1).replace(A2c, B2c, 1); print("2. fecha base: OK")
else: fallos.append("2. no localizo pintarBloque o su llamada")
A3 = "\ninitNotifications();"
B3 = "\n// autollamada quitada: iOS solo permite pedir permiso desde un gesto. Usa el boton."
if "autollamada quitada" in s: print("3. autollamada: ya estaba")
elif A3 in s: s = s.replace(A3, B3, 1); print("3. autollamada notificaciones: OK")
else: fallos.append("3. no localizo initNotifications()")
if fallos:
    print("\n".join("   " + f for f in fallos)); sys.exit("\nABORTADO. index.html NO se ha modificado.")
if sorted(set(re.findall(r"showTab\('([a-z]+)'", s))) != tabs:
    sys.exit("ABORTADO: el parche alteraria las pestanas.")
bak = Path(f"index.html.antes_parche_{datetime.datetime.now():%H%M%S}")
bak.write_text(s0, encoding="utf-8"); P.write_text(s, encoding="utf-8")
print(f"\nOK. {len(tabs)} pestanas intactas. Copia previa en {bak.name}")
