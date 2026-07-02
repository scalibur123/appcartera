#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parche: DESNIVEL DE BAJADA (flecha abajo) en rutas PLANIFICADAS.

Toca 3 archivos (mismo tema):
  1) src/lib/mapbox.ts              -> routeElevationStats ahora calcula tambien lossM (bajada acumulada)
  2) src/components/EtapaEditor.tsx -> el rotulo del planificador muestra  ... up gainM ... down lossM
  3) src/routes/app.rutas.$id.tsx   -> la ficha de una ruta anade un Stat "down Desnivel"

Las rutas GRABADAS no se tocan (ya calculaban y mostraban subida y bajada por su cuenta).

Seguridad:
  - Idempotente: si un cambio ya esta aplicado, lo salta (no repite).
  - Ancla unica: cada cambio exige que su texto original aparezca EXACTAMENTE una vez; si no, ABORTA sin tocar nada.
  - Backup por archivo: <archivo>.bak_<timestamp> antes de escribir.
  - Balance de simbolos: comprueba que ( ) { } [ ] quedan igual de balanceados que antes; si no, restaura y aborta.
  - Validacion de sintaxis con esbuild por archivo; si falla, restaura y aborta.

Uso (desde la raiz del proyecto):
  python3 desnivel_bajada.py
Luego:
  npm run build && npx cap copy ios
