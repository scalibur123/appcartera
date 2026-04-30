#!/usr/bin/env python3
"""Calcula el % cambio del dia desde previousClose si Yahoo devuelve null."""
from pathlib import Path

p = Path.home() / "APPCARTERA_NUEVA" / "server.js"
s = p.read_text(encoding="utf-8")

old = """            symbol: m.symbol || symbol,
            price: m.regularMarketPrice,
            currency: m.currency,
            exchange: m.fullExchangeName || m.exchangeName,
            changePct: m.regularMarketChangePercent || 0,
            longName: m.longName || m.shortName || null"""

new = """            symbol: m.symbol || symbol,
            price: m.regularMarketPrice,
            currency: m.currency,
            exchange: m.fullExchangeName || m.exchangeName,
            changePct: (m.regularMarketChangePercent != null) ? m.regularMarketChangePercent : ((m.regularMarketPrice && m.chartPreviousClose) ? ((m.regularMarketPrice - m.chartPreviousClose) / m.chartPreviousClose) * 100 : 0),
            longName: m.longName || m.shortName || null"""

if old in s:
    s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")
    print("OK changePct calculado desde previousClose")
else:
    print("AVISO: bloque no encontrado en server.js")
    # Mostrar el bloque actual para diagnostico
    import re
    m = re.search(r"changePct:[^,]+", s)
    if m:
        print(f"Linea actual: {m.group(0)}")
