#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
demo_pipeline.py — Corre el slice completo de research del sistema FBA:
    Cerebro (keywords)  ->  market_intel (score de nicho)  ->  listing (copy).

Uso:
    python demo_pipeline.py --demo
    python demo_pipeline.py --csv "Cerebro_B0XXXX.csv" --keyword "bamboo kitchen utensils"
"""

import argparse
import os
import sys

_RAIZ = os.path.dirname(os.path.abspath(__file__))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from agents.market_intel import market_intel, _texto as mi_texto   # noqa: E402
from agents.listing import generar, _texto as li_texto             # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pipeline FBA: Cerebro -> market_intel -> listing.")
    ap.add_argument("--keyword", default="bamboo kitchen utensils")
    ap.add_argument("--marketplace", default="US")
    ap.add_argument("--csv", help="Export CSV de Cerebro.")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args(argv)

    mi = market_intel(args.keyword, args.marketplace, csv_path=args.csv, demo=args.demo)
    print(mi_texto(mi))
    print()
    if not mi["ok"]:
        print("Pipeline detenido: sin datos de Cerebro. Conecta un CSV o usa --demo.")
        return 1
    if mi["veredicto"] in ("ROJO", "AMARILLO"):
        print(f"[AVISO] Veredicto {mi['veredicto']}: el nicho no es claramente ganable. "
              "Se genera el listing igual, pero conviene validar/diferenciar antes de invertir.")
        print()
    d = generar(args.keyword, args.marketplace, csv_path=args.csv, demo=args.demo)
    print(li_texto(args.keyword, d))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
