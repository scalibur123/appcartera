# AppCartera — Seguimiento sesión 17 mayo 2026

---

## ARQUITECTURA GENERAL

- **Servidor**: Node.js corriendo en local en `~/APPCARTERA_NUEVA/server.js`
- **Frontend**: `index.html` generado por `update_from_excel_v3.py` desde el Excel
- **Base de datos**: Supabase
- **Push**: Git → GitHub (el `actualizar` hace todo automáticamente)
- **Variables de entorno**: archivo `.env` en `~/APPCARTERA_NUEVA/` — el server.js lo carga al arrancar
- **Comando para actualizar todo**: `actualizar` en Terminal (alias que ejecuta python3 update_from_excel_v3.py + git add + commit + push)

---

## ESTRUCTURA DE ARCHIVOS CLAVE

```
~/APPCARTERA_NUEVA/
  index.html              ← generado por update_from_excel_v3.py
  server.js               ← servidor Node.js
  update_from_excel_v3.py ← script principal de actualización
  check-alerts.js         ← chequeo de alertas (llamado desde server.js cada 5 min)
  notifications.js        ← envío de notificaciones Firebase
  supabase-client.js      ← cliente Supabase
  tickers.json            ← mapa ticker → símbolo Yahoo (generado por update_from_excel_v3.py)
  tickers_override.json   ← overrides manuales de símbolos Yahoo
  price-cache.json        ← caché de precios (generado por server.js)
  fcm-token.txt           ← token FCM para notificaciones push
  .env                    ← variables de entorno (SUPABASE_URL, SUPABASE_KEY, etc.)
```

---

## TABLAS SUPABASE

- `alert_state` — estado de alertas (clave/valor), incluye dia_state, base_semana, base_mes, base_anual
- `historico_alertas` — historial de alertas disparadas
- `cartera_snapshots` — snapshot diario del valor total de la cartera (fecha, valor_total)
- `variaciones_diarias` — variación diaria calculada desde snapshots
- `earnings` — próximos earnings de los valores en cartera
- `price_targets` — **ya no se usa**, puede borrarse de Supabase

---

## EXCEL — ESTRUCTURA RELEVANTE

**Pestaña 2026:**
- Col D: ticker
- Col E: precio Excel
- Col G: moneda
- Col H: banco
- Col I: fecha compra
- Col K: títulos
- Col N: coste EUR
- Col Q: fecha venta
- Col Y: plusvalía bruta venta
- Col Z: plusvalía neta venta
- Col B / AO: nombre completo con formato "(MIC:TICKER)" para resolver símbolo Yahoo
- Filas 5-258: posiciones abiertas
- Filas 262-400: ventas del año

**Pestaña DIANA:**
- Col B: ticker
- Col AC: precio objetivo personal
- Col AF: precio objetivo consenso analistas (introducido manualmente desde Investing.com)
- Filas 12-220

**Pestaña Mensual:**
- Datos de plusvalías anuales, netas, brutas, sueldo

---

## PESTAÑAS DE LA APP (orden en nav y swipe)

1. **Resumen** — valor total, HOY/SEMANA/MES/ANUAL, alertas del día
2. **Cartera** — lista de valores con precio, variación, B/P
3. **Diana** — valores cerca o en objetivo
4. **Mensual** — plusvalías realizadas, sueldo, datos fiscales
5. **Ventas** — ventas del año agrupadas por mes
6. **Historico** — historial de alertas disparadas
7. **Earnings** — próximos earnings de valores en cartera
8. **Analistas** — valores por encima/debajo del objetivo de analistas (lee de `objetivo_analistas` en const C, que viene de col AF de Diana)

**Array de tabs para swipe** (línea ~421 de index.html):
```javascript
const tabs=['resumen','cartera','diana','mensual','ventas','historico','earnings','analistas'];
```

---

## DETALLE DE POSICIÓN

