#!/usr/bin/env python3
"""Hace que renderDiana NO aplique el sort por distancia al objetivo cuando hay un sort manual activo."""
from pathlib import Path

p = Path.home() / "APPCARTERA_NUEVA" / "index.html"
s = p.read_text(encoding="utf-8")

old = 'data.sort((a,b)=>{const pa=prices[a.tckr]?.price,pb=prices[b.tckr]?.price;const da=pa?(pa-a.objetivo)/a.objetivo:-999,db=pb?(pb-b.objetivo)/b.objetivo:-999;return db-da;});'
new = 'if(!dSort){data.sort((a,b)=>{const pa=prices[a.tckr]?.price,pb=prices[b.tckr]?.price;const da=pa?(pa-a.objetivo)/a.objetivo:-999,db=pb?(pb-b.objetivo)/b.objetivo:-999;return db-da;});}'

if old in s:
    s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")
    print("OK fix aplicado: Diana respeta el sort manual")
else:
    print("AVISO: la linea exacta no se encontro")
