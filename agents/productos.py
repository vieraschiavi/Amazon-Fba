#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/productos.py — Portafolio de productos persistente (FBA).

Gestion del negocio producto a producto, sobre la tabla `products` de SQLite:
  - guardar()            alta con metricas calculadas por agents/pricing (no a mano)
  - listar()             portafolio con metricas + ventas reales (join con orders)
  - actualizar()         edita insumos y RECALCULA landed/precio/margen/roi/semaforo
  - desactivar()         baja logica (activo=0); el historico de ventas queda
  - analisis()           analisis financiero completo de UN producto:
                         unit economics + proyeccion de caja 12m + ventas reales
  - resumen_portafolio() consolidado del negocio: capital, sueldo meseta proyectado,
                         facturacion/neto real y mix por producto

Regla del proyecto: nada se inventa. Lo proyectado sale de agents/pricing y
agents/capital_planner (mismas formulas que el panel); lo real sale de `orders`.
"""
import argparse
import json
import os
import sys
from datetime import datetime

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import config                                       # noqa: E402
from core import db                                 # noqa: E402
from agents.pricing import evaluar                  # noqa: E402
from agents.capital_planner import proyeccion_realista  # noqa: E402

PIPELINE_MESES = 4          # meses de stock que ata el capital de un producto


def _metricas(costo, flete, arancel_pct, prep, fba_fee, precio_competencia=None):
    """Unit economics via agents/pricing (fuente unica de formulas)."""
    return evaluar({"costo": costo, "flete": flete, "arancel_pct": arancel_pct,
                    "prep": prep}, fba_fee=fba_fee,
                   precio_competencia=precio_competencia)


def guardar(nombre, asin="", costo=0.0, flete=0.0, arancel_pct=0.0, prep=0.0,
            fba_fee=None, precio_competencia=None, techo_demanda=290,
            marketplace=None, notas=""):
    """Alta de producto: calcula las metricas y persiste. Devuelve la fila creada."""
    if not (nombre or "").strip():
        return {"ok": False, "mensaje": "El producto necesita un nombre."}
    fba_fee = config.FBA_FEE_DEFAULT if fba_fee is None else fba_fee
    m = _metricas(costo, flete, arancel_pct, prep, fba_fee, precio_competencia)
    pid = db.insert("products", nombre=nombre.strip(), asin=(asin or "").strip(),
                    costo=costo, flete=flete, arancel_pct=arancel_pct, prep=prep,
                    fba_fee=fba_fee, landed=m["landed"], precio=m["precio"],
                    neto=m["neto"], margen=m["margen_pct"], roi=m["roi_pct"],
                    semaforo=m["semaforo"], techo_demanda=int(techo_demanda),
                    marketplace=marketplace or config.MARKETPLACE,
                    notas=notas or "", activo=1)
    return {"ok": True, "id": pid, "mensaje": f"'{nombre}' guardado en el portafolio.",
            **m}


def actualizar(pid, **campos):
    """Edita insumos de un producto y recalcula todas las metricas derivadas."""
    filas = db.rows("SELECT * FROM products WHERE id=?", (pid,))
    if not filas:
        return {"ok": False, "mensaje": f"No existe el producto id={pid}."}
    p = filas[0]
    editables = ("nombre", "asin", "costo", "flete", "arancel_pct", "prep",
                 "fba_fee", "techo_demanda", "notas", "activo")
    for k in editables:
        if k in campos and campos[k] is not None:
            p[k] = campos[k]
    m = _metricas(p["costo"] or 0, p["flete"] or 0, p["arancel_pct"] or 0,
                  p["prep"] or 0, p["fba_fee"] or config.FBA_FEE_DEFAULT,
                  campos.get("precio_competencia"))
    db.execute("""UPDATE products SET nombre=?, asin=?, costo=?, flete=?,
                  arancel_pct=?, prep=?, fba_fee=?, landed=?, precio=?, neto=?,
                  margen=?, roi=?, semaforo=?, techo_demanda=?, notas=?, activo=?
                  WHERE id=?""",
               (p["nombre"], p["asin"], p["costo"], p["flete"], p["arancel_pct"],
                p["prep"], p["fba_fee"], m["landed"], m["precio"], m["neto"],
                m["margen_pct"], m["roi_pct"], m["semaforo"],
                int(p["techo_demanda"] or 0), p["notas"], int(p["activo"] or 0),
                pid))
    return {"ok": True, "id": pid, "mensaje": "Producto actualizado.", **m}


def desactivar(pid):
    """Baja logica: sale del portafolio activo, el historico de ventas queda."""
    n = db.execute("UPDATE products SET activo=0 WHERE id=?", (pid,))
    return {"ok": n > 0, "mensaje": "Producto desactivado." if n else "No existe."}


# Historial minimo para proyectar un run-rate desde ventas propias. Con menos
# dias, multiplicar por 30 amplifica ruido: 2 ventas en 2 dias NO son 30/mes.
MIN_DIAS_RUN_RATE = 7


def _run_rate_propio(asin, hoy=None):
    """Ventas/mes medidas de TUS PROPIAS ordenes registradas (tabla `orders`).

    No es una estimacion de mercado: es el run-rate REAL de lo que vendiste. Para
    un producto de marca propia (tu ASIN, tu listing) eso ES lo que vende ese
    ASIN. No cuesta nada y no depende de ninguna API.

    Devuelve {unidades_mes, dias, unidades_total} o None si no hay historial
    suficiente (ver MIN_DIAS_RUN_RATE) -- en ese caso NO se proyecta nada."""
    filas = db.rows(
        "SELECT SUM(unidades) AS u, MIN(fecha) AS desde, MAX(fecha) AS hasta, "
        "COUNT(*) AS n FROM orders WHERE asin=?", (asin,))
    if not filas or not filas[0].get("u"):
        return None
    f = filas[0]
    total = int(f["u"] or 0)
    if total <= 0:
        return None
    # Ventana observada: de la PRIMERA venta hasta hoy (no hasta la ultima: los
    # dias sin vender tambien cuentan, si no se sobreestima el ritmo).
    ref = hoy or datetime.now()
    try:
        desde = datetime.fromisoformat(str(f["desde"]))
    except ValueError:
        return None
    dias = (ref - desde).total_seconds() / 86400.0
    if dias < MIN_DIAS_RUN_RATE:
        return None
    return {"unidades_mes": int(round(total / dias * 30.0)),
            "dias": int(round(dias)), "unidades_total": total}


def estimar_ventas(pid, bsr=None, categoria=None):
    """Estima cuantas unidades/mes vende ESE producto en Amazon y guarda el
    resultado dentro de la ficha (ventas_estim_mes/_fuente/_fecha/_confianza).

    SIN DATOS INVENTADOS (regla del proyecto): el numero sale SOLO de una fuente
    real, en este orden de preferencia:
      1) Jungle Scout (ventas reales por ASIN, sales_estimates) — es lo mejor;
      2) Keepa (BSR real -> curva BSR/ventas, estimacion gruesa documentada);
      3) BSR PUBLICO DE AMAZON -> curva. GRATIS, sin ninguna API. El BSR figura
         en la pagina de cualquier producto ("Best Sellers Rank"): lo pegas o lo
         escribis y la misma curva de (2) lo convierte a u/mes. Sirve para
         CUALQUIER ASIN, incluido uno que todavia no vendes -- que es el caso de
         uso real cuando estas investigando si entrar a un producto;
      4) TUS PROPIAS VENTAS registradas (run-rate de `orders`). Ojo: esto NO es
         una estimacion de mercado, es MEDICION de lo que vendiste vos. Va
         ultimo justamente por eso: solo dice algo de un ASIN que ya vendes.

    `bsr` puede ser el numero o el bloque pegado de Amazon; si no se pasa, se usa
    el que ya este guardado en la ficha. Se guarda para poder re-estimar."""
    from data import jungle_scout, keepa, bsr as bsr_mod   # import diferido

    filas = db.rows("SELECT * FROM products WHERE id=?", (pid,))
    if not filas:
        return {"ok": False, "mensaje": f"No existe el producto id={pid}."}
    prod = filas[0]
    asin = (prod.get("asin") or "").strip()
    if not asin:
        return {"ok": False, "mensaje": "Cargá el ASIN del producto para estimar sus "
                "ventas: sin ASIN no hay forma real de saber cuánto vende en Amazon."}

    # BSR: el que llega por parametro pisa al guardado; si no llega ninguno, se
    # reusa el de la ficha para que re-estimar no obligue a pegarlo de nuevo.
    lectura = None
    if bsr is not None and str(bsr).strip() != "":
        lectura = bsr_mod.estimar(bsr, categoria)
        if not lectura.get("ok"):
            return {"ok": False, "asin": asin, "mensaje": lectura["mensaje"]}
    elif prod.get("bsr"):
        lectura = bsr_mod.estimar(int(prod["bsr"]),
                                  categoria or prod.get("bsr_categoria"))

    confianza = None
    # 1) Jungle Scout: ventas reales por ASIN (lo preferido).
    js = jungle_scout.ventas_asin(asin)
    kp = {}
    propio = None
    if js.get("ok") and js.get("ventas_estim"):
        est, fuente, confianza = int(js["ventas_estim"]), "Jungle Scout", "alta"
    else:
        # 2) Keepa: BSR real convertido a ventas por la curva (mas grueso).
        kp = keepa.producto(asin)
        if kp.get("ok") and kp.get("ventas_estim"):
            est, fuente, confianza = int(kp["ventas_estim"]), "Keepa (BSR)", "media"
        elif lectura and lectura.get("ok"):
            # 3) GRATIS: BSR publico que cargo el usuario -> misma curva.
            est = int(lectura["ventas_estim"])
            cat = lectura.get("categoria")
            fuente = "BSR de Amazon" + (f" ({cat})" if cat else "")
            confianza = lectura.get("confianza")
        else:
            # 4) Ultimo recurso: medicion de tus propias ventas registradas.
            propio = _run_rate_propio(asin)
            if propio:
                est = propio["unidades_mes"]
                fuente = f"Tus ventas ({propio['dias']} días)"
                confianza = "alta"
            else:
                # Nada real disponible: se avisa que falta, no se inventa.
                motivo = js.get("mensaje") or kp.get("mensaje") or ""
                return {"ok": False, "asin": asin, "mensaje":
                        "Todavía no se puede estimar las ventas de este ASIN. El "
                        "camino GRATIS: abrí el producto en Amazon, copiá el bloque "
                        "\"Best Sellers Rank\" (o sólo el número) y pegalo acá — con "
                        "eso se estima sin pagar ninguna API. También sirve conectar "
                        "Jungle Scout o Keepa en Config. " + motivo}

    # Se guarda en la ficha con fuente, confianza y fecha, para que sea auditable.
    db.execute("UPDATE products SET ventas_estim_mes=?, ventas_estim_fuente=?, "
               "ventas_estim_confianza=?, ventas_estim_fecha=datetime('now') "
               "WHERE id=?", (est, fuente, confianza, pid))
    if lectura and lectura.get("ok"):
        db.execute("UPDATE products SET bsr=?, bsr_categoria=? WHERE id=?",
                   (lectura["bsr"], lectura.get("categoria"), pid))
    fila = db.rows("SELECT ventas_estim_fecha FROM products WHERE id=?", (pid,))
    fecha = fila[0]["ventas_estim_fecha"] if fila else None
    return {"ok": True, "id": pid, "asin": asin, "ventas_estim_mes": est,
            "ventas_estim_fuente": fuente, "ventas_estim_fecha": fecha,
            "ventas_estim_confianza": confianza,
            "bsr": lectura["bsr"] if lectura and lectura.get("ok") else prod.get("bsr"),
            "mensaje": f"~{est} u/mes según {fuente} (confianza {confianza}) — "
                       "guardado en la ficha del producto."}


def _ventas_por_asin():
    return {r["asin"]: r for r in db.rows(
        "SELECT asin, SUM(ingreso) AS ingreso, SUM(neto) AS neto, "
        "SUM(unidades) AS unidades, COUNT(*) AS ordenes FROM orders GROUP BY asin")}


def listar(solo_activos=True):
    """Portafolio con metricas guardadas + ventas reales acumuladas (por ASIN)."""
    sql = "SELECT * FROM products" + (" WHERE activo=1" if solo_activos else "")
    productos = db.rows(sql + " ORDER BY id")
    ventas = _ventas_por_asin()
    for p in productos:
        v = ventas.get(p.get("asin") or "", {})
        p["ventas_ingreso"] = round(v.get("ingreso") or 0, 2)
        p["ventas_neto"] = round(v.get("neto") or 0, 2)
        p["ventas_unidades"] = v.get("unidades") or 0
        p["ventas_ordenes"] = v.get("ordenes") or 0
        techo = p.get("techo_demanda") or 0
        p["capital_pipeline"] = round(techo * PIPELINE_MESES * (p.get("landed") or 0), 2)
        p["sueldo_meseta_teorico"] = round(techo * (p.get("neto") or 0) * 0.95, 2)
    return productos


def analisis(pid, meses=12):
    """Analisis financiero completo de un producto del portafolio."""
    filas = db.rows("SELECT * FROM products WHERE id=?", (pid,))
    if not filas:
        return {"ok": False, "mensaje": f"No existe el producto id={pid}."}
    p = filas[0]
    m = _metricas(p["costo"] or 0, p["flete"] or 0, p["arancel_pct"] or 0,
                  p["prep"] or 0, p["fba_fee"] or config.FBA_FEE_DEFAULT)
    techo = int(p["techo_demanda"] or 0)
    capital = techo * PIPELINE_MESES * m["landed"]
    proy = proyeccion_realista(capital, m["landed"], m["precio"], m["neto"],
                               techo_demanda=techo, meses=meses) if techo > 0 else None
    ventas = db.rows(
        "SELECT fecha, unidades, precio, ingreso, neto, pais, segmento FROM orders "
        "WHERE asin=? ORDER BY id DESC LIMIT 100", (p.get("asin") or "",))
    tot = _ventas_por_asin().get(p.get("asin") or "", {})
    return {
        "ok": True, "producto": p, "unit_economics": m,
        "capital_pipeline": round(capital, 2),
        "proyeccion": proy,
        "ventas_reales": {
            "ingreso": round(tot.get("ingreso") or 0, 2),
            "neto": round(tot.get("neto") or 0, 2),
            "unidades": tot.get("unidades") or 0,
            "ordenes": tot.get("ordenes") or 0,
            "ultimas": ventas,
        },
    }


def resumen_portafolio():
    """Consolidado del negocio: lo proyectado (motor de pricing/caja) vs lo real (orders)."""
    prods = listar(solo_activos=True)
    if not prods:
        return {"ok": True, "n_productos": 0, "productos": [],
                "mensaje": "Portafolio vacio: guarda un producto desde Pricing."}
    capital = sum(p["capital_pipeline"] for p in prods)
    sueldo = sum(p["sueldo_meseta_teorico"] for p in prods)
    ingreso_real = sum(p["ventas_ingreso"] for p in prods)
    neto_real = sum(p["ventas_neto"] for p in prods)
    margen_prom = (sum((p["margen"] or 0) for p in prods) / len(prods))
    semaforos = {"verde": 0, "amarillo": 0, "rojo": 0}
    for p in prods:
        if p.get("semaforo") in semaforos:
            semaforos[p["semaforo"]] += 1
    return {
        "ok": True, "n_productos": len(prods),
        "capital_pipeline_total": round(capital, 2),
        "sueldo_meseta_proyectado": round(sueldo, 2),
        "ingreso_real": round(ingreso_real, 2),
        "neto_real": round(neto_real, 2),
        "margen_promedio_pct": round(margen_prom, 1),
        "semaforos": semaforos,
        "productos": prods,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Portafolio de productos FBA (CLI).")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--resumen", action="store_true")
    ap.add_argument("--analisis", type=int, metavar="ID")
    ap.add_argument("--estimar-ventas", type=int, metavar="ID",
                    help="estima ventas de mercado del ASIN y las guarda en la ficha")
    ap.add_argument("--bsr", default=None,
                    help="BSR publico de Amazon (numero o bloque 'Best Sellers "
                         "Rank' pegado): estima GRATIS, sin API")
    ap.add_argument("--categoria", default=None,
                    help="categoria principal del ASIN (afina la curva del BSR)")
    args = ap.parse_args(argv)
    db.init()
    if args.estimar_ventas:
        out = estimar_ventas(args.estimar_ventas, bsr=args.bsr,
                             categoria=args.categoria)
    elif args.analisis:
        out = analisis(args.analisis)
    elif args.resumen:
        out = resumen_portafolio()
    else:
        out = listar(solo_activos=False)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
