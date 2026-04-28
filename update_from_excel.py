import openpyxl, json, os, re
excel = os.path.expanduser("~/AppCartera_Data/PLUSVALIAS BOLSA 26_APP.xlsm")
index = os.path.expanduser("~/APPCARTERA_NUEVA/index.html")
wb = openpyxl.load_workbook(excel, data_only=True)
ws = wb['2026']
arr, seen = [], set()
for r in range(5, 259):
    t = ws[f'D{r}'].value
    if not t or t == '#VALUE!': continue
    t = str(t).strip()
    if t in seen: continue
    seen.add(t)
    tit = float(ws[f'K{r}'].value or 0)
    cst = float(ws[f'N{r}'].value or 0)
    if tit == 0: continue
    arr.append({'tckr': t, 'nombre': str(ws[f'B{r}'].value or t).strip(), 'titulos': round(tit, 2), 'coste_eur': round(cst, 2), 'precio_medio': round(cst/tit, 4), 'moneda': 'EUR', 'banco': '-', 'objetivo': None})
with open(index, 'r') as f: c = f.read()
new = 'const C=' + json.dumps(arr, separators=(',', ':')) + ';'
c = re.sub(r'const C=\[.*?\];', new, c, flags=re.DOTALL)
with open(index, 'w') as f: f.write(c)
print(f'Total: {len(arr)} valores')
