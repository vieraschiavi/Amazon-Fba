#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/helium_productos.py — Importador de exports de PRODUCTOS (no de keywords).

QUE PROBLEMA RESUELVE
---------------------
data/bsr.py ya permite estimar las ventas de un ASIN gratis, pegando su BSR. Lo
que seguia sin poder hacerse gratis era el DESCUBRIMIENTO: saber QUE ASINs
rankean para una keyword. Para eso hace falta Keepa, Jungle Scout... o un export
de una herramienta que el usuario YA paga.

Este modulo lee esos exports de producto y de ahi salen los vendedores
principales del nicho, con sus ventas mensuales, de una sola vez:

  - Helium 10 Xray (extension) y Black Box (busqueda de productos)
  - Jungle Scout Product Database / Product Tracker

Son herramientas distintas con nombres de columna distintos, asi que se resuelve
por alias igual que en data/cerebro.py (que hace lo mismo para keywords).

DE DONDE SALE EL NUMERO DE VENTAS (regla del proyecto: sin datos inventados)
---------------------------------------------------------------------------
Por orden de preferencia, y SIEMPRE etiquetado:

  1) La columna de ventas del propio export. Es la estimacion de Helium 10 o de
     Jungle Scout, calibrada con datos que nosotros no tenemos. Si viene, manda.
  2) Si el export no trae ventas pero si BSR, se convierte con la curva de
     data/bsr.py, y se etiqueta como tal para que se note que es mas gruesa.
  3) Si no trae ni una ni otra, la fila se lista SIN numero. No se rellena.

