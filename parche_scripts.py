import shutil, sys
from datetime import datetime
from pathlib import Path

D = Path.home() / "APPCARTERA_NUEVA"

BLOQUE = '''
# Wall Street cierra a las 22:00 hora espanola (21:00 en las pocas semanas de
# desfase entre el cambio de hora de EEUU y el de Europa). A las 22:10 la sesion
# esta cerrada SIEMPRE.
CIERRE_USA_LOCAL = (22, 10)


def _usa_ya_cerro(ahora=None):
    """True si la sesion de Wall Street de HOY ya ha cerrado."""
    ahora = ahora or datetime.now()
    return (ahora.hour, ahora.minute) >= CIERRE_USA_LOCAL


def _dia_provisional(f, hay_usd):
    """True si el dia f no se puede dar por cerrado todavia: es hoy, hay
    posiciones en dolares y Wall Street sigue abierta. Los precios USA que
    devuelve Yahoo son entonces intradia, no cierres, y publicar ese dia hace
    que ESTA SEMANA reste contra una base falsa."""
    if not hay_usd:
        return False
    return f == date.today() and not _usa_ya_cerro()

'''

PR = {
"reconstruir_historico.py": [

('UA = {"User-Agent": "Mozilla/5.0"}\n',
 'UA = {"User-Agent": "Mozilla/5.0"}\n' + BLOQUE),

('    pub = sorted(str(x["fecha"]) for x in serie_out if not x["incompleto"])',
 '    pub = sorted(str(x["fecha"]) for x in serie_out\n'
 '                 if not x["incompleto"] and not x.get("provisional"))'),

('        falta_coste = 0.0\n        falta_tckrs = []\n',
 '        falta_coste = 0.0\n        falta_tckrs = []\n        n_usd = 0\n'),

('            valor += p["titulos"] * pe\n            coste += p["coste"]\n            n_pos += 1\n',
 '            valor += p["titulos"] * pe\n            coste += p["coste"]\n            n_pos += 1\n'
 '            if p["moneda"] == "USD":\n                n_usd += 1\n'),

('                          "n_pos": n_pos, "falta_coste": falta_coste, "falta_tckrs": falta_tckrs,\n'
 '                          "coste_abierto": coste_abierto, "incompleto": incompleto})',
 '                          "n_pos": n_pos, "n_usd": n_usd,\n'
 '                          "falta_coste": falta_coste, "falta_tckrs": falta_tckrs,\n'
 '                          "coste_abierto": coste_abierto, "incompleto": incompleto,\n'
 '                          "provisional": _dia_provisional(f, n_usd > 0)})'),

('        elif not x["incompleto"] and f < hoy_str:',
 '        elif not x["incompleto"] and not x["provisional"] and f < hoy_str:'),

('    serie_json = {\n'
 '        "generado": datetime.now().isoformat(timespec="seconds"),\n'
 '        "ultimo_dia": str(ult["fecha"]),\n'
 '        "latente_ultimo": round(ult["latente"], 2),\n'
 '        "coste_ultimo": round(ult["coste"], 2),\n'
 '        "serie": {str(s["fecha"]): round(s["latente"], 2)\n'
 '                  for s in serie_out if not s["incompleto"]},',
 '    provisionales = [str(s["fecha"]) for s in serie_out if s["provisional"]]\n'
 '    publicados = [s for s in serie_out if not s["incompleto"] and not s["provisional"]]\n'
 '    serie_json = {\n'
 '        "generado": datetime.now().isoformat(timespec="seconds"),\n'
 '        # ultimo_dia es el ultimo dia PUBLICADO, o sea el ultimo cierre bueno.\n'
 '        "ultimo_dia": str(publicados[-1]["fecha"]) if publicados else None,\n'
 '        "ultimo_calculado": str(ult["fecha"]),\n'
 '        "latente_ultimo": round(publicados[-1]["latente"], 2) if publicados else None,\n'
 '        "coste_ultimo": round(publicados[-1]["coste"], 2) if publicados else None,\n'
 '        "provisionales": provisionales,\n'
 '        "serie": {str(s["fecha"]): round(s["latente"], 2) for s in publicados},'),

('    print(f"💾 Serie JSON: {n_pub} dias publicados de {len(serie_out)} calculados "\n'
 '          f"en {SALIDA_JSON.name}")',
 '    print(f"💾 Serie JSON: {n_pub} dias publicados de {len(serie_out)} calculados "\n'
 '          f"en {SALIDA_JSON.name}")\n'
 '    if provisionales:\n'
 '        barra("⚠️  DIA NO PUBLICADO: WALL STREET SIGUE ABIERTA")\n'
 '        print(f"   {\', \'.join(provisionales)} se ha calculado pero NO se publica.")\n'
 '        print("   Los precios USA de Yahoo son ahora intradia, no cierres: si se")\n'
 '        print("   guardaran, manana ESTA SEMANA restaria contra una base falsa.")\n'
 '        print("   Vuelve a ejecutar despues de las 22:10 para grabar el cierre bueno.")\n'
 '        print(f"   La base sigue siendo {serie_json[\'ultimo_dia\']}, que es correcto.")'),
],

"update_from_excel_v3.py": [

('    if d.weekday() < 5 and ahora.hour >= 18:\n        return d',
 '    # Antes bastaba con las 18:00 (cierre europeo), pero con mas de 90 posiciones\n'
 '    # en dolares eso grababa el dia con Wall Street a medio camino: el "cierre"\n'
 '    # guardado era un precio intradia y ESTA SEMANA restaba contra una base falsa.\n'
 '    if d.weekday() < 5 and (ahora.hour, ahora.minute) >= (22, 10):\n        return d'),
],
}

hechos = []
for nombre, parches in PR.items():
    f = D / nombre
    if not f.exists():
        sys.exit("No encuentro " + str(f))
    t = f.read_text(encoding="utf-8")
    if "22, 10" in t or "CIERRE_USA_LOCAL" in t:
        print(nombre + ": ya estaba aplicado, se salta.")
        continue
    mal = [str(i + 1) for i, (v, _) in enumerate(parches) if t.count(v) != 1]
    if mal:
        sys.exit(nombre + ": no encaja en los parches " + ",".join(mal) + ". No se ha tocado nada.")
    hechos.append((f, t, parches))

for f, t, parches in hechos:
    c = f.parent / (f.name + ".backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(f, c)
    for v, n in parches:
        t = t.replace(v, n, 1)
    f.write_text(t, encoding="utf-8")
    print("OK " + f.name + ": " + str(len(parches)) + " cambios. Backup: " + c.name)

import py_compile
for nombre in PR:
    py_compile.compile(str(D / nombre), doraise=True)
print("Los dos scripts compilan correctamente.")
