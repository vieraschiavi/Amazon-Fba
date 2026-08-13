#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/analytics.py — Registro de ventas, KPIs y mix (FBA).
registrar_venta(...) -> guarda en orders + dispara alerta por email.
kpis() -> facturacion, neto, margen global y mix por producto/pais/segmento.
"""
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
from core import db        # noqa: E402
from core import notify    # noqa: E402


def registrar_venta(asin, unidades, precio, neto_unitario, pais="US",
                    segmento="general", product_id=None, alertar=True):
    ingreso = unidades * precio
    neto = unidades * neto_unitario
    rid = db.insert("orders", asin=asin, unidades=unidades, precio=precio,
                    neto_unitario=neto_unitario, ingreso=ingreso, neto=neto,
                    pais=pais, segmento=segmento, product_id=product_id)
    if alertar:
        notify.alertar(
            f"[FBA] Venta: {unidades}x {asin}",
            f"Vendiste {unidades} unidades de {asin} a USD {precio:.2f}.\n"
            f"Facturacion: USD {ingreso:.2f} | Neto: USD {neto:.2f}\n"
            f"Pais: {pais} | Segmento: {segmento}")
    return {"id": rid, "ingreso": round(ingreso, 2), "neto": round(neto, 2)}


def _mix(campo):
    return db.rows(
        f"SELECT {campo} AS k, SUM(ingreso) AS ingreso, SUM(neto) AS neto, "
        f"SUM(unidades) AS unidades FROM orders GROUP BY {campo} ORDER BY ingreso DESC")


def kpis():
    tot = db.rows("SELECT COALESCE(SUM(ingreso),0) AS facturacion, "
                  "COALESCE(SUM(neto),0) AS neto, COALESCE(SUM(unidades),0) AS unidades, "
                  "COUNT(*) AS ordenes FROM orders")[0]
    fact = tot["facturacion"] or 0
    margen_global = (tot["neto"] / fact * 100.0) if fact else 0.0
    return {
        "facturacion": round(fact, 2), "neto": round(tot["neto"] or 0, 2),
        "unidades": tot["unidades"] or 0, "ordenes": tot["ordenes"] or 0,
        "margen_global_pct": round(margen_global, 1),
        "por_producto": _mix("asin"), "por_pais": _mix("pais"),
        "por_segmento": _mix("segmento"),
    }


if __name__ == "__main__":
    db.init()
    print(registrar_venta("B0DEMO123", 10, 24.0, 6.9, pais="US", segmento="hogar", alertar=False))
    print("KPIs:", {k: v for k, v in kpis().items() if not isinstance(v, list)})