Nunca se mezclan las dos fuentes en un mismo numero sin decir cual se uso.
"""
import argparse
import csv
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from data import bsr as bsr_mod                    # noqa: E402
from data import mercado                           # noqa: E402  (potencial_producto)
from data.cerebro import _num                      # noqa: E402  (mismo parser US/EU)

# Alias reales de columna de cada herramienta. Todo en minuscula: el matcheo
# normaliza el header antes de comparar.
COLUMN_ALIASES = {
    "asin": ["asin", "asin principal", "parent asin", "child asin"],
    "titulo": ["product details", "title", "product name", "producto",
               "product title", "nombre del producto", "titulo", "título"],
    "marca": ["brand", "marca"],
    "precio": ["price", "price $", "precio", "current price", "buy box price",
               "precio actual"],
    # Ventas en UNIDADES por mes (lo que mas nos importa).
    "ventas": ["sales", "monthly sales", "est. monthly sales", "estimated sales",
               "est. sales", "ventas", "ventas mensuales", "unidades vendidas",
               "sales/mo", "monthly units sold", "est. monthly units sold"],
    "ingresos": ["revenue", "monthly revenue", "est. monthly revenue",
                 "estimated revenue", "ingresos", "ingresos mensuales",
                 "revenue/mo", "est. revenue"],
    "bsr": ["bsr", "best seller rank", "best sellers rank", "rank",
            "sales rank", "ranking", "clasificacion", "clasificación",
            "bsr actual", "current bsr"],
    "categoria": ["category", "categoria", "categoría", "product category",
                  "top level category", "parent category"],
    "resenas": ["review count", "reviews", "resenas", "reseñas",
                "number of reviews", "ratings count"],
    "rating": ["rating", "ratings", "calificacion", "calificación",
               "average rating", "star rating"],
    "vendedor": ["seller", "vendedor", "seller name", "fulfillment",
                 "fulfilled by", "seller country"],
}


def _resolver_columnas(headers):
    norm = {(h or "").strip().lower(): h for h in headers}
    mapeo = {}
    for clave, alias in COLUMN_ALIASES.items():
        for a in alias:
            if a in norm:
                mapeo[clave] = norm[a]
                break
    return mapeo


def parse_productos_csv(path):
    """Lee un export de productos y devuelve la lista de filas normalizadas.

    Levanta ValueError si el CSV no parece un export de productos (para no
    confundirlo con el de keywords de Cerebro, que se sube por otra puerta)."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        muestra = f.read(8192)
        f.seek(0)
        try:
            dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t")
        except csv.Error:
            dialecto = csv.excel
        reader = csv.DictReader(f, dialect=dialecto)
        if not reader.fieldnames:
            return []
        eu = getattr(dialecto, "delimiter", ",") == ";"
        m = _resolver_columnas(reader.fieldnames)
        if "asin" not in m:
            raise ValueError(
                "El CSV no parece un export de PRODUCTOS (Helium 10 Xray/Black Box "
                "o Jungle Scout Product Database): no tiene columna de ASIN. Si es "
                "un export de keywords de Cerebro, subilo en Investigación. "
                "Columnas vistas: "
                + ", ".join(h for h in reader.fieldnames if h))
        if not ({"ventas", "ingresos", "bsr"} & set(m)):
            raise ValueError(
                "El CSV tiene ASIN pero ninguna columna de ventas, ingresos ni BSR, "
                "así que no hay con qué estimar cuánto vende cada producto. "
                "Columnas vistas: "
                + ", ".join(h for h in reader.fieldnames if h))

        filas = []
        for row in reader:
            asin = str(row.get(m["asin"], "")).strip().upper()
            if not asin:
                continue

            def txt(clave):
                return str(row.get(m.get(clave), "") or "").strip()

            def n_opt(clave):
                """None SOLO si la columna no vino o vino vacia -- un valor
                real 0 (0 ventas, 0 resenas: el caso mas interesante, un
                lanzamiento nuevo) se respeta como 0, nunca se confunde con
                "sin dato". El `int(n(clave)) or None` anterior colapsaba las
                dos cosas y tiraba a la basura un 0 real que vino del export."""
                if clave not in m:
                    return None
                crudo = row.get(m[clave])
                if crudo is None or str(crudo).strip() == "":
                    return None
                return _num(crudo, eu=eu)

            precio, ventas = n_opt("precio"), n_opt("ventas")
            ingresos, bsr = n_opt("ingresos"), n_opt("bsr")
            resenas, rating = n_opt("resenas"), n_opt("rating")

            filas.append({
                "asin": asin,
                "titulo": txt("titulo")[:120] or asin,
                "marca": txt("marca") or None,
                "vendedor": txt("vendedor") or None,
                "categoria": txt("categoria") or None,
                "precio": round(precio, 2) if precio is not None else None,
                "ventas_csv": int(ventas) if ventas is not None else None,
                "ingresos_csv": round(ingresos, 2) if ingresos is not None else None,
                "bsr": int(bsr) if bsr is not None else None,
                "resenas": int(resenas) if resenas is not None else None,
                "rating": round(rating, 1) if rating is not None else None,
            })
    # Dedupe por ASIN: se queda con la fila de mas ventas (los exports repiten
    # el mismo ASIN cuando hay variantes).
    por_asin = {}
    for f_ in filas:
        prev = por_asin.get(f_["asin"])
        if prev is None or (f_["ventas_csv"] or 0) > (prev["ventas_csv"] or 0):
            por_asin[f_["asin"]] = f_
    return list(por_asin.values())


