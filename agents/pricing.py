#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/pricing.py — Costo desembarcado, precio, margen, ROI y semaforo (FBA).
Reconstruido desde DOCUMENTACION.md (formulas oficiales, no se tocan):

    landed_cost     = costo + flete + (costo+flete)*arancel_pct/100 + prep
    neto            = precio - referral - fba_fee - ads - landed
    margen %        = neto / precio * 100
    ROI %           = neto / landed * 100
    precio_objetivo = (fba_fee + landed) / (1 - referral/100 - acos/100 - margen_obj/100)
    break_even      = (fba_fee + landed) / (1 - referral/100 - acos/100)

evaluar(prod, fba_fee, precio_competencia, margen_obj):
  - calcula el precio para el margen objetivo;
  - si hay competencia, prueba ENTRAR 5% por debajo del lider, pero solo si el margen
    sigue por encima del amarillo (12%); si no, usa el precio objetivo.
Semaforo: verde >= 25%, amarillo >= 12%, rojo por debajo.

Standalone:
    python agents/pricing.py --costo 2.1 --flete 0.8 --arancel 6 --prep 0.5 --competencia 19.99
Importable:
    from agents.pricing import evaluar, landed_cost
"""
import argparse
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import config  # noqa: E402


def landed_cost(costo, flete, arancel_pct, prep):
    return costo + flete + (costo + flete) * arancel_pct / 100.0 + prep


def _semaforo(margen_pct):
    if margen_pct >= config.UMBRAL_VERDE:
        return "verde"
    if margen_pct >= config.UMBRAL_AMARILLO:
        return "amarillo"
    return "rojo"


def _metricas(precio, landed, fba_fee, referral_pct, acos_pct):
    referral = precio * referral_pct / 100.0
    ads = precio * acos_pct / 100.0
    neto = precio - referral - fba_fee - ads - landed
    margen = (neto / precio * 100.0) if precio > 0 else 0.0
    roi = (neto / landed * 100.0) if landed > 0 else 0.0
    return {"precio": round(precio, 2), "referral": round(referral, 2),
            "fba_fee": round(fba_fee, 2), "ads": round(ads, 2),
            "landed": round(landed, 2), "neto": round(neto, 2),
            "margen_pct": round(margen, 1), "roi_pct": round(roi, 1)}


def precio_objetivo(landed, fba_fee, margen_obj, referral_pct, acos_pct):
    denom = 1 - referral_pct / 100.0 - acos_pct / 100.0 - margen_obj / 100.0
    if denom <= 0:
        return None
    return (fba_fee + landed) / denom


def break_even(landed, fba_fee, referral_pct, acos_pct):
    denom = 1 - referral_pct / 100.0 - acos_pct / 100.0
    if denom <= 0:
        return None
    return (fba_fee + landed) / denom


def acos_bancable(margen_actual_pct, margen_minimo_pct, acos_supuesto_pct=None):
    """
    Cuanto ACoS (gasto en Amazon Advertising / facturacion, en %) podes bancar
    sin que el margen caiga por debajo de `margen_minimo_pct`.

    `margen_actual_pct` ya asume el ACoS que el pricing tiene cargado
    (config.ACOS_PCT por defecto): cada punto extra de ACoS le resta
    exactamente un punto al margen (ambos son % del precio de venta), asi
    que el maximo bancable es simplemente ese ACoS de base mas el colchon
    entre el margen actual y el minimo aceptable. Nunca negativo.
    """
    acos_supuesto_pct = config.ACOS_PCT if acos_supuesto_pct is None else acos_supuesto_pct
    return max(0.0, round(acos_supuesto_pct + (margen_actual_pct - margen_minimo_pct), 1))


def evaluar(prod: dict, fba_fee: float = None, precio_competencia: float = None,
            margen_obj: float = None) -> dict:
    fba_fee = config.FBA_FEE_DEFAULT if fba_fee is None else fba_fee
    margen_obj = config.TARGET_MARGIN if margen_obj is None else margen_obj
    referral_pct = config.REFERRAL_PCT
    acos_pct = config.ACOS_PCT

    landed = landed_cost(prod.get("costo", 0), prod.get("flete", 0),
                         prod.get("arancel_pct", 0), prod.get("prep", 0))

    p_obj = precio_objetivo(landed, fba_fee, margen_obj, referral_pct, acos_pct)
    be = break_even(landed, fba_fee, referral_pct, acos_pct)

    estrategia = "objetivo"
    precio = p_obj if p_obj else (be or landed * 2)

    # intentar entrar 5% por debajo del lider si el margen aguanta el amarillo
    if precio_competencia and precio_competencia > 0:
        p_comp = precio_competencia * 0.95
        m_comp = _metricas(p_comp, landed, fba_fee, referral_pct, acos_pct)
        if m_comp["margen_pct"] >= config.UMBRAL_AMARILLO:
            precio = p_comp
            estrategia = "competitivo (-5% vs lider)"

    m = _metricas(precio, landed, fba_fee, referral_pct, acos_pct)
    m.update({
        "semaforo": _semaforo(m["margen_pct"]),
        "estrategia": estrategia,
        "precio_objetivo": round(p_obj, 2) if p_obj else None,
        "break_even": round(be, 2) if be else None,
        "precio_competencia": precio_competencia,
        "margen_objetivo": margen_obj,
    })
    return m


def _texto(prod, m):
    out = ["=" * 56, "PRICING", "=" * 56,
           f"Landed cost      : USD {m['landed']}",
           f"Break-even       : USD {m['break_even']}",
           f"Precio objetivo  : USD {m['precio_objetivo']}  (margen obj {m['margen_objetivo']}%)",
           f"Estrategia       : {m['estrategia']}",
           f"PRECIO SUGERIDO  : USD {m['precio']}",
           f"  - referral     : USD {m['referral']}",
           f"  - FBA fee      : USD {m['fba_fee']}",
           f"  - ads (ACoS)   : USD {m['ads']}",
           f"  - neto/unidad  : USD {m['neto']}",
           f"MARGEN           : {m['margen_pct']}%   ROI: {m['roi_pct']}%   [{m['semaforo'].upper()}]",
           "=" * 56]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pricing FBA (landed, precio, margen, ROI).")
    ap.add_argument("--costo", type=float, default=2.1)
    ap.add_argument("--flete", type=float, default=0.8)
    ap.add_argument("--arancel", type=float, default=6.0)
    ap.add_argument("--prep", type=float, default=0.5)
    ap.add_argument("--fba", type=float, default=None)
    ap.add_argument("--competencia", type=float, default=None)
    ap.add_argument("--margen", type=float, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    prod = {"costo": args.costo, "flete": args.flete, "arancel_pct": args.arancel,
            "prep": args.prep}
    m = evaluar(prod, fba_fee=args.fba, precio_competencia=args.competencia,
                margen_obj=args.margen)
    print(json.dumps(m, ensure_ascii=False, indent=2) if args.json else _texto(prod, m))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
