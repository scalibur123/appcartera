#!/usr/bin/env python3
"""arregla_diana_bancos.py
- Diana solo lee filas 11-220 y solo tickers vivos
- Si un ticker tiene varias filas en Diana, se queda con la primera
- Lee banco real desde col H de pestaña 2026 y lo normaliza
"""
from pathlib import Path
import re

sp = Path.home() / "APPCARTERA_NUEVA" / "update_from_excel_v3.py"
s = sp.read_text(encoding="utf-8")

mapa_bancos = '''
BANCO_NORMALIZE = {
    'r4': 'R4', 'R4': 'R4',
    'ing': 'ING', 'Ing': 'ING', 'ING': 'ING',
    'ibkr': 'IBKR', 'IBKR': 'IBKR', 'Ibkr': 'IBKR',
    'revolut': 'REVOLUT', 'Revolut': 'REVOLUT',
    'medio': 'MEDIOLANUM', 'MEDIO': 'MEDIOLANUM', 'Medio': 'MEDIOLANUM',
    'myinv': 'MYINV', 'Myinv': 'MYINV', 'MyInv': 'MYINV',
    'r4/ing': 'R4/ING', 'R4/ING': 'R4/ING', 'ing/r4': 'R4/ING',
    'medio/ing': 'MEDIO/ING', 'MEDIO/ING': 'MEDIO/ING', 'ing/medio': 'MEDIO/ING',
}

def normalizar_banco(b):
    if not b: return '-'
    b = str(b).strip()
    return BANCO_NORMALIZE.get(b, b.upper())

'''

if 'BANCO_NORMALIZE' not in s:
    s = re.sub(r'(\ndef cargar_overrides)', mapa_bancos + r'\1', s, count=1)
    print("OK normalizador de bancos anadido")
else:
    print("AVISO: BANCO_NORMALIZE ya existe")

old_diana = '''def leer_diana(wb):
    """Lee pestana DIANA y devuelve dict {ticker: objetivo_AC}"""
    if HOJA_DIANA not in wb.sheetnames:
        print(f"AVISO: pestana '{HOJA_DIANA}' no existe")
        return {}
    ws = wb[HOJA_DIANA]
    objetivos = {}
    # Cabeceras en fila 11, datos a partir de fila 12
    for row in range(12, ws.max_row + 1):
        ticker = ws[f"B{row}"].value  # col B = TCKR
        objetivo = ws[f"AC{row}"].value  # col AC = objetivo con dividendos
        if ticker and isinstance(ticker, str) and isinstance(objetivo, (int, float)):
            objetivos[ticker.strip()] = round(float(objetivo), 4)
    return objetivos'''

new_diana = '''def leer_diana(wb, tickers_vivos):
    """Lee Diana solo filas 11-220 y solo tickers que esten vivos en cartera.
    Si un ticker aparece varias veces, se queda con la primera."""
    if HOJA_DIANA not in wb.sheetnames:
        return {}
    ws = wb[HOJA_DIANA]
    objetivos = {}
    for row in range(12, 221):
        ticker = ws[f"B{row}"].value
        objetivo = ws[f"AC{row}"].value
        if not ticker or not isinstance(ticker, str): continue
        ticker = ticker.strip()
        if ticker not in tickers_vivos: continue
        if ticker in objetivos: continue
        if not isinstance(objetivo, (int, float)): continue
        objetivos[ticker] = round(float(objetivo), 4)
    return objetivos'''

if old_diana in s:
    s = s.replace(old_diana, new_diana)
    print("OK leer_diana actualizada (filas 11-220 + filtra tickers vivos)")
else:
    print("AVISO: leer_diana ya estaba modificada o no encontre el bloque exacto")

old_call = '''    # 1. Leer objetivos de Diana
    objetivos = leer_diana(wb)'''
new_call = '''    # Recopilar tickers vivos de pestana 2026
    tickers_vivos = set()
    for row in range(FILA_INI, FILA_FIN + 1):
        t = ws[f"D{row}"].value
        if t and str(t).strip():
            tickers_vivos.add(str(t).strip())
    # 1. Leer objetivos de Diana (solo tickers vivos)
    objetivos = leer_diana(wb, tickers_vivos)'''

if old_call in s:
    s = s.replace(old_call, new_call)
    print("OK llamada a leer_diana actualizada con tickers_vivos")
else:
    print("AVISO: llamada a leer_diana no encontrada o ya estaba modificada")

old_banco = '"banco": "-"'
new_banco = '"banco": normalizar_banco(ws[f"H{row}"].value)'

if old_banco in s:
    s = s.replace(old_banco, new_banco, 1)
    print("OK lectura de banco desde col H anadida")
else:
    print("AVISO: 'banco': '-' no encontrado o ya estaba modificado")

sp.write_text(s, encoding="utf-8")
print("\nOK update_from_excel_v3.py guardado")
