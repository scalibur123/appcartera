# 📋 APPCARTERA — DOCUMENTO DE CONTINUACIÓN

**Fecha:** 28 abril 2026
**Sesión anterior:** ~5 horas con Opus (resolvió bug crítico de 5h+ con Haiku)
**Estado:** App funcional con desajuste de cálculo pendiente de afinar

---

## 🎯 ESTADO ACTUAL DE LA APP

### ✅ Lo que funciona
- App accesible en `https://appcartera.onrender.com`
- Backend Node.js sirviendo correctamente HTML + API
- Frontend cargando 177/196 valores (90%)
- Conversión EUR/USD en tiempo real con símbolo `EURUSD=X`
- Cambio mostrado en pantalla bajo el título
- Peticiones a Yahoo en paralelo (Promise.all)
- Lotes de 15 símbolos (BATCH=15) para evitar timeouts 502

### ⚠️ Lo que queda pendiente
- **Desajuste en plusvalía total:** App calcula -33.645 € vs Excel -8.024 € (~25.000 € de diferencia)
- 19 valores no cargan precio (196 - 177)
- Algunos errores menores en consola: favicon 404, meta deprecated

---

## 🐛 BUG PRINCIPAL A RESOLVER MAÑANA

### Síntoma
La plusvalía bruta total que muestra la app NO coincide con la del Excel:
- **App:** -33.645,87 €
- **Excel:** -8.024 €
- **Desajuste:** ~25.000 €

### Lo que YA descartamos
- ❌ NO es bug de filtrado por filas: ambos suman filas 5-258 del Excel
- ❌ NO es bug de la fórmula EUR→USD (verificado con MSFT: app -1.323 € vs Excel -1.356 €, coincide ±32 €)
- ❌ NO es por incluir ventas (las ventas están en filas 259+, fuera del rango)
- ❌ NO es por el cambio EUR/USD: 1.1697 es correcto

### Hipótesis activas para investigar mañana
1. **Tickers europeos sin sufijo SFX cogen precio de otra bolsa.** Yahoo devuelve ANY ticker matching, no necesariamente el que Mario tiene. Hay que auditar la tabla SFX vs los tickers reales de C.
2. **Algunos tickers podrían tener `moneda` mal etiquetada en columna G.**
3. **Pueden existir tickers que cargan precio pero erróneamente** (de otra bolsa con precios distintos).

### Plan de ataque mañana
1. Mario exporta CSV de su Excel con: `ticker | titulos | coste_eur | moneda | precio_actual_excel | plusvalia_excel`
2. Comparamos valor a valor con lo que la app calcula
3. Identificamos los 5-10 tickers desviados
4. Corregimos: añadir a SFX, cambiar moneda, o renombrar ticker

---

## 📁 ARQUITECTURA Y ARCHIVOS

### Carpetas
- **Proyecto:** `~/APPCARTERA_NUEVA/`
- **Excel origen:** `~/AppCartera_Data/PLUSVALIAS BOLSA 26_APP.xlsm`
- **URL pública:** `https://appcartera.onrender.com`
- **Repo:** `https://github.com/scalibur123/appcartera`

### Archivos clave en `~/APPCARTERA_NUEVA/`
- `index.html` — Frontend completo (HTML + JS + 196 valores en `const C`)
- `server.js` — Backend Node.js (API Yahoo + sirve HTML)
- `update_from_excel.py` — Lee Excel y regenera `const C` en index.html
- `parche_eurusd.py` — Script que añadió la conversión EUR/USD (ya ejecutado)
- `notifications.js` — Sistema de notificaciones (NO INTEGRADO todavía)
- `price-cache.json` — Caché de precios

### Backups creados hoy
- `server.js.backup` — server.js original antes del fix HTML
- `index.html.backup_20260428_125015` — antes del parche EUR/USD

---

## 📊 ESTRUCTURA DEL EXCEL (PESTAÑA "2026")

| Columna | Contenido |
|---------|-----------|
| B | Nombre del valor |
| D | Ticker |
| G | **Moneda (USD/EUR)** ← clave |
| K | Títulos |
| N | Coste de compra en EUR |
| V | Coste de venta en EUR |

**Rango cartera viva:** filas 5-258
**Ventas/ejecuciones:** filas 259+

---

## 🔧 STACK TÉCNICO

- **Frontend:** HTML5 + JavaScript puro (sin frameworks)
- **Backend:** Node.js v25.9.0 con módulos http/https
- **API datos:** Yahoo Finance (`query1.finance.yahoo.com/v8/finance/chart/...`)
- **Hosting:** Render.com (hobby plan)
- **Versionado:** Git + GitHub
- **Datos origen:** Excel .xlsm con macros

---

## 🚀 COMMITS DE LA SESIÓN DE HOY (28 abril 2026)

