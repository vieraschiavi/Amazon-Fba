#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""generar_referencia.py — Regenera test/nucleo_referencia.json desde el motor
Python (agents/*). Corre estos casos y guarda su salida como "verdad" contra la
que se valida el port JavaScript (test/verificar_nucleo.js).

Uso:  python test/generar_referencia.py
Corre cuando cambian las formulas en agents/ para que la prueba de regresion
del motor JS siga comparando contra el original."""
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from agents.pricing import evaluar as ev_precio, landed_cost
from agents.ganancias import simular
from agents.exito import evaluar as ev_exito
from agents.dedicacion import estimar
from agents.capital_planner import proyeccion_realista
from data import bsr as bsr_mod
from data.mercado import potencial_producto, vendedores_principales
from data.motor_propio import analizar_hallazgos
from data.demanda_nativa import _score as _score_demanda, _nivel as _nivel_demanda

IN = {
    "pricing": {"prod": {"costo": 2.1, "flete": 0.8, "arancel_pct": 6, "prep": 0.5},
                "precio_competencia": 19.99},
    "ganancias": {"inversion": 3000, "costo": 2.1, "flete": 0.8, "arancel_pct": 6,
                  "prep": 0.5, "precio": 24, "techo_demanda": 290},
    "exito": {"keyword": "bamboo",
              "competencia": {"ventas_estim_total": 1890, "n_competidores": 8,
                              "resenas_mediana": 1200, "rating_promedio": 4.336,
                              "precio_mediana": 24.0},
              "interes_kw": 70, "precio_objetivo": 24.0, "margen_pct": 24.9},
    "dedicacion": {"n_op": 3, "lanzando": True},
    "caja": {"budget": 3000, "precio": 24, "techo_demanda": 290},
    # Estimacion por BSR: la app movil la hace OFFLINE, asi que su port JS tiene
    # que dar exactamente el mismo numero que la PC.
    "bsr_curva": [1, 100, 500, 999, 1000, 1234, 5000, 12486, 50000,
                  100000, 500000, 900000],
    "bsr_categorias": [[1000, None], [1000, "Home & Kitchen"],
                       [1000, "Clothing, Shoes & Jewelry"],
                       [1000, "Musical Instruments"], [1000, "Hogar y cocina"],
                       [1000, "Categoria Que No Existe"], [3200, "Toys & Games"]],
    "bsr_textos": [
        "Best Sellers Rank: #1,234 in Home & Kitchen (See Top 100 in Home & Kitchen)\n#5 in Cutting Boards",
        "#12,486 in Sports & Outdoors",
        "nº1.234 en Hogar y cocina",
        "#1,234 in Home & Kitchen   $24.99",
        "4500",
        "hola que tal",
        "",
    ],
    "potencial": [
        {"ventas": 500, "rating": 4.5, "resenas": 800, "precio": 25},
        {"ventas": 2500, "rating": 3.4, "resenas": 50, "precio": 45},
        {"ventas": 500, "precio": 25},
        {"ventas": 500},
        {},
        # 0 real (no ausente): lanzamiento nuevo, 0 ventas y 0 resenas, precio
        # gratis. El puerto JS tiene que tratar estos 0 igual que Python.
        {"ventas": 0, "rating": 4.0, "resenas": 500, "precio": 25},
        {"ventas": 500, "rating": 4.0, "resenas": 0, "precio": 25},
        {"ventas": 500, "rating": 4.0, "resenas": 500, "precio": 0},
        # rating=0 SI sigue siendo "sin dato" (no existe 0 estrellas en Amazon).
        {"ventas": 500, "rating": 0, "resenas": 500, "precio": 25},
    ],
    "vendedores": ("B08XYZ1234  Bamboo board  #1,234 in Home & Kitchen   $24.99\n"
                   "B07ABC5678  Board pro     #5,600 in Home & Kitchen   $19.99\n"
                   "B09QWE1111  Eco bundle    #18,900 in Home & Kitchen  $31.50\n"
                   "B01NOBSR99  Sin rank                                 $22.00"),
    # Demanda/nichos sin API: la app movil trae las sugerencias de Amazon con
    # SU internet, pero la PUNTUACION (score por keyword, agrupacion en nichos,
    # score de demanda relativa) tiene que dar identico a la PC. `hallazgos` es
    # lo que motor_propio.expandir() acumula (keyword -> mejor_rank+apariciones);
    # aca se fija a mano un caso realista para que la prueba sea deterministica
    # (sin pegarle a la red).
    "demanda": {
        "seed": "dog leash",
        "hallazgos": {
            "dog leash": {"mejor_rank": 1, "apariciones": 3},
            "dog leash for large dogs": {"mejor_rank": 1, "apariciones": 2},
            "dog leash retractable": {"mejor_rank": 2, "apariciones": 2},
            "dog leash for small dogs": {"mejor_rank": 3, "apariciones": 1},
            "dog leash hook": {"mejor_rank": 2, "apariciones": 1},
            "dog leash and collar set": {"mejor_rank": 4, "apariciones": 1},
            "dog leash holder for wall": {"mejor_rank": 5, "apariciones": 1},
            "dog harness": {"mejor_rank": 7, "apariciones": 1},
        },
    },
}

esperado = {}
esperado["pricing"] = ev_precio(IN["pricing"]["prod"],
                                precio_competencia=IN["pricing"]["precio_competencia"])
esperado["ganancias"] = simular(inversion=IN["ganancias"]["inversion"],
                                costo=IN["ganancias"]["costo"], flete=IN["ganancias"]["flete"],
                                arancel_pct=IN["ganancias"]["arancel_pct"],
                                prep=IN["ganancias"]["prep"], precio=IN["ganancias"]["precio"],
                                techo_demanda=IN["ganancias"]["techo_demanda"])
esperado["exito"] = ev_exito(IN["exito"]["keyword"], competencia=IN["exito"]["competencia"],
                             interes_kw=IN["exito"]["interes_kw"],
                             precio_objetivo=IN["exito"]["precio_objetivo"],
                             margen_pct=IN["exito"]["margen_pct"])
esperado["dedicacion"] = estimar(n_productos_operacion=IN["dedicacion"]["n_op"],
                                 lanzando_producto=IN["dedicacion"]["lanzando"])
_landed = landed_cost(2.1, 0.8, 6, 0.5)
_net = 24 - 24 * 0.15 - 3.65 - 24 * 0.10 - _landed
esperado["caja"] = proyeccion_realista(3000, _landed, 24, _net,
                                       techo_demanda=IN["caja"]["techo_demanda"])

# --- estimacion por BSR (la app movil replica esto offline) ---
esperado["bsr_curva"] = [bsr_mod.ventas_desde_bsr(b) for b in IN["bsr_curva"]]
esperado["bsr_categorias"] = [bsr_mod.ventas_desde_bsr(b, c)
                              for b, c in IN["bsr_categorias"]]
esperado["bsr_confianza"] = [bsr_mod.confianza_de(b, c)
                             for b, c in IN["bsr_categorias"]]
# Del parseo se comparan los CAMPOS (bsr/categoria/ventas/confianza), no la
# redaccion del mensaje: el movil tiene su propio texto mas corto de pantalla.
esperado["bsr_textos"] = []
for t in IN["bsr_textos"]:
    r = bsr_mod.estimar(t)
    esperado["bsr_textos"].append({
        "ok": r["ok"], "bsr": r["bsr"], "categoria": r["categoria"],
        "ventas_estim": r["ventas_estim"], "confianza": r["confianza"]})
esperado["potencial"] = [potencial_producto(detalle=True, **caso)
                         for caso in IN["potencial"]]
_vend = vendedores_principales(IN["vendedores"])
esperado["vendedores"] = {
    "ok": _vend["ok"], "ventas_estim_total": _vend["ventas_estim_total"],
    "ventas_estim_lider": _vend["ventas_estim_lider"],
    "productos": [{k: p[k] for k in ("asin", "bsr", "categoria", "precio",
                                     "ventas_estim", "confianza", "cuota_pct",
                                     "ingreso_estim_mes", "potencial",
                                     "potencial_parcial")}
                  for p in _vend["productos"]],
}

# --- demanda / nichos sin API (la app movil replica la PUNTUACION offline) ---
_seed = IN["demanda"]["seed"]
_kws, _nichos = analizar_hallazgos(_seed, IN["demanda"]["hallazgos"])
_amplitud = len(_kws)
_top_interes = _kws[0]["interes"] if _kws else 0
_seed_l = _seed.lower()
_seed_directo = any(k["keyword"].lower() == _seed_l or k["keyword"].lower().startswith(_seed_l)
                    for k in _kws[:15])
esperado["demanda"] = {
    "keywords": _kws,
    "nichos": _nichos,
    "amplitud": _amplitud,
    "top_interes": _top_interes,
    "seed_directo": _seed_directo,
    "demanda_score": _score_demanda(_amplitud, _top_interes, _seed_directo),
    "nivel": _nivel_demanda(_amplitud),
}

destino = os.path.join(_RAIZ, "test", "nucleo_referencia.json")
with open(destino, "w", encoding="utf-8") as fh:
    json.dump({"inputs": IN, "esperado": esperado}, fh, ensure_ascii=False, indent=2)
print("Referencia guardada en", destino)
