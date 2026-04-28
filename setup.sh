#!/bin/bash
# setup.sh - Instalacion completa de AppCartera v3
# Ejecutar:  bash setup.sh
# Hace todo en un solo paso. Sin nombres con corchetes ni problemas raros.

set -e

PROYECTO="$HOME/APPCARTERA_NUEVA"
cd "$PROYECTO"

echo ""
echo "============================================="
echo "  AppCartera v3 - Setup completo"
echo "============================================="
echo ""

# 1. Detectar donde esta el Excel
EXCEL=""
for ruta in \
    "$HOME/APPCARTERA_NUEVA/PLUSVALIAS BOLSA 26_APP.xlsm" \
    "$HOME/AppCartera_Data/PLUSVALIAS BOLSA 26_APP.xlsm" ; do
    if [ -f "$ruta" ]; then
        EXCEL="$ruta"
        break
    fi
done

if [ -z "$EXCEL" ]; then
    echo "❌ ERROR: No encuentro PLUSVALIAS BOLSA 26_APP.xlsm en:"
    echo "   - $HOME/APPCARTERA_NUEVA/"
    echo "   - $HOME/AppCartera_Data/"
    echo ""
    echo "Busca el archivo y muevelo a una de esas dos carpetas."
    exit 1
fi

echo "✅ Excel encontrado: $EXCEL"

# 2. Si esta en APPCARTERA_NUEVA, ajustar el path en update_from_excel_v3.py
if echo "$EXCEL" | grep -q "APPCARTERA_NUEVA"; then
    echo "ℹ️  Excel esta en APPCARTERA_NUEVA. Ajustando ruta en el script..."
    SCRIPT="update_from_excel_v3.py"
    if [ -f "$SCRIPT" ]; then
        # Backup
        cp "$SCRIPT" "$SCRIPT.bak"
        # Reemplazar la linea con la nueva ruta
        python3 - <<PYEOF
import re
ruta_nueva = '${EXCEL}'
with open('${SCRIPT}', 'r') as f:
    contenido = f.read()
nuevo = re.sub(
    r'EXCEL = HOME / "AppCartera_Data" / "PLUSVALIAS BOLSA 26_APP.xlsm"',
    f'EXCEL = Path("{ruta_nueva}")',
    contenido
)
with open('${SCRIPT}', 'w') as f:
    f.write(nuevo)
print("   ✅ Ruta del Excel actualizada en", '${SCRIPT}')
PYEOF
    fi
fi

# 3. Verificar que tickers_override.json existe
if [ ! -f "tickers_override.json" ]; then
    echo "⚠️  No existe tickers_override.json (no pasa nada, se usaran heuristicas)"
fi

# 4. Verificar que hay AO en el Excel
echo ""
echo "🔎 Comprobando si la macro VBA ya copio la columna B -> AO..."
TIENE_MIC=$(python3 -c "
import openpyxl
try:
    wb = openpyxl.load_workbook('$EXCEL', data_only=True, keep_vba=False)
    ws = wb['2026']
    cnt = 0
    for r in range(5, 30):
        v = ws[f'AO{r}'].value
        if v and '(' in str(v) and ':' in str(v):
            cnt += 1
    print(cnt)
except Exception as e:
    print(0)
")

if [ "$TIENE_MIC" -lt 5 ]; then
    echo ""
    echo "⚠️  La columna AO esta vacia o sin formato MIC."
    echo "   Esto significa que la macro VBA aun NO esta instalada."
    echo "   El script funcionara igualmente pero usando heuristicas (override + Madrid por defecto)."
    echo ""
    echo "   Para resultados PERFECTOS, instala la macro VBA siguiendo estos pasos:"
    echo "   1. Abre el Excel:  open '$EXCEL'"
    echo "   2. Pulsa Opcion+F11"
    echo "   3. Doble click en 'ThisWorkbook' (panel izquierdo)"
    echo "   4. Pega el contenido de macro_vba_AutoCopyMIC.txt"
    echo "   5. Cierra editor VBA y pulsa Cmd+S en el Excel"
    echo "   6. Vuelve a ejecutar bash setup.sh"
    echo ""
else
    echo "   ✅ La macro VBA ya esta funcionando ($TIENE_MIC tickers con MIC)"
fi

# 5. Ejecutar update_from_excel_v3.py
echo ""
echo "🚀 Regenerando index.html y tickers.json..."
python3 update_from_excel_v3.py

# 6. Validar
echo ""
read -p "¿Lanzar validate.py contra Yahoo? Tarda ~70s. [s/N] " RESP
if [[ "$RESP" =~ ^[sS]$ ]]; then
    python3 validate.py
fi

echo ""
echo "============================================="
echo "  ✅ Setup completado"
echo "============================================="