def vendedores_desde_csv(path, max_n=25):
    """Vendedores principales del nicho a partir de un export de productos.

    Devuelve la MISMA forma que data/mercado.vendedores_principales(), asi que
    el panel muestra los dos caminos con el mismo codigo."""
    try:
        filas = parse_productos_csv(path)
    except ValueError as e:
        return {"ok": False, "fuente": "csv_invalido", "productos": [],
                "ventas_estim_total": 0, "ventas_estim_lider": 0, "mensaje": str(e)}
    if not filas:
        return {"ok": False, "fuente": "sin_datos", "productos": [],
                "ventas_estim_total": 0, "ventas_estim_lider": 0,
                "mensaje": "El CSV no tenía ninguna fila con ASIN."}

    productos, n_csv, n_curva, n_sin = [], 0, 0, 0
    for f_ in filas:
        if f_["ventas_csv"] is not None:
            # 1) La estimacion propia de la herramienta manda: esta calibrada.
            # "is not None" (no truthy): un 0 real del export (0 ventas, un
            # lanzamiento nuevo) tiene que quedar como 0, no caer al branch de
            # la curva ni al de "sin dato" -- el export YA daba la respuesta.
            ventas, conf, fuente = f_["ventas_csv"], "alta", "CSV (Helium 10 / Jungle Scout)"
            n_csv += 1
        elif f_["bsr"]:
            # 2) Sin ventas pero con BSR: se convierte con la curva (mas grueso).
            # Truthy esta bien aca: un BSR real nunca es 0 (el ranking arranca
            # en 1), asi que no hay un "0 real" que confundir con "sin dato".
            ventas = bsr_mod.ventas_desde_bsr(f_["bsr"], f_["categoria"])
            conf = bsr_mod.confianza_de(f_["bsr"], f_["categoria"])
            fuente = "BSR del CSV (curva)"
            n_curva += 1
        else:
            # 3) Ni ventas ni BSR: se lista sin numero, no se inventa.
            ventas, conf, fuente = None, None, "sin dato"
            n_sin += 1

        ingreso = f_["ingresos_csv"]
        if ingreso is None and ventas is not None and f_["precio"] is not None:
            ingreso = round(ventas * f_["precio"], 2)

        _det_pot = mercado.potencial_producto(
            ventas=ventas, rating=f_["rating"], resenas=f_["resenas"],
            precio=f_["precio"], detalle=True)

        productos.append({
            "asin": f_["asin"], "titulo": f_["titulo"], "marca": f_["marca"],
            "vendedor": f_["vendedor"], "precio": f_["precio"], "bsr": f_["bsr"],
            "categoria": f_["categoria"], "ventas_estim": ventas,
            "confianza": conf, "fuente_ventas": fuente,
            "ingreso_estim_mes": ingreso, "resenas": f_["resenas"],
            "rating": f_["rating"],
            # Un export suele traer rating y resenas, asi que el potencial sale
            # con los 4 componentes (el camino de pegado a mano solo tiene 2).
            # Igual se marca si esta fila quedo parcial: no todos los exports
            # traen todas las columnas.
            "potencial": _det_pot["potencial"],
            "potencial_parcial": _det_pot["parcial"],
            "link": f"https://www.amazon.com/dp/{f_['asin']}",
        })

    # "is not None": un 0 real (fila con ventas_estim=0, ya cubierta arriba) es
    # una estimacion valida -- no es lo mismo que la fila sin ninguna fuente.
    con_venta = [p for p in productos if p.get("ventas_estim") is not None]
    total = sum(p["ventas_estim"] for p in con_venta)
    for p in productos:
        v = p.get("ventas_estim")
        p["cuota_pct"] = round(v * 100.0 / total, 1) if (v is not None and total) else None

    productos.sort(key=lambda p: (p.get("ventas_estim") or -1), reverse=True)
    recortado = len(productos) > max_n
    productos = productos[:max_n]

    avisos = []
    if n_csv:
        avisos.append(f"{n_csv} con ventas del propio export (fuente calibrada).")
    if n_curva:
        avisos.append(f"{n_curva} sin ventas en el CSV: estimados por la curva del BSR.")
    if n_sin:
        avisos.append(f"{n_sin} sin ventas ni BSR: listados sin número (no se inventa).")
    if recortado:
        avisos.append(f"Se muestran los {max_n} que más venden de {len(filas)}.")

    return {
        "ok": bool(con_venta),
        "fuente": "Export de productos (Helium 10 / Jungle Scout)",
        "productos": productos,
        "ventas_estim_total": total,
        "ventas_estim_lider": max((p["ventas_estim"] for p in con_venta), default=0),
        "n_filas": len(filas),
        "mensaje": " ".join(avisos) or "No se pudo estimar ninguna fila.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Vendedores principales desde un export de productos "
                    "(Helium 10 Xray/Black Box o Jungle Scout).")
    ap.add_argument("--csv", required=True, help="ruta del export .csv")
    ap.add_argument("--max", type=int, default=25)
    a = ap.parse_args(argv)
    print(json.dumps(vendedores_desde_csv(a.csv, a.max), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