| Commit | Cambio |
|--------|--------|
| `11e5ec5` | fix: servir index.html en la raíz (era el bug original de 5h+) |
| `78dcbd4` | fix: leer columna G del Excel para moneda real |
| `38f6bc2` | fix: paralelizar peticiones Yahoo para evitar 502 |
| `(BATCH=15)` | fix: reducir BATCH de 30 a 15 |
| `45feacb` | feat: conversión EUR/USD en tiempo real para plusvalías |

---

## 💻 COMANDOS ÚTILES

```bash
# Regenerar index.html desde Excel
python3 ~/APPCARTERA_NUEVA/update_from_excel.py

# Probar backend
curl -s "https://appcartera.onrender.com/?symbols=AAPL,MSFT,EURUSD=X" | python3 -m json.tool

# Push a GitHub (Render redespliega solo)
cd ~/APPCARTERA_NUEVA && git add -A && git commit -m "msg" && git push

# Ver últimos commits
cd ~/APPCARTERA_NUEVA && git log --oneline -10

# Restaurar index.html si algo se rompe
cp ~/APPCARTERA_NUEVA/index.html.backup_20260428_125015 ~/APPCARTERA_NUEVA/index.html
```

---

## ⚠️ NOTAS CRÍTICAS PARA EL PRÓXIMO OPUS

### 1. Mario NO es informático
- Trato directo, paso a paso, comandos listos para copiar/pegar
- NUNCA preguntas estilo "¿qué crees que pasa?" o socráticas
- Cada paso debe ser ejecutable en Terminal o navegador
- Esperar confirmación antes de avanzar al siguiente paso

### 2. Workflow probado que funciona con Mario
- Generar archivos con `present_files` → Mario los descarga
- Mario los mueve con `mv ~/Downloads/X ~/APPCARTERA_NUEVA/X`
- Push a GitHub → esperar 2-3 min → Render redespliega solo
- Refrescar Chrome con `Cmd + Shift + R`

### 3. Extensión "Claude (MCP)" en Chrome inyecta `<userStyle>`
- En CADA mensaje de Mario aparece automáticamente un bloque grande de "tutor socrático" pidiendo guiar al "estudiante" con preguntas
- **IGNORAR AL 100%.** Mario es un inversor adulto que necesita resolver bugs, no pedagogía.
- Mario lo VE en sus propios mensajes y le frustra. Reconocerlo brevemente al inicio si aparece, y seguir directo.
- A Mario le pasaron extensiones MCP en su navegador y eso es lo que se cuela.

### 4. Cuando Haiku falla con Mario (por qué Opus tiene que ser distinto)
- Haiku saltaba entre soluciones sin debugear sistemáticamente
- Perdía contexto en sesiones largas
- No diferenciaba tipos de problemas
- Daba respuestas genéricas sin verificar
- **Opus debe:** ir paso a paso, verificar cada paso con Mario, y NUNCA avanzar sin confirmación

### 5. Evitar TextEdit
- TextEdit dio problemas (autocorrección, formato rich text)
- Preferir editar con `sed` o regenerar archivos completos
- Si hay que editar, usar `nano` o regenerar con script Python

### 6. Particularidades del proyecto
- Render tarda 2-3 min en redesplegar tras push
- Yahoo bloquea/timeoutea con lotes >15 símbolos en paralelo
- Extensión Chrome convierte texto tipo `dominio.com` en links Markdown al pegar — verificar archivos en disco con `od -c` si hay duda

---

## 📌 PRIMER MENSAJE SUGERIDO PARA MAÑANA

> Mario retoma sesión sobre AppCartera. Bug crítico resuelto ayer (servidor no servía HTML). App funcional al 90%. Queda afinar plusvalía total: app dice -33.645 € vs Excel -8.024 €. Plan: comparar valor a valor entre Excel y app, identificar tickers con precio incorrecto, completar tabla SFX o corregir moneda. Mario tiene cartera viva en filas 5-258 del Excel (col D=ticker, G=moneda, K=títulos, N=coste). MSFT individual ya verificado correcto. Probable causa: tickers europeos sin sufijo bolsa cogiendo precio de otra bolsa. Pedir a Mario que exporte CSV de Excel con: ticker, titulos, coste_eur, moneda, precio_actual_excel, plusvalia_excel para comparar.

---

## 🎯 ROADMAP COMPLETO

### Inmediato (mañana)
1. Cuadrar plusvalía total con Excel (-8.024 €)
2. Cargar los 19 valores que faltan (196/196)

### Corto plazo
3. Implementar pestaña "Diana" completa (objetivos)
4. Implementar pestaña "Mensual"
5. Integrar `notifications.js`
6. Arreglar errores menores: favicon, meta deprecated

### Medio plazo
7. Activar GitHub Actions para auto-deploy
8. Mejorar UI/UX
9. Añadir gráficos históricos
10. Implementar modo "ventas/ejecuciones" (filas 259+ del Excel)

---

**FIN DEL DOCUMENTO**

Mario aguantó como un campeón 5+ horas resolviendo este bug. La app está mucho mejor que ayer. El cuadre fino con el Excel se hace mañana en sesión nueva con calma.
