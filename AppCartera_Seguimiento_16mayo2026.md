# AppCartera — Seguimiento sesión 16 mayo 2026

---

## CAMBIOS REALIZADOS HOY

### 1. Pestaña Ventas
- Nueva pestaña en la app que muestra todas las ventas del año agrupadas por mes
- Muestra ticker, fecha, plusvalía bruta y neta de cada venta
- Muestra total anual arriba (bruto y neto)
- Los encabezados de mes tienen fondo gris oscuro para distinguirlos visualmente
- Se actualiza cada vez que ejecutas `actualizar` en Terminal
- Lee del Excel: pestaña 2026, filas 258-380, col D=ticker, col Q=fecha, col Y=bruto, col Z=neto

### 2. Snapshot diario y variaciones diarias
- Corregida la hora del snapshot: ahora se guarda a las **22:20 España (20:20 UTC)** con todos los mercados cerrados (Europa y USA)
- Corregido el uso de `getUTCHours()` en vez de `getHours()` para consistencia con servidor en UTC
- Añadida llamada a `guardarVariacionDiaria` después de cada snapshot — esto es lo que alimenta SEMANA/MES/ANUAL
- Reset de SEMANA: se hace el **domingo a las 23:59 España (21:59 UTC)**

### 3. Valores base fijados en Supabase (tabla variaciones_diarias)
- **2026-01-01**: 107.295,34 € — base ANUAL ajustada (105.456,34 + 1.839 para compensar mayo)
- **2026-05-01**: -1.839,00 € — base MES mayo (resultado acumulado de las dos primeras semanas de mayo)

### 4. Valores correctos en la app a fecha de hoy
- **HOY**: 0 € (es sábado, mercado cerrado) ✅
- **SEMANA**: 0 € (empieza el lunes) ✅
- **MES**: -1.839,00 € (acumulado mayo hasta hoy) ✅
- **ANUAL**: +105.456,34 € (acumulado real del año) ✅

---

## CÓMO FUNCIONA A PARTIR DEL LUNES

### Automático (sin hacer nada):
- Cada día laborable a las 22:20 España el servidor guarda el snapshot de la cartera
- Calcula la variación del día (precio hoy menos precio ayer) y la guarda en Supabase
- HOY se acumula en SEMANA, SEMANA en MES, MES en ANUAL

### Cuando ejecutas `actualizar`:
- Si has hecho ventas ese día o días anteriores, el Excel ya las tiene con su fecha real
- Ejecutar `actualizar` corrige cualquier desviación porque recalcula todo desde el Excel
- Las ventas se recogen por su fecha real de venta, no por la fecha en que actualizas

### Regla práctica:
- **HOY** puede no recoger una venta si la grabas al día siguiente — es normal
- **SEMANA** sí recogerá todas las ventas de la semana si ejecutas `actualizar` antes del domingo
- **MES y ANUAL** siempre correctos al ejecutar `actualizar`

---

## VERIFICAR ESTA SEMANA (lunes 18 a viernes 22 mayo)

Cada día entrar en **Supabase → tabla variaciones_diarias** y comprobar:

✅ Que aparece una fila nueva con la fecha del día laborable anterior  
✅ Que el valor es distinto de 0  

| Día a verificar | Fecha que debe aparecer | Acción si falta |
|----------------|------------------------|-----------------|
| Martes 19 | 2026-05-18 | Avisar — servidor no ejecutó snapshot |
| Miércoles 20 | 2026-05-19 | Avisar — servidor no ejecutó snapshot |
| Jueves 21 | 2026-05-20 | Avisar — servidor no ejecutó snapshot |
| Viernes 22 | 2026-05-21 | Avisar — servidor no ejecutó snapshot |

Si algún día falta la fila → abrir nueva sesión con Claude y revisar los logs de Render.

---

## COMANDO PARA ACTUALIZAR
```
actualizar
```
(alias configurado en Terminal — ejecuta python3 update_from_excel_v3.py + git add + commit + push)
