# AppCartera — Seguimiento sesión 17 mayo 2026

---

## ARQUITECTURA GENERAL

- **Servidor**: Node.js corriendo en local en `~/APPCARTERA_NUEVA/server.js`
- **Frontend**: `index.html` generado por `update_from_excel_v3.py` desde el Excel
- **Base de datos**: Supabase
- **Push**: Git → GitHub (el `actualizar` hace todo automáticamente)
- **Variables de entorno**: archivo `.env` en `~/APPCARTERA_NUEVA/` — el server.js lo carga al arrancar
- **Comando para actualizar todo**: `actualizar` en Terminal

---

## ESTRUCTURA DE ARCHIVOS CLAVE

```
~/APPCARTERA_NUEVA/
  index.html              ← generado por update_from_excel_v3.py
  server.js               ← servidor Node.js
  update_from_excel_v3.py ← script principal de actualización
  check-alerts.js         ← chequeo de alertas (cada 5 min desde server.js)
  notifications.js        ← envío de notificaciones Firebase
  supabase-client.js      ← cliente Supabase
  tickers.json            ← mapa ticker → símbolo Yahoo
  tickers_override.json   ← overrides manuales de símbolos Yahoo
  price-cache.json        ← caché de precios
  fcm-token.txt           ← token FCM para notificaciones push
  .env                    ← variables de entorno
```

---

## TABLAS SUPABASE

- `alert_state` — estado de alertas, incluye dia_state, base_semana, base_mes, base_anual
- `historico_alertas` — historial de alertas disparadas
- `cartera_snapshots` — snapshot diario del valor total (fecha, valor_total)
- `variaciones_diarias` — variación diaria calculada desde snapshots
- `earnings` — próximos earnings de valores en cartera
- `price_targets` — ya no se usa, puede borrarse

---

## EXCEL — ESTRUCTURA RELEVANTE

**Pestaña 2026:**
- Col D: ticker | Col E: precio | Col G: moneda | Col H: banco
- Col I: fecha compra | Col K: títulos | Col N: coste EUR
- Col Q: fecha venta | Col Y: plusvalía bruta | Col Z: plusvalía neta
- Col B / AO: nombre con formato "(MIC:TICKER)" para resolver símbolo Yahoo
- Filas 5-258: posiciones abiertas | Filas 262-400: ventas del año

**Pestaña DIANA:**
- Col B: ticker | Col AC: objetivo personal | Col AF: objetivo analistas (Investing.com)
- Filas 12-220

**Pestaña Mensual:** plusvalías anuales, netas, brutas, sueldo

---

## PESTAÑAS DE LA APP (orden en nav y swipe)

1. **Resumen** — valor total, HOY/SEMANA/MES/ANUAL, alertas del día
2. **Cartera** — lista de valores con precio, variación, B/P
3. **Diana** — valores cerca o en objetivo
4. **Mensual** — plusvalías realizadas, sueldo, datos fiscales
5. **Ventas** — ventas del año agrupadas por mes
6. **Historico** — historial de alertas disparadas
7. **Earnings** — próximos earnings
8. **Analistas** — valores por encima/debajo del objetivo de analistas. Tiene buscador.

**Array de tabs para swipe** (~línea 421):
```javascript
const tabs=['resumen','cartera','diana','mensual','ventas','historico','earnings','analistas'];
```

---

## DETALLE DE POSICIÓN

- Todos los precios a **2 decimales, sin símbolo de moneda**
- Máx 52 semanas en moneda original del ticker (sin convertir a EUR)
- Cada compra muestra su banco específico (col H de esa fila)
- Banco general = unión de todos los bancos: ej. `ING/R4`

---

## PESTAÑA ANALISTAS

- Lee de `const C` directamente — sin API externa
- Usa precios cargados en `prices`
- ⚠️ Rojo: precio >= objetivo analistas (considera venta)
- Verde: resto ordenado por upside
- Buscador por ticker en la parte superior
- Se actualiza con `actualizar` (lee col AF de Diana)

---

## SNAPSHOT Y VARIACIONES DIARIAS

- Snapshot: días laborables a las **22:20 España (20:20 UTC)**
- Reset SEMANA: domingos a las **23:59 España (21:59 UTC)**
- Bases en Supabase: `base_semana`, `base_mes`, `base_anual`

---

## ALERTAS (check-alerts.js)

- 🎯 Valor en objetivo | ⬇️ Salió de objetivo
- ⚠️ Cerca del objetivo (7%) | ↩️ Salió de pendientes
- 😊 Subida >5% en el día | 📈 Cerca del máximo 52s (3%)

---

## BANCOS Y SÍMBOLOS YAHOO

Bancos: se acumulan todos los distintos por ticker → `ING/R4`, `ING/MEDIOLANUM`, etc.

Cascada resolución símbolo Yahoo:
1. `tickers_override.json` (gana siempre)
2. Ticker ya tiene sufijo
3. MIC de col B o AO del Excel
4. `mic_nombres.txt` (fallback manual)
5. Heurística: USD → sin sufijo, EUR → `.MC`

---

## VERIFICACIÓN SEMANAL (18-22 mayo)

Supabase → tabla `variaciones_diarias`, fila nueva cada día laborable:

| Día | Fecha esperada |
|-----|---------------|
| Martes 19 | 2026-05-18 |
| Miércoles 20 | 2026-05-19 |
| Jueves 21 | 2026-05-20 |
| Viernes 22 | 2026-05-21 |

---

## SERVICIOS ACTIVOS

- Supabase, Firebase, GitHub, Alpha Vantage (earnings)

**Cerrar/ignorar:** Finnhub, FMP — no sirven para price targets en plan gratuito

---

## PROBLEMAS CONOCIDOS

**Pestaña Analistas desaparece tras `actualizar`:**
El Python la reinyecta automáticamente. Si falla, el patrón busca `</body>` en el index.html.

**`actualizar` sobreescribe fixes:**
El Python solo reemplaza `const C=[...]` y variables JS. Los fixes de `showDetalle` están en HTML estático. Si se sobreescriben, revisar que el `index.html` base ya tiene los fixes antes de `actualizar`.
