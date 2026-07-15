#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/inventario.py — Pronostico de reabastecimiento (restock) FBA.

Imita la funcion estrella de Sellerboard: con la VELOCIDAD DE VENTA REAL de cada
producto (de la tabla `orders`) y el stock que carga el usuario, calcula:
  - cuantos dias de cobertura te queda el stock actual,
  - cuando se te va a agotar (fecha de quiebre),
  - hasta cuando podes esperar para pedir sin quedarte sin stock (fecha de
    pedido, contando el lead time del proveedor),
  - cuanto reponer para cubrir un horizonte objetivo, y el capital que ata.

Regla del proyecto: nada se inventa. Si un producto no tuvo ventas en la ventana
o no tiene stock cargado, se dice honestamente y NO se estima nada. Nunca lanza.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from core import db                    # noqa: E402
from agents import productos           # noqa: E402

# Defaults del pronostico (se pueden pisar por parametro desde el panel).
VENTANA_DIAS = 30            # ventana para medir la velocidad (run-rate)
COBERTURA_OBJETIVO_DIAS = 90  # cuanto stock querer tener por delante al reponer
SAFETY_DIAS = 7             # colchon de seguridad sobre el lead time
LEAD_TIME_DEFAULT = 60      # lead time por defecto si el producto no tiene uno


def _velocidades(ventana_dias=VENTANA_DIAS):
    """{asin: unidades/dia} sobre la ventana, desde ventas reales (orders)."""
    ventana_dias = max(1, int(ventana_dias))
    filas = db.rows(
        "SELECT asin, SUM(unidades) AS u FROM orders "
        "WHERE asin IS NOT NULL AND asin != '' "
        "AND fecha >= datetime('now', ?) GROUP BY asin",
        (f"-{ventana_dias} days",))
    return {r["asin"]: (r["u"] or 0) / ventana_dias for r in filas}


def _pronostico_producto(p, vel, hoy, cobertura_objetivo_dias, safety_dias):
    """Pronostico de UN producto. `vel` = unidades/dia (ya calculada)."""
    stock = p.get("stock")
    lead = int(p.get("lead_time_dias") or LEAD_TIME_DEFAULT)
    landed = p.get("landed") or 0.0
    base = {
        "id": p.get("id"), "nombre": p.get("nombre"), "asin": p.get("asin") or "",
        "stock": stock, "lead_time_dias": lead,
        "velocidad_diaria": round(vel, 2),
    }
    if vel <= 0:
        return {**base, "estado": "sin_ventas", "prioridad": 4,
                "mensaje": f"Sin ventas en los ultimos {VENTANA_DIAS} dias: no "
                           "puedo estimar reposicion todavia."}
    if stock is None:
        return {**base, "estado": "sin_stock", "prioridad": 3,
                "mensaje": "Carga tu stock actual para calcular el reabastecimiento."}

    stock = int(stock)
    dias_cobertura = stock / vel
    # Hasta cuando podes esperar para PEDIR sin quebrar: cobertura menos lo que
    # tarda en llegar (lead time) menos el colchon.
    dias_hasta_pedir = dias_cobertura - lead - safety_dias
    # Cuanto reponer: cubrir lead time + horizonte objetivo, menos lo que ya tenes.
    cantidad_sugerida = max(0, round(vel * (lead + cobertura_objetivo_dias) - stock))
    capital = round(cantidad_sugerida * landed, 2)

    if dias_hasta_pedir <= 0:
        estado, prioridad = "rojo", 0
    elif dias_hasta_pedir <= 14:
        estado, prioridad = "amarillo", 1
    else:
        estado, prioridad = "verde", 2

    return {
        **base,
        "dias_cobertura": round(dias_cobertura, 1),
        "fecha_quiebre": (hoy + timedelta(days=dias_cobertura)).strftime("%Y-%m-%d"),
        "dias_hasta_pedir": round(max(0.0, dias_hasta_pedir), 1),
        "fecha_pedir": (hoy + timedelta(days=max(0.0, dias_hasta_pedir))).strftime("%Y-%m-%d"),
        "cantidad_sugerida": int(cantidad_sugerida),
        "capital_reposicion": capital,
        "estado": estado, "prioridad": prioridad,
    }


def panel(ventana_dias=VENTANA_DIAS, cobertura_objetivo_dias=COBERTURA_OBJETIVO_DIAS,
          safety_dias=SAFETY_DIAS, hoy=None):
    """Pronostico de reabastecimiento de todo el portafolio activo, ordenado por
    urgencia. `hoy` es inyectable para tests deterministicos."""
    hoy = hoy or datetime.now()
    prods = productos.listar(solo_activos=True)
    vels = _velocidades(ventana_dias)
    items = [_pronostico_producto(p, vels.get(p.get("asin") or "", 0.0), hoy,
                                  int(cobertura_objetivo_dias), int(safety_dias))
             for p in prods]
    # rojo -> amarillo -> verde -> sin_stock -> sin_ventas; dentro, mas urgente antes.
    items.sort(key=lambda i: (i["prioridad"], i.get("dias_hasta_pedir", 1e9)))

    accionables = [i for i in items if i["estado"] in ("rojo", "amarillo")]
    return {
        "ok": True,
        "ventana_dias": int(ventana_dias),
        "cobertura_objetivo_dias": int(cobertura_objetivo_dias),
        "safety_dias": int(safety_dias),
        "resumen": {
            "n_productos": len(items),
            "n_reponer": len(accionables),
            "n_sin_stock": sum(1 for i in items if i["estado"] == "sin_stock"),
            "n_sin_ventas": sum(1 for i in items if i["estado"] == "sin_ventas"),
            "capital_reposicion_total": round(
                sum(i.get("capital_reposicion", 0) for i in accionables), 2),
        },
        "items": items,
    }


def set_stock(pid, stock, lead_time_dias=None):
    """Carga/actualiza el stock actual (unidades) y el lead time (dias) de un
    producto. No recalcula unit economics (stock/lead no los afectan)."""
    try:
        pid = int(pid)
        stock = max(0, int(stock))
    except (TypeError, ValueError):
        return {"ok": False, "mensaje": "Stock y producto deben ser numeros validos."}
    filas = db.rows("SELECT id FROM products WHERE id=?", (pid,))
    if not filas:
        return {"ok": False, "mensaje": f"No existe el producto id={pid}."}
    if lead_time_dias is None:
        db.execute("UPDATE products SET stock=?, stock_fecha=datetime('now') WHERE id=?",
                   (stock, pid))
    else:
        try:
            lead = max(1, int(lead_time_dias))
        except (TypeError, ValueError):
            return {"ok": False, "mensaje": "El lead time debe ser un numero de dias."}
        db.execute("UPDATE products SET stock=?, lead_time_dias=?, "
                   "stock_fecha=datetime('now') WHERE id=?", (stock, lead, pid))
    return {"ok": True, "id": pid, "stock": stock,
            "mensaje": "Stock actualizado."}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Pronostico de reabastecimiento FBA (restock) — CLI.")
    ap.add_argument("--panel", action="store_true", help="pronostico del portafolio")
    ap.add_argument("--set-stock", nargs=2, metavar=("ID", "UNIDADES"),
                    help="carga el stock actual de un producto")
    ap.add_argument("--lead", type=int, default=None, help="lead time en dias (con --set-stock)")
    args = ap.parse_args(argv)
    db.init()
    if args.set_stock:
        out = set_stock(args.set_stock[0], args.set_stock[1], lead_time_dias=args.lead)
    else:
        out = panel()
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
