#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

destino = os.path.join(_RAIZ, "test", "nucleo_referencia.json")
with open(destino, "w", encoding="utf-8") as fh:
    json.dump({"inputs": IN, "esperado": esperado}, fh, ensure_ascii=False, indent=2)
print("Referencia guardada en", destino)
