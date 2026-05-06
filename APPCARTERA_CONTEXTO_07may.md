# AppCartera - Contexto sesión 7 mayo 2026

## App
- URL: https://appcartera.onrender.com
- Repo: github.com/scalibur123/appcartera (rama main, auto-deploy Render)
- Carpeta: ~/APPCARTERA_NUEVA
- Stack: HTML/JS + Node.js

## Workflow
- Editar → git add/commit/push → esperar 2-3min → cerrar/abrir PWA iPhone
- Para actualizar datos: python3 update_from_excel_v3.py → git add/commit/push

## Excel
- /Users/mabascal/Library/Mobile Documents/com~apple~CloudDocs/INVERSION/PLUSVALIAS BOLSA 26.xlsm
- Pestaña 2026: D=ticker, G=moneda, I=fecha_compra, K=titulos, N=coste EUR, filas 5-258
- Pestaña 2026 ejecuciones: filas 262-400, col Q=fecha venta, Y=plusvalia bruta, Z=neta
- Pestaña Semanal: col A=semana, C=+/- semanal 2026, F=total mensual/anual, F57=acumulado anual
- Pestaña Mensual: R13=bruto anual, S13=neto anual, J13=neto mensual, N13=sueldo bruto

## Snapshots Supabase (cartera_snapshots)
- 2025-12-31: 2085509.99 (base ANUAL)
- 2026-04-30: 2192805.33 (base MES)
- 2026-05-02: 2118684.67 (base SEMANA viernes anterior)
- 2026-05-05: 2214236.33 (lunes rally aranceles)
- Se guarda automaticamente cada dia a las 17:30

## Calculo HOY/SEMANA/MES/ANUAL
- HOY: variacion Yahoo + plusvalias realizadas hoy (PLUSV_HOY)
- SEMANA: valorAhora - snapshot_viernes + plusvalias semana (PLUSV_SEMANA)
- MES: RENDIMIENTO_MES (Excel) + varDesViernes + PLUSV_SEMANA
- ANUAL: RENDIMIENTO_ANUAL (Excel F57) + varDesViernes + PLUSV_SEMANA
- plusv_hoy y plusv_semana se leen automaticamente del Excel en cada ejecucion

## Servicios externos
- Render.com: hosting Node.js plan gratuito
- Supabase: ntvupakoulwiffvdcfox - tablas: historico_alertas, cartera_snapshots, earnings, alert_state (RLS activado)
- Firebase: appcartera123 (notificaciones push iPhone)
- Alpha Vantage: 9JNVRNFZ3D5VBP5E (earnings)

## Funcionalidades implementadas hoy 6-may
- Tarjeta Nomina en pestana Mensual (sueldo neto 12 pagas + neto est. 26)
- Alert state persistido en Supabase (sobrevive reinicios Render)
- HOY/SEMANA/MES/ANUAL calculados desde snapshots Supabase
- Modal al pulsar tarjetas objetivo/pendientes: ultimo estado de cada ticker
- Vista cartera: Mundo/Europa/USA con ordenacion dia/az/posicion/subidas/bajadas
- Detalle posicion al pulsar en Diana: compras desglosadas con fecha, cantidad, precio
- Plusvalias realizadas computan automaticamente en HOY/SEMANA/MES/ANUAL

## Pendiente
- Verificar HOY/SEMANA/MES/ANUAL con datos reales el sabado tras actualizar Investing
- Discrepancia 25000 euros cartera vs Excel: posibles sufijos bolsa incorrectos
