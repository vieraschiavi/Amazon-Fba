#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/ganancias.py — Simulador de ganancia potencial de MV FBA IA.

Responde la pregunta del dueno: "si invierto X plata (o compro X unidades) en
este producto, ¿cuanto gano?" — con DESGLOSE completo de costos y ganancia neta.

Usa los mismos motores validados del sistema (nada se calcula dos veces distinto):
  - agents/pricing: landed cost, referral, FBA fee, publicidad, neto/unidad.
  - agents/capital_planner: proyeccion 12 meses reciclando capital (con techo
    de demanda, lead time y DD+7) para el escenario sostenido.

Dos vistas:
  1) VENTA DEL LOTE: compras N unidades con tu inversion y las vendes todas al
     precio dado -> ingreso bruto, cada costo desglosado, ganancia neta, ROI y
     cuantos meses tardas en venderlo dado el techo de demanda.
  2) RECICLANDO CAPITAL 12 MESES: el landed repone stock y el neto se retira
     como sueldo -> sueldo en meseta y caja minima (proyeccion realista).

HONESTIDAD: asume que vendes al precio dado y al ritmo del techo; el resultado
real depende de ranking, PPC y producto. Es proyeccion, no promesa.
"""
import argparse
import json
import math
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import config                                            # noqa: E402
from agents.pricing import evaluar, landed_cost          # noqa: E402
from agents.capital_planner import proyeccion_realista   # noqa: E402


def simular(inversion=None, unidades=None, costo=2.10, flete=0.80, arancel_pct=6.0,
            prep=0.50, fba_fee=None, precio=None, precio_competencia=None,
            techo_demanda=290, devoluciones=0.05, meses=12):
    """
    Pasa `inversion` (USD) O `unidades` (la otra se deduce del landed cost).
    `precio`: tu precio de venta; si no lo pasas, usa el sugerido por el pricing.
    Devuelve {ok, entrada, unit_economics, lote{ingresos, costos{}, ganancia...},
    reciclado{...}, caveat}.
    """
    fba_fee = config.FBA_FEE_DEFAULT if fba_fee is None else fba_fee
    landed = landed_cost(costo, flete, arancel_pct, prep)
    if landed <= 0:
        return {"ok": False, "mensaje": "Cargar costos: el landed cost dio 0."}

    # precio: el que pasa el usuario, o el sugerido por el motor de pricing
    m = evaluar({"costo": costo, "flete": flete, "arancel_pct": arancel_pct,
                 "prep": prep}, fba_fee=fba_fee,
                precio_competencia=precio_competencia)
    precio_v = float(precio) if precio and precio > 0 else m["precio"]
    referral_u = precio_v * config.REFERRAL_PCT / 100.0
    ads_u = precio_v * config.ACOS_PCT / 100.0
    neto_u = precio_v - referral_u - fba_fee - ads_u - landed

    # inversion <-> unidades
    if unidades and unidades > 0:
        unidades = int(unidades)
        inversion_usada = round(unidades * landed, 2)
        entrada = f"{unidades} unidades"
    elif inversion and inversion > 0:
        unidades = int(inversion // landed)
        inversion_usada = round(unidades * landed, 2)
        entrada = f"USD {inversion:,.0f} de inversion"
    else:
        return {"ok": False,
                "mensaje": "Indica cuanta plata invertis (USD) o cuantas unidades."}
    if unidades <= 0:
        return {"ok": False,
                "mensaje": f"Con USD {inversion:,.0f} no llegas a 1 unidad "
                           f"(landed USD {landed:.2f})."}

    vendibles = unidades * (1 - devoluciones)      # 5% vuelve y se reembolsa
    ingreso_bruto = vendibles * precio_v
    costos = {
        "producto": round(unidades * costo, 2),
        "flete": round(unidades * flete, 2),
        "arancel": round(unidades * (costo + flete) * arancel_pct / 100.0, 2),
        "prep": round(unidades * prep, 2),
        "comision_amazon_referral": round(vendibles * referral_u, 2),
        "fba_fee": round(vendibles * fba_fee, 2),
        "publicidad_acos": round(vendibles * ads_u, 2),
    }
    total_costos = round(sum(costos.values()), 2)
    ganancia_neta = round(ingreso_bruto - total_costos, 2)
    meses_venta = math.ceil(unidades / techo_demanda) if techo_demanda else None

    lote = {
        "unidades_compradas": unidades,
        "inversion_usada": inversion_usada,
        "unidades_vendidas_netas": round(vendibles, 1),
        "devoluciones_pct": devoluciones * 100,
        "ingreso_bruto": round(ingreso_bruto, 2),
        "costos": costos,
        "total_costos": total_costos,
        "ganancia_neta": ganancia_neta,
        "ganancia_por_unidad": round(neto_u, 2),
        "margen_pct": round(ganancia_neta / ingreso_bruto * 100, 1) if ingreso_bruto else 0,
        "roi_inversion_pct": round(ganancia_neta / inversion_usada * 100, 1)
                             if inversion_usada else 0,
        "meses_para_venderlo": meses_venta,
        "ganancia_por_mes_promedio": round(ganancia_neta / meses_venta, 2)
                                     if meses_venta else None,
    }

    # escenario sostenido: reciclando capital 12 meses (motor de caja existente)
    proy = proyeccion_realista(inversion_usada, landed, precio_v, neto_u,
                               devoluciones=devoluciones,
                               techo_demanda=int(techo_demanda), meses=meses)
    rp = proy["resumen"]
    reciclado = {
        "sueldo_meseta_mensual": rp["sueldo_meseta"],
        "ganancia_12m_estimada": round(sum(f["sueldo"] for f in proy["filas"]), 2),
        "caja_minima": rp["caja_minima"],
        "mes_primer_cobro": rp["mes_primer_cobro"],
        "alerta": rp["alerta"],
        "filas": proy["filas"],
    }

    return {
        "ok": True,
        "entrada": entrada,
        "unit_economics": {
            "landed": round(landed, 2), "precio_venta": round(precio_v, 2),
            "precio_es_sugerido": not (precio and precio > 0),
            "referral_unidad": round(referral_u, 2), "fba_fee": round(fba_fee, 2),
            "publicidad_unidad": round(ads_u, 2), "neto_unidad": round(neto_u, 2),
            "semaforo": m["semaforo"] if not (precio and precio > 0) else
                        ("verde" if (neto_u / precio_v * 100) >= config.UMBRAL_VERDE else
                         "amarillo" if (neto_u / precio_v * 100) >= config.UMBRAL_AMARILLO
                         else "rojo"),
        },
        "lote": lote,
        "reciclado": reciclado,
        "caveat": ("Proyeccion, no promesa: asume que vendes al precio indicado y "
                   "al ritmo del techo de demanda; el resultado real depende del "
                   "ranking, el PPC y la calidad del producto. Si la ganancia por "
                   "unidad es negativa, NO compres: estarias pagando por vender."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cuanto podrias ganar con un producto.")
    ap.add_argument("--inversion", type=float, default=None, help="USD a invertir")
    ap.add_argument("--unidades", type=int, default=None, help="o cantidad a comprar")
    ap.add_argument("--costo", type=float, default=2.10)
    ap.add_argument("--flete", type=float, default=0.80)
    ap.add_argument("--arancel", type=float, default=6.0)
    ap.add_argument("--prep", type=float, default=0.50)
    ap.add_argument("--fba", type=float, default=None)
    ap.add_argument("--precio", type=float, default=None)
    ap.add_argument("--techo", type=int, default=290)
    args = ap.parse_args(argv)
    r = simular(inversion=args.inversion or (3000 if not args.unidades else None),
                unidades=args.unidades, costo=args.costo, flete=args.flete,
                arancel_pct=args.arancel, prep=args.prep, fba_fee=args.fba,
                precio=args.precio, techo_demanda=args.techo)
    if not r["ok"]:
        print(r["mensaje"])
        return 1
    ue, lo, re = r["unit_economics"], r["lote"], r["reciclado"]
    print("=" * 62)
    print(f"CUANTO PODRIAS GANAR — {r['entrada']}")
    print("=" * 62)
    print(f"Landed USD {ue['landed']}  ->  {lo['unidades_compradas']} unidades "
          f"(inversion USD {lo['inversion_usada']:,.0f})")
    print(f"Precio venta USD {ue['precio_venta']}"
          + ("  (sugerido por el pricing)" if ue["precio_es_sugerido"] else ""))
    print(f"\nVENTA DEL LOTE (con {lo['devoluciones_pct']:.0f}% devoluciones):")
    print(f"  Ingreso bruto            USD {lo['ingreso_bruto']:>10,.2f}")
    for k, v in lo["costos"].items():
        print(f"  - {k:<24} USD {v:>10,.2f}")
    print(f"  GANANCIA NETA            USD {lo['ganancia_neta']:>10,.2f}  "
          f"(neto/u USD {lo['ganancia_por_unidad']}, margen {lo['margen_pct']}%, "
          f"ROI {lo['roi_inversion_pct']}%)")
    if lo["meses_para_venderlo"]:
        print(f"  Tiempo de venta: ~{lo['meses_para_venderlo']} meses al techo "
              f"-> USD {lo['ganancia_por_mes_promedio']:,.2f}/mes")
    print(f"\nRECICLANDO CAPITAL 12 MESES (repones stock, retiras el neto):")
    print(f"  Sueldo en meseta USD {re['sueldo_meseta_mensual']:,.2f}/mes · "
          f"ganancia 12m ~USD {re['ganancia_12m_estimada']:,.2f} · "
          f"caja minima USD {re['caja_minima']:,.2f}")
    print("\n" + r["caveat"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
