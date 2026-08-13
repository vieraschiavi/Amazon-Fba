#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/market_intel.py — Inteligencia de mercado + score de nicho (FBA).

Reconstruido desde DOCUMENTACION.md (firma y formula oficiales) y cableado a
data/cerebro.py como fuente real de demanda/competencia/oportunidad.

Formula documentada (no se toca):
    demanda          = min(demanda_mensual / 5000, 1)
    baja_competencia = max(0, 1 - competidores / 40)
    necesidad_valor  = oportunidad_valor / 100
    score_nicho      = round((0.35*demanda + 0.30*baja_competencia + 0.35*necesidad_valor) * 100)

PRODUCCION: sin export de Cerebro -> estado vacio explicado (NO inventa datos).

Standalone:
    python agents/market_intel.py --demo
    python agents/market_intel.py --csv export.csv --keyword "bamboo kitchen utensils"
Importable:
    from agents.market_intel import market_intel
"""

import argparse
import json
import os
import sys

# bootstrap para correr standalone desde agents/
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from data.cerebro import (cerebro_con_estado, enriquecer_market_intel,  # noqa: E402
                          veredicto_nicho)


def market_intel(keyword: str, marketplace: str = "US",
                 csv_path: str = None, demo: bool = False) -> dict:
    """
    Devuelve la inteligencia de nicho para `keyword` en `marketplace`.
    Fuente: export CSV de Helium 10 Cerebro (o demo). Sin dato -> estado vacio.
    """
    kws, estado = cerebro_con_estado(categoria=keyword, csv_path=csv_path, demo=demo)
    if not kws:
        return {
            "keyword": keyword, "marketplace": marketplace,
            "demanda_mensual": 0, "competidores": 0, "oportunidad_valor": 0,
            "score_nicho": 0, "veredicto": "SIN DATOS",
            "comentario": estado["mensaje"], "fuente": estado["fuente"],
            "n_keywords": 0, "n_oportunidad": 0, "ok": False,
        }
    enr = enriquecer_market_intel(kws, keyword)
    ver = veredicto_nicho(kws)
    return {
        "keyword": keyword, "marketplace": marketplace,
        "demanda_mensual": enr["demanda_mensual"],
        "competidores": enr["competidores"],
        "oportunidad_valor": enr["oportunidad_valor"],
        "score_nicho": enr["score_nicho"],
        "veredicto": ver["veredicto"], "comentario": ver["comentario"],
        "fuente": estado["fuente"], "archivo": estado.get("archivo"),
        "n_keywords": enr["n_keywords"], "n_oportunidad": enr["n_oportunidad"],
        "ok": True,
    }


def _texto(mi: dict) -> str:
    out = ["=" * 60, f"MARKET INTEL — '{mi['keyword']}'  (mkt={mi['marketplace']})", "=" * 60]
    if not mi["ok"]:
        out.append("Sin datos: " + mi["comentario"])
        out.append("=" * 60)
        return "\n".join(out)
    out += [
        f"Demanda mensual    : {mi['demanda_mensual']:,} busquedas/mes",
        f"Competidores (med.): {mi['competidores']}  (densidad de titulos pag.1)",
        f"Oportunidad valor  : {mi['oportunidad_valor']}/100",
        f"SCORE DE NICHO     : {mi['score_nicho']}/100",
        f"VEREDICTO          : {mi['veredicto']} — {mi['comentario']}",
        f"Keywords / opp     : {mi['n_keywords']} / {mi['n_oportunidad']}",
        f"Fuente             : {mi['fuente']}",
        "=" * 60,
    ]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Inteligencia de mercado + score de nicho (FBA).")
    ap.add_argument("--keyword", default="cocina eco", help="Nicho/keyword principal.")
    ap.add_argument("--marketplace", default="US")
    ap.add_argument("--csv", help="Export CSV de Cerebro.")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    mi = market_intel(args.keyword, args.marketplace, csv_path=args.csv, demo=args.demo)
    print(json.dumps(mi, ensure_ascii=False, indent=2) if args.json else _texto(mi))
    return 0 if mi["ok"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
