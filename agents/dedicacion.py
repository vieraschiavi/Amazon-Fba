#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/dedicacion.py — Estimador de dedicacion horaria de MV FBA IA.

Responde "¿cuantas horas por semana necesito REALMENTE?" con un desglose por
tarea, distinguiendo lo que el sistema ya automatiza (bot de FAQ, alertas,
analytics) de lo que sigue siendo trabajo humano (sourcing, calidad, decisiones).

Dos fases:
  - LANZAMIENTO: mientras validas un producto nuevo (investigar, contactar
    proveedores, armar listing/fotos, configurar Seller Central). Es la carga
    mas alta y se repite cada vez que lanzas un producto.
  - OPERACION: producto ya en meseta, semana tipica con el bot y las alertas
    haciendo el trabajo repetitivo.

HONESTIDAD: son horas de REFERENCIA (rangos), no una promesa. Vender bien
requiere mas horas que las de aca si el producto tiene problemas de calidad,
reclamos o guerra de precios.
"""
import argparse
import json
import sys

TAREAS_LANZAMIENTO = [
    ("Investigar nicho y keywords (motor propio / Cerebro)", 3, 5, "una vez"),
    ("Evaluar y contactar proveedores + RFQ + negociar + pedir muestra", 4, 6, "una vez"),
    ("Armar listing + coordinar/organizar las 7 fotos", 3, 4, "una vez"),
    ("Configurar Seller Central + primer envio a Amazon (FBA)", 2, 3, "una vez"),
    ("Monitorear PPC y precio la primera semana tras lanzar", 2, 3, "por semana, primer mes"),
]

TAREAS_OPERACION_POR_PRODUCTO = [
    ("Revisar PPC, precio y stock", 0.5, 1.0),
    ("Atender casos que el bot deriva (no son FAQ)", 0.5, 1.0),
    ("Seguimiento de reposicion con el proveedor", 0.25, 0.5),
    ("Leer KPIs y alertas (ya automatizadas)", 0.25, 0.25),
]

AUTOMATIZADO = [
    "Clasificar y responder consultas FAQ (envio, garantia, estado de pedido...)",
    "Registrar ventas, calcular KPIs y margen global",
    "Enviar alertas por email de cada venta/consulta",
    "Calcular pricing, proyeccion de caja y semaforo de margen",
    "Investigar keywords con el motor propio (corre solo, vos revisas el resultado)",
]


def estimar(n_productos_operacion=1, lanzando_producto=False, semanas_desde_lanzamiento=0):
    """
    n_productos_operacion: productos ya en meseta (fuera del que estas lanzando).
    lanzando_producto: True si estas validando/lanzando un producto nuevo ahora.
    semanas_desde_lanzamiento: para diluir la carga de 'primera semana' del lanzamiento.
    Devuelve horas/semana min-max desglosadas por tarea + total.
    """
    filas, total_min, total_max = [], 0.0, 0.0

    if lanzando_producto:
        for tarea, mn, mx, cuando in TAREAS_LANZAMIENTO:
            if cuando == "una vez":
                # se prorratea en las primeras ~3 semanas del lanzamiento
                mn_s, mx_s = mn / 3.0, mx / 3.0
            elif semanas_desde_lanzamiento <= 4:
                mn_s, mx_s = mn, mx
            else:
                continue
            filas.append({"tarea": tarea, "horas_min": round(mn_s, 1),
                          "horas_max": round(mx_s, 1), "frecuencia": cuando,
                          "fase": "lanzamiento"})
            total_min += mn_s
            total_max += mx_s

    for tarea, mn, mx in TAREAS_OPERACION_POR_PRODUCTO:
        mn_t, mx_t = mn * n_productos_operacion, mx * n_productos_operacion
        if mn_t == 0 and mx_t == 0:
            continue
        filas.append({"tarea": f"{tarea} (x{n_productos_operacion} producto/s)",
                      "horas_min": round(mn_t, 1), "horas_max": round(mx_t, 1),
                      "frecuencia": "por semana", "fase": "operacion"})
        total_min += mn_t
        total_max += mx_t

    return {
        "n_productos_operacion": n_productos_operacion,
        "lanzando_producto": lanzando_producto,
        "horas_semana_min": round(total_min, 1),
        "horas_semana_max": round(total_max, 1),
        "desglose": filas,
        "automatizado_por_el_sistema": AUTOMATIZADO,
        "caveat": ("Rangos de referencia. Un producto con problemas de calidad, "
                   "reclamos o guerra de precios exige mas horas que estas; un "
                   "producto sano con proveedor solido puede exigir menos."),
    }


def linea_de_tiempo_dedicacion(n_lanzamientos=2, gap_semanas=20):
    """
    Vista rapida de como varia la dedicacion a lo largo del tiempo si lanzas
    `n_lanzamientos` productos espaciados `gap_semanas` entre si (por defecto
    ~5 meses, el mismo gap que usa agents/portafolio.recomendar_portafolio).
    """
    filas = []
    for i in range(n_lanzamientos):
        semana_inicio = i * gap_semanas
        est_lanz = estimar(n_productos_operacion=i, lanzando_producto=True,
                           semanas_desde_lanzamiento=0)
        est_op = estimar(n_productos_operacion=i + 1, lanzando_producto=False)
        filas.append({
            "producto": i + 1, "semana_lanzamiento": semana_inicio,
            "horas_semana_durante_lanzamiento": (est_lanz["horas_semana_min"],
                                                 est_lanz["horas_semana_max"]),
            "horas_semana_en_operacion_despues": (est_op["horas_semana_min"],
                                                  est_op["horas_semana_max"]),
        })
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser(description="Estimador de dedicacion horaria FBA.")
    ap.add_argument("--productos", type=int, default=1)
    ap.add_argument("--lanzando", action="store_true")
    args = ap.parse_args(argv)
    r = estimar(n_productos_operacion=args.productos, lanzando_producto=args.lanzando)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