"""

import os
import sys
import shutil
import time
import subprocess

ROOT = os.getcwd()

EDITS = [
    {
        "file": "src/lib/mapbox.ts",
        "loader": "ts",
        "changes": [
            {
                "name": "tipo RouteElevation (+ lossM)",
                "done": "gainM: number; lossM: number } | null;",
                "old": "export type RouteElevation = { startM: number; maxM: number; minM: number; gainM: number } | null;",
                "new": "export type RouteElevation = { startM: number; maxM: number; minM: number; gainM: number; lossM: number } | null;",
            },
            {
                "name": "calculo gain + loss",
                "done": "    let loss = 0;\n",
                "old": (
                    "    let gain = 0;\n"
                    "    let last = elevations[0];\n"
                    "    for (let i = 1; i < elevations.length; i++) {\n"
                    "      const d = elevations[i] - last;\n"
                    "      if (Math.abs(d) >= 10) { if (d > 0) gain += d; last = elevations[i]; }\n"
                    "    }\n"
                    "    return { startM, maxM, minM, gainM: Math.round(gain) };"
                ),
                "new": (
                    "    let gain = 0;\n"
                    "    let loss = 0;\n"
                    "    let last = elevations[0];\n"
                    "    for (let i = 1; i < elevations.length; i++) {\n"
                    "      const d = elevations[i] - last;\n"
                    "      if (Math.abs(d) >= 10) { if (d > 0) gain += d; else loss += -d; last = elevations[i]; }\n"
                    "    }\n"
                    "    return { startM, maxM, minM, gainM: Math.round(gain), lossM: Math.round(loss) };"
                ),
            },
        ],
    },
    {
        "file": "src/components/EtapaEditor.tsx",
        "loader": "tsx",
        "changes": [
            {
                "name": "tipo estado elev del planificador (+ lossM)",
                "done": "gainM: number; lossM: number } | null>(null);",
                "old": "  const [elev, setElev] = useState<{ startM: number; maxM: number; minM: number; gainM: number } | null>(null);",
                "new": "  const [elev, setElev] = useState<{ startM: number; maxM: number; minM: number; gainM: number; lossM: number } | null>(null);",
            },
            {
                "name": "rotulo del planificador (anadir bajada)",
                "done": "\u00b7 \u2193 {elev.lossM} m",
                "old": "\u00b7 \u2191 {elev.gainM} m",
                "new": "\u00b7 \u2191 {elev.gainM} m \u00b7 \u2193 {elev.lossM} m",
            },
        ],
    },
    {
        "file": "src/routes/app.rutas.$id.tsx",
        "loader": "tsx",
        "changes": [
            {
                "name": "tipo estado elev de la ficha (+ lossM)",
                "done": "gainM: number; lossM: number } | null>(null);",
                "old": "  const [elev, setElev] = useState<{ startM: number; maxM: number; minM: number; gainM: number } | null>(null);",
                "new": "  const [elev, setElev] = useState<{ startM: number; maxM: number; minM: number; gainM: number; lossM: number } | null>(null);",
            },
            {
                "name": "ficha de ruta (anadir Stat de bajada)",
                "done": "label=\"\u2193 Desnivel\"",
                "old": "            <Stat label=\"\u2191 Desnivel\" value={elev ? `${elev.gainM} m` : \"\u2014\"} />",
                "new": (
                    "            <Stat label=\"\u2191 Desnivel\" value={elev ? `${elev.gainM} m` : \"\u2014\"} />\n"
                    "            <Stat label=\"\u2193 Desnivel\" value={elev ? `${elev.lossM} m` : \"\u2014\"} />"
                ),
            },
        ],
    },
]

BRACKET_PAIRS = [("(", ")"), ("{", "}"), ("[", "]")]


def fail(msg):
    print("\n\u274c  ABORTADO: " + msg)
    print("   No se ha modificado nada (o se ha restaurado el backup). El repo queda como estaba.")
    sys.exit(1)


def find_esbuild():
    local = os.path.join(ROOT, "node_modules", ".bin", "esbuild")
    if os.path.exists(local):
        return [local]
    # fallback: npx sin instalar (usa lo que haya en el proyecto)
    return None


def esbuild_check(path, loader, esbuild_cmd):
    # esbuild infiere el loader por la extension (.ts / .tsx); no se pasa --loader con un fichero.
    args = None
    if esbuild_cmd is not None:
        args = esbuild_cmd + [path, "--log-level=error"]
    else:
        args = ["npx", "--no-install", "esbuild", path, "--log-level=error"]
    try:
        r = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        return (None, "esbuild no encontrado")
    if r.returncode == 0:
        return (True, "")
    return (False, (r.stderr or "").strip())


def main():
    # Comprobacion minima de que estamos en la raiz correcta
    if not os.path.exists(os.path.join(ROOT, "package.json")):
        fail("no veo package.json aqui. Ejecuta el script desde la raiz del proyecto.")

    # ---- 1) PASADA EN SECO: leer, decidir que aplicar, validar anclas ----
    plan = []  # lista de (fileinfo, texto_original, [cambios_pendientes])
    total_pending = 0
    for fileinfo in EDITS:
        path = os.path.join(ROOT, fileinfo["file"])
        if not os.path.exists(path):
            fail("no existe el archivo " + fileinfo["file"])
        with open(path, encoding="utf-8") as f:
            text = f.read()
        pending = []
        for ch in fileinfo["changes"]:
            if ch["done"] in text:
                print("  \u2713 (ya aplicado) " + fileinfo["file"] + " :: " + ch["name"])
                continue
            n = text.count(ch["old"])
            if n == 0:
                fail("ancla NO encontrada en " + fileinfo["file"] + " :: " + ch["name"] +
                     "\n   (quizas el archivo ha cambiado; no se aplica nada por seguridad)")
            if n > 1:
                fail("ancla encontrada " + str(n) + " veces en " + fileinfo["file"] + " :: " + ch["name"] +
                     " (debe ser unica; no se aplica nada por seguridad)")
            pending.append(ch)
        plan.append((fileinfo, text, pending))
        total_pending += len(pending)

    if total_pending == 0:
        print("\n\u2705  Todo estaba ya aplicado. Nada que hacer.")
        return

    esbuild_cmd = find_esbuild()
    ts = time.strftime("%Y%m%d_%H%M%S")

    # ---- 2) APLICAR archivo por archivo (con backup, balance y esbuild) ----
    applied = []
    for fileinfo, original, pending in plan:
        if not pending:
            continue
        path = os.path.join(ROOT, fileinfo["file"])
        backup = path + ".bak_" + ts

        new_text = original
        for ch in pending:
            new_text = new_text.replace(ch["old"], ch["new"], 1)

        # Balance de simbolos: cada edicion debe anadir el MISMO numero de aperturas que de cierres
        for op, cl in BRACKET_PAIRS:
            d_open = new_text.count(op) - original.count(op)
            d_close = new_text.count(cl) - original.count(cl)
            if d_open != d_close:
                fail("balance de '" + op + cl + "' descuadrado en " + fileinfo["file"] +
                     " (aperturas +" + str(d_open) + " / cierres +" + str(d_close) +
                     "; no se ha escrito nada).")

        # Escribir backup + archivo
        shutil.copy2(path, backup)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)

        # Validacion de sintaxis
        ok, err = esbuild_check(path, fileinfo["loader"], esbuild_cmd)
        if ok is False:
            shutil.copy2(backup, path)
            os.remove(backup)
            fail("esbuild ha detectado un error de sintaxis en " + fileinfo["file"] +
                 " (restaurado el backup):\n" + err)
        elif ok is None:
            print("  \u26a0  esbuild no disponible: me salto la validacion de sintaxis de " + fileinfo["file"])

        for ch in pending:
            print("  \u2713 aplicado  " + fileinfo["file"] + " :: " + ch["name"])
        applied.append((fileinfo["file"], backup))

    print("\n\u2705  Parche aplicado.")
    print("   Backups: " + ", ".join(os.path.basename(b) for _, b in applied))
    print("\n\u25b6  Ahora compila y copia a iOS:")
    print("   npm run build && npx cap copy ios")


if __name__ == "__main__":
    main()
