#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
core/demo_seed.py — Producto de ejemplo para la DEMO (full experience).

El cliente que prueba la demo puede cargar UN producto de ejemplo, ya con costo,
precio, margen, ROI y un par de ventas, para recorrer TODO el sistema (Pricing,
Portafolio, Caja, Ventas, Asistente) con numeros reales sin tener que cargar nada
a mano. Es idempotente (no duplica) y se marca con notas="[EJEMPLO]" para poder
quitarlo. La misma idea vive en mobile/js/app.js (boton "Ver con datos de ejemplo").
"""
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from core import db  # noqa: E402

MARCA = "[EJEMPLO]"
_ASIN_EJEMPLO = "B0DEMOMV01"


def hay_ejemplo():
    filas = db.rows("SELECT id FROM products WHERE asin=? LIMIT 1", (_ASIN_EJEMPLO,))
    return bool(filas)


def cargar_ejemplo():
    """Carga 1 producto de ejemplo + 2 ventas si no existe ya. Idempotente."""
    from agents import productos
    if hay_ejemplo():
        return {"ok": True, "ya": True,
                "mensaje": "El producto de ejemplo ya estaba cargado."}
    r = productos.guardar(
        nombre="Set utensilios de bambú (EJEMPLO)", asin=_ASIN_EJEMPLO,
        costo=2.10, flete=0.80, arancel_pct=6.0, prep=0.50, fba_fee=3.65,
        precio_competencia=18.99, techo_demanda=290, marketplace="US",
        notas=MARCA + " Producto de muestra para probar el sistema completo.")
    if not r.get("ok"):
        return r
    try:
        from agents import analytics
        analytics.registrar_venta(_ASIN_EJEMPLO, 120, 18.99, r.get("neto", 7.10),
                                  pais="US", segmento="Hogar", alertar=False)
        analytics.registrar_venta(_ASIN_EJEMPLO, 95, 18.99, r.get("neto", 7.10),
                                  pais="US", segmento="Hogar", alertar=False)
    except Exception:
        pass  # las ventas son opcionales; el producto ya da la experiencia
    try:
        from agents import inventario
        # stock + lead time de muestra para que el pronostico de reabastecimiento
        # tenga algo que mostrar en la demo
        inventario.set_stock(r["id"], 140, lead_time_dias=60)
    except Exception:
        pass
    return {"ok": True, "ya": False, "id": r["id"],
            "mensaje": "Producto de ejemplo cargado. Recorré Pricing, Caja, "
                       "Ventas y el Asistente para ver todo funcionando."}


def quitar_ejemplo():
    """Borra el producto de ejemplo y sus ventas."""
    db.execute("DELETE FROM orders WHERE asin=?", (_ASIN_EJEMPLO,))
    db.execute("DELETE FROM products WHERE asin=?", (_ASIN_EJEMPLO,))
    return {"ok": True, "mensaje": "Producto de ejemplo quitado."}
