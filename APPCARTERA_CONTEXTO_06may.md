# AppCartera - Contexto sesión 6 mayo 2026

## App
- URL: https://appcartera.onrender.com
- Repo: github.com/scalibur123/appcartera (rama main, auto-deploy Render)
- Carpeta: ~/APPCARTERA_NUEVA
- Stack: HTML/JS + Node.js

## Mario
- No programador, necesita comandos copy-paste Mac
- Workflow: editar → git add/commit/push → esperar 2-3min → refrescar PWA iPhone

## Excel
- /Users/mabascal/Library/Mobile Documents/com~apple~CloudDocs/INVERSION/PLUSVALIAS BOLSA 26.xlsm
- Pestaña 2026: D=ticker, G=moneda, K=títulos, N=coste EUR, filas 5-258
- Pestaña 2026 ejecuciones: filas 262-400, col Q=fecha venta, Y=plusvalía bruta, Z=neta
- Pestaña dividendos 26: col A=fecha, H=total bruto, I=total neto
- Pestaña Semanal: col A=semana, B=+/- semanal 2026, col F=total mensual 2026
- Pestaña IRPF: F35=tipo efectivo IRPF (~20.98%)
- Pestaña Mensual: R13=bruto anual, S13=neto anual, J13=neto mensual

## Servicios externos
- Render.com: hosting Node.js plan gratuito
- Supabase: ntvupakoulwiffvdcfox
  - Tablas: historico_alertas, cartera_snapshots, earnings
  - Credenciales en ~/APPCARTERA_NUEVA/.env (NO en repo)
- Firebase: appcartera123 (notificaciones push iPhone)
- Alpha Vantage API key: 9JNVRNFZ3D5VBP5E (earnings calendar)
- Variables Render: FIREBASE_CREDENTIALS, SUPABASE_URL, SUPABASE_KEY, ALPHAVANTAGE_KEY

## Archivos clave
- server.js: servidor Node.js, rutas HTTP, chequeo alertas cada 5min, snapshot cartera 17:30
- check-alerts.js: notificaciones push (en objetivo, pendiente <7%, máximo 52s)
- notifications.js: envío FCM con collapse-id anti-duplicados
- update_from_excel_v3.py: actualiza todo desde Excel + earnings Alpha Vantage
- tickers.json: mapa ticker→símbolo Yahoo Finance (SE COMMITEA al repo)
- .env: credenciales Supabase locales (NO se commitea)

## Funcionalidades implementadas
- 196 valores Yahoo Finance tiempo real
- Resumen: plusvalías en vivo, card Cartera·Valores (HOY/SEMANA/MES/ANUAL), contadores +/- día
- Cartera: filtros, búsqueda por ticker Y nombre, % sobre precio compra
- Diana: filtros combinables por grupos (zona/estado/banco dropdown), orden cercanía objetivo
- Mensual: bruto/neto + equivalencia salarial IRPF Cataluña
- Historico: alertas Supabase
- Earnings: próximos resultados desde Alpha Vantage, fechas en ámbar
- Push notifications: en objetivo, salió, pendiente <7%, max52s, collapse-id anti-duplicados
- Pull-to-refresh
- Swipe lateral con animación entre pestañas
- Snapshot diario cartera en Supabase a las 17:30 laborables
- EUR/USD con flecha variación día

## Pendiente
- ESTA SEMANA: acumula solo hoy (lunes). Desde mañana usará snapshots Supabase para semana real
- Notificaciones duplicadas iPhone: problema iOS, no del servidor
- Discrepancia ~25.000€ cartera vs Excel: posibles sufijos bolsa incorrectos en tickers

## Mario IRPF
- 53 años, casado, 2 hijos, Cataluña, custodia compartida
- SS 3.4%, tramos estatales + autonómicos Cataluña
