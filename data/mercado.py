#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/mercado.py — Explorador de mercado de MV FBA IA.

Completa el modulo estilo Helium 10 / Jungle Scout con datos de PRODUCTOS:

  - productos_estrella(): los productos que mejor venden para una keyword y un
    rango de precios, con precio, BSR, ventas estimadas, rating y reseñas.
    FUENTE REAL: Keepa Product Finder (/query) + detalle de producto — requiere
    KEEPA_API_KEY (~19 EUR/mes; cuesta ~10 tokens la busqueda + 1 por producto).
    Sin clave -> estado vacio explicado + links directos a Amazon filtrados por
    precio para mirar a mano (el sistema NO scrapea Amazon: viola sus terminos).
  - resumen_competencia(): senales agregadas de los competidores (cuantos son,
    rating promedio, mediana de reseñas, precios) para el asesor de exito.
  - links_amazon() / links_proveedores(): links directos y filtrados para ver
    competidores y contactar proveedores MEJOR RANKEADOS (Alibaba con Trade
    Assurance + Verified Supplier, 1688, Global Sources, Made-in-China).

HONESTIDAD: las ventas se estiman con la curva BSR->ventas (gruesa, documentada
en data/keepa.py). El texto de reseñas no se scrapea: se linkea y se analiza
pegandolo en el Asistente IA.
"""
import argparse
import json
import os
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import config                                   # noqa: E402
from data.keepa import _estim_ventas           # noqa: E402

_QUERY_URL = "https://api.keepa.com/query"
_PRODUCT_URL = "https://api.keepa.com/product"
_UA = "mv-amazon-fba-ia/1.0"


# --------------------------------------------------------------------------- #
# Links directos (siempre disponibles, gratis)
# --------------------------------------------------------------------------- #
def links_amazon(keyword, precio_min=None, precio_max=None):
    """Links a Amazon US: mas vendidos y filtrado por rango de precios."""
    q = urllib.parse.quote_plus(keyword)
    links = [{"nombre": "Resultados ordenados por popularidad",
              "url": f"https://www.amazon.com/s?k={q}&s=exact-aware-popularity-rank"},
             {"nombre": "Best Sellers de la busqueda",
              "url": f"https://www.amazon.com/s?k={q}"}]
    if precio_min is not None and precio_max is not None and precio_max > 0:
        lo, hi = int(precio_min * 100), int(precio_max * 100)
        links.insert(0, {
            "nombre": f"Filtrado USD {precio_min:.0f}-{precio_max:.0f} por popularidad",
            "url": (f"https://www.amazon.com/s?k={q}&rh=p_36%3A{lo}-{hi}"
                    f"&s=exact-aware-popularity-rank")})
    return links


def links_proveedores(keyword):
    """
    Links de contacto a proveedores MEJOR RANKEADOS del producto.
    Alibaba se filtra por Trade Assurance + Verified Supplier (los rankings
    de seriedad reales de la plataforma); el resto son directorios B2B serios.
    """
    q = urllib.parse.quote_plus(keyword)
    return [
        {"plataforma": "Alibaba (Trade Assurance + Verified)", "prioridad": 1,
         "url": f"https://www.alibaba.com/trade/search?SearchText={q}&ta=y&assessment_company=y",
         "nota": "El filtro ya deja solo proveedores verificados con pago protegido. "
                 "Ordena por 'Transaction Level' y contacta 5-8 con el RFQ del sistema."},
        {"plataforma": "Alibaba RFQ Marketplace", "prioridad": 2,
         "url": "https://rfq.alibaba.com/",
         "nota": "Publica el RFQ y deja que los proveedores compitan por tu orden."},
        {"plataforma": "Global Sources", "prioridad": 3,
         "url": f"https://www.globalsources.com/searchList/products?keyWord={q}",
         "nota": "Proveedores auditados; fuerte en electronica y hogar."},
        {"plataforma": "Made-in-China (Audited Suppliers)", "prioridad": 4,
         "url": f"https://www.made-in-china.com/products-search/hot-china-products/{q}.html",
         "nota": "Filtra por 'Audited Supplier'."},
        {"plataforma": "1688 (mayorista China, precios fabrica)", "prioridad": 5,
         "url": f"https://s.1688.com/selloffer/offer_search.htm?keywords={q}",
         "nota": "Precios mas bajos pero en chino y sin Trade Assurance export: "
                 "usalo para negociar, compra via agente o Alibaba."},
    ]


def link_resenas(asin):
    return f"https://www.amazon.com/product-reviews/{asin}/?sortBy=recent"


# --------------------------------------------------------------------------- #
# Productos estrella (Keepa Product Finder) — datos reales con clave
# --------------------------------------------------------------------------- #
def _keepa_query(keyword, precio_min, precio_max, max_n, timeout=30):
    """POST /query de Keepa (Product Finder). Devuelve lista de ASIN."""
    seleccion = {
        "title": keyword,
        "current_NEW_gte": int(precio_min * 100),
        "current_NEW_lte": int(precio_max * 100),
        "current_SALES_gte": 1,           # con ranking de ventas real
        "sort": [["current_SALES", "asc"]],
        "productType": [0, 1],
        "perPage": max(10, min(50, max_n * 2)),
        "page": 0,
    }
    url = (_QUERY_URL + "?" + urllib.parse.urlencode(
        {"key": config.KEEPA_API_KEY, "domain": config.KEEPA_DOMAIN}))
    req = urllib.request.Request(
        url, data=json.dumps(seleccion).encode("utf-8"),
        headers={"User-Agent": _UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data.get("asinList") or []


def _keepa_detalles(asins, timeout=30):
    """Detalle de hasta 10 ASIN en un request (precio, BSR, rating, reseñas)."""
    params = urllib.parse.urlencode({
        "key": config.KEEPA_API_KEY, "domain": config.KEEPA_DOMAIN,
        "asin": ",".join(asins[:10]), "stats": 90, "rating": 1})
    req = urllib.request.Request(f"{_PRODUCT_URL}?{params}",
                                 headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = []
    for p in data.get("products") or []:
        stats = p.get("stats") or {}
        cur = stats.get("current") or []

        def val(idx, div=1.0):
            if len(cur) > idx and cur[idx] is not None and cur[idx] >= 0:
                return cur[idx] / div
            return None

        precio = val(1, 100.0) or val(0, 100.0)      # NEW, si no AMAZON (USD)
        bsr = val(3)                                  # SALES rank
        rating = val(16, 10.0)                        # RATING viene 0-50
        resenas = val(17)                             # COUNT_REVIEWS
        asin = p.get("asin", "")
        out.append({
            "asin": asin, "titulo": (p.get("title") or "")[:120],
            "precio": round(precio, 2) if precio else None,
            "bsr": int(bsr) if bsr else None,
            "ventas_estim": _estim_ventas(int(bsr)) if bsr else 0,
            "rating": round(rating, 1) if rating else None,
            "resenas": int(resenas) if resenas else 0,
            "link": f"https://www.amazon.com/dp/{asin}",
            "link_resenas": link_resenas(asin),
        })
    return out


def demo_estrellas(keyword, precio_min, precio_max):
    base = [
        ("B0DEMO0001", f"[DEMO] {keyword} premium set 12pc", 24.99, 3200, 4.6, 2840),
        ("B0DEMO0002", f"[DEMO] {keyword} eco bundle", 19.99, 5400, 4.4, 1520),
        ("B0DEMO0003", f"[DEMO] {keyword} pro edition", 29.99, 8100, 4.7, 4310),
        ("B0DEMO0004", f"[DEMO] {keyword} starter kit", 16.99, 12400, 4.1, 640),
        ("B0DEMO0005", f"[DEMO] {keyword} deluxe holder", 22.49, 15800, 4.3, 890),
        ("B0DEMO0006", f"[DEMO] {keyword} compact", 14.99, 21700, 3.9, 310),
    ]
    prods = [{"asin": a, "titulo": t, "precio": pr, "bsr": b,
              "ventas_estim": _estim_ventas(b), "rating": ra, "resenas": re,
              "link": f"https://www.amazon.com/dp/{a}",
              "link_resenas": link_resenas(a)}
             for a, t, pr, b, ra, re in base
             if precio_min <= pr <= precio_max] or []
    return prods


def productos_estrella(keyword, precio_min=10.0, precio_max=50.0, max_n=10,
                       demo=False):
    """
    Productos que mejor venden para `keyword` en el rango de precios.
    Devuelve {ok, fuente, productos[], links_amazon, mensaje, costo_tokens}.
    """
    keyword = (keyword or "").strip()
    la = links_amazon(keyword, precio_min, precio_max)
    if demo:
        prods = demo_estrellas(keyword, precio_min, precio_max)
        return {"ok": bool(prods), "fuente": "DEMO", "productos": prods,
                "links_amazon": la, "costo_tokens": 0,
                "mensaje": "Datos [DEMO] ilustrativos (no reales)."}
    if not keyword or len(keyword) < 3:
        return {"ok": False, "fuente": "sin_datos", "productos": [],
                "links_amazon": la, "costo_tokens": 0,
                "mensaje": "Escribi una keyword de al menos 3 letras."}
    if not config.KEEPA_API_KEY:
        return {"ok": False, "fuente": "sin_clave", "productos": [],
                "links_amazon": la, "costo_tokens": 0,
                "mensaje": ("Sin KEEPA_API_KEY no hay datos programaticos de "
                            "productos (el sistema no scrapea Amazon). Usa los "
                            "links filtrados por precio para mirar a mano, o "
                            "conecta Keepa (~19 EUR/mes) en Config.")}
    try:
        asins = _keepa_query(keyword, precio_min, precio_max, max_n)
        if not asins:
            return {"ok": False, "fuente": "Keepa", "productos": [],
                    "links_amazon": la, "costo_tokens": 10,
                    "mensaje": "Keepa no encontro productos con esos filtros. "
                               "Proba un rango de precios mas amplio."}
        prods = _keepa_detalles(asins[:max_n])
        prods.sort(key=lambda p: (p["bsr"] or 10**9))
        return {"ok": True, "fuente": "Keepa Product Finder",
                "productos": prods[:max_n], "links_amazon": la,
                "costo_tokens": 10 + len(prods),
                "mensaje": f"{len(prods)} productos reales via Keepa."}
    except urllib.error.HTTPError as e:
        det = "clave invalida o sin tokens" if e.code in (400, 401, 402, 403) \
              else f"HTTP {e.code}"
        return {"ok": False, "fuente": "error", "productos": [],
                "links_amazon": la, "costo_tokens": 0,
                "mensaje": f"Keepa rechazo la consulta ({det})."}
    except Exception as e:
        return {"ok": False, "fuente": "error", "productos": [],
                "links_amazon": la, "costo_tokens": 0,
                "mensaje": f"Error de red consultando Keepa: {e}"}


# --------------------------------------------------------------------------- #
# Resumen de competencia (insumo del asesor de exito)
# --------------------------------------------------------------------------- #
def resumen_competencia(productos):
    """Senales agregadas de los competidores para evaluar la entrada al nicho."""
    validos = [p for p in productos if p.get("precio")]
    if not validos:
        return {"ok": False, "n_competidores": 0}
    ratings = [p["rating"] for p in validos if p.get("rating")]
    resenas = [p["resenas"] for p in validos if p.get("resenas") is not None]
    precios = [p["precio"] for p in validos]
    ventas = [p.get("ventas_estim") or 0 for p in validos]
    return {
        "ok": True,
        "n_competidores": len(validos),
        "rating_promedio": round(statistics.mean(ratings), 2) if ratings else None,
        "resenas_mediana": int(statistics.median(resenas)) if resenas else 0,
        "resenas_max": max(resenas) if resenas else 0,
        "precio_min": min(precios), "precio_max": max(precios),
        "precio_mediana": round(statistics.median(precios), 2),
        "ventas_estim_total": int(sum(ventas)),
        "ventas_estim_lider": max(ventas) if ventas else 0,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Explorador de mercado (productos estrella).")
    ap.add_argument("--keyword", default="bamboo kitchen utensils")
    ap.add_argument("--min", type=float, default=10.0)
    ap.add_argument("--max", type=float, default=50.0)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args(argv)
    r = productos_estrella(args.keyword, args.min, args.max, demo=args.demo)
    print(json.dumps({**r, "competencia": resumen_competencia(r["productos"]),
                      "proveedores": links_proveedores(args.keyword)},
                     ensure_ascii=False, indent=2))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
