# 🚀 AppCartera v2 — Solución definitiva al problema de tickers

## Qué hay aquí

```
update_from_excel_v2.py    Lee Excel, regenera index.html y tickers.json
validate.py                 Compara precios Yahoo vs Excel, avisa de descuadres
server_v2.js                Backend con endpoint /audit añadido
audit.html                  Página visual de auditoría (vas a /audit.html)
tickers_override.json       Mapa MANUAL ticker → símbolo Yahoo (PRIORIDAD MÁXIMA)
```

## Cómo funciona

1. **`tickers_override.json` es la fuente de verdad humana.** Para cada ticker problemático, añades una línea con el símbolo Yahoo correcto. Una vez añadido, NUNCA MÁS se desajusta.

2. **`update_from_excel_v2.py`** lee el Excel, agrega posiciones por ticker, resuelve el símbolo Yahoo de cada uno (override manual > sufijo existente > USD directo > Madrid por defecto), y genera:
   - `tickers.json` (mapa interno con todo lo necesario)
   - `index.html` con la `const C` actualizada

3. **`validate.py`** llama a Yahoo para los 196 símbolos, compara el precio devuelto con el del Excel, y te muestra los desviados ordenados por % desviación. Si hay más de 5 desviados, devuelve exit code 1 (puedes usarlo como pre-commit hook).

4. **`server_v2.js`** añade el endpoint `/audit` que devuelve JSON con la auditoría completa, y `/audit.html` que es la versión visual.

## Workflow nuevo

```bash
# Cuando edites el Excel:
python3 update_from_excel_v2.py
python3 validate.py                # Te dice si hay desajustes ANTES de subir

# Si validate.py reporta tickers desviados:
#   1. Mira la fila del ticker problemático
#   2. Ve a https://finance.yahoo.com y busca el nombre del valor
#   3. Apunta el símbolo correcto (ej: "AMP.MC" en vez de "AMP")
#   4. Edita tickers_override.json y añade:  "AMP": "AMP.MC",
#   5. Re-ejecuta:  python3 update_from_excel_v2.py && python3 validate.py
#   6. Repite hasta que validate.py diga "✅ TODO LIMPIO"

# Cuando esté limpio:
git add -A && git commit -m "actualizar cartera" && git push
```

## Instalación inicial

Mover los archivos a `~/APPCARTERA_NUEVA/` y arrancar:

```bash
cd ~/APPCARTERA_NUEVA

# 1. Probar update local
python3 update_from_excel_v2.py

# 2. Probar validate local
python3 validate.py --max=20    # primero con 20 para ir rápido

# 3. Si todo OK, validar todos
python3 validate.py

# 4. Reemplazar server.js por server_v2.js
cp server.js server.js.OLD
cp server_v2.js server.js

# 5. Arrancar localmente para probar
node server.js
# Abrir http://localhost:3000/audit.html
```

## Si algo se rompe

Tienes backups automáticos de index.html cada vez que ejecutas update_from_excel_v2.py.
Para volver atrás:

```bash
ls ~/APPCARTERA_NUEVA/index.html.backup_*
cp ~/APPCARTERA_NUEVA/index.html.backup_YYYYMMDD_HHMMSS ~/APPCARTERA_NUEVA/index.html
```

## Por qué esta solución es definitiva

- **Idempotente**: el Excel es la fuente, los overrides persisten entre actualizaciones
- **Autoexplicativa**: la página `/audit.html` te dice exactamente qué falla
- **Atrapa errores ANTES del deploy**: nunca más subes y descubres -25.000 € de descuadre
- **No requiere tocar código**: solo añadir líneas al JSON