- Precio actual, B/P diario, B/P abiertas, Objetivo, Máx 52 semanas
- Todos los precios a **2 decimales**
- Lista de compras: cada línea muestra `N acc @ precio € [BANCO]` — el banco es específico de cada compra (col H de la fila correspondiente)
- El banco general del ticker es la unión de todos los bancos distintos: ej. `ING/R4`

---

## PESTAÑA ANALISTAS

- Lee directamente de `C` (const C en index.html) — sin API externa, sin Supabase
- Usa los precios ya cargados en la variable `prices` de la app
- Muestra valores donde `precio actual >= objetivo_analistas` en rojo (⚠️ considera venta)
- Resto de valores con objetivo definido ordenados por upside
- Se actualiza cada vez que ejecutas `actualizar` (lee col AF de Diana)
- **No hay ninguna API externa de analistas** — los datos los introduces tú manualmente en el Excel

---

## SNAPSHOT Y VARIACIONES DIARIAS

- Snapshot: días laborables a las **22:20 España (20:20 UTC)**
- Después del snapshot se llama a `guardarVariacionDiaria` automáticamente
- Reset SEMANA: domingos a las **23:59 España (21:59 UTC)**
- Bases en Supabase: `base_semana`, `base_mes`, `base_anual` en tabla `alert_state`

---

## ALERTAS (check-alerts.js)

Se ejecuta cada 5 minutos desde server.js. Detecta:
- 🎯 Valor en objetivo (precio >= objetivo)
- ⬇️ Valor salió de objetivo
- ⚠️ Valor cerca del objetivo (dentro del 7%)
- ↩️ Valor salió de pendientes
- 😊 Subida >5% en el día (una vez)
- 📈 Cerca del máximo de 52 semanas (dentro del 3%)

Estado guardado en Supabase tabla `alert_state` con clave `alert_state` y `dia_state`.

---

## NORMALIZACIÓN DE BANCOS

Mapa en `update_from_excel_v3.py`:
```python
BANCO_NORMALIZE = {
    'r4': 'R4', 'ing': 'ING', 'ibkr': 'IBKR',
    'revolut': 'REVOLUT', 'medio': 'MEDIOLANUM',
    'myinv': 'MYINV', ...
}
```
Si un ticker tiene posiciones en varios bancos, se muestra como `ING/R4`, `ING/MEDIOLANUM`, etc.

---

## RESOLUCIÓN DE SÍMBOLOS YAHOO

Cascada en `resolver_simbolo_yahoo`:
1. `tickers_override.json` (manual, gana siempre)
2. Ticker ya tiene sufijo (`.MC`, `.AS`, etc.)
3. MIC extraído de col B o AO del Excel (formato `"Nombre (MIC:TICKER)"`)
4. MIC de `mic_nombres.txt` (fallback manual)
5. Heurística por moneda: USD → sin sufijo, EUR → `.MC`

---

## VERIFICACIÓN SEMANAL (semana 18-22 mayo)

Comprobar en **Supabase → tabla variaciones_diarias** que aparece fila nueva cada día laborable:

| Día | Fecha esperada |
|-----|---------------|
| Martes 19 | 2026-05-18 |
| Miércoles 20 | 2026-05-19 |
| Jueves 21 | 2026-05-20 |
| Viernes 22 | 2026-05-21 |

Si falta alguna → revisar que el servidor está corriendo y que `price-cache.json` existe.

---

## SERVICIOS ACTIVOS

- **Supabase**: base de datos principal
- **Firebase**: notificaciones push
- **GitHub**: repositorio y push automático con `actualizar`
- **Alpha Vantage**: earnings calendar (variable `ALPHAVANTAGE_KEY` en `.env`)

**Servicios creados y abandonados (puedes cerrar):**
- Finnhub — no tiene price targets en plan gratuito
- Financial Modeling Prep (FMP) — solo devuelve 6 tickers de 193
