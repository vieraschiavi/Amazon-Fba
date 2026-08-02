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
import re
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
from data import jungle_scout                   # noqa: E402

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
    # Jungle Scout primero si esta conectado (da ventas + rating + reseñas
    # directos, sin la curva BSR gruesa). Si no, se cae a Keepa; si tampoco,
    # a los links libres de abajo. Los links_amazon ya van en toda respuesta.
    if config.JUNGLE_SCOUT_API_KEY and config.JUNGLE_SCOUT_KEY_NAME:
        r = jungle_scout.buscar_productos(keyword, precio_min, precio_max, max_n)
        if r.get("ok"):
            return {"ok": True, "fuente": "Jungle Scout",
                    "productos": r["productos"][:max_n], "links_amazon": la,
                    "costo_tokens": 0, "mensaje": r["mensaje"]}
        # JS conectado pero sin resultados/erro y ADEMAS hay Keepa -> intenta Keepa;
        # si no hay Keepa, devuelve el estado honesto de JS con los links libres.
        if not config.KEEPA_API_KEY:
            return {"ok": False, "fuente": r.get("fuente", "Jungle Scout"),
                    "productos": [], "links_amazon": la, "costo_tokens": 0,
                    "mensaje": r["mensaje"]}
    if not config.KEEPA_API_KEY:
        return {"ok": False, "fuente": "sin_clave", "productos": [],
                "links_amazon": la, "costo_tokens": 0,
                "mensaje": ("Sin Keepa ni Jungle Scout no hay datos "
                            "programaticos de productos (el sistema no scrapea "
                            "Amazon). Usa los links filtrados por precio para "
                            "mirar a mano, o conecta Keepa (~19 EUR/mes) o "
                            "Jungle Scout (API) en Config.")}
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


# --------------------------------------------------------------------------- #
# Potencial de un PRODUCTO dentro de su nicho
# --------------------------------------------------------------------------- #
# OJO: esto es un score NUEVO y distinto del score de NICHO de
# agents/market_intel.py (que mide ganabilidad del nicho con la formula
# 0.35/0.30/0.35 y NO se toca). Este mide otra cosa: dado un nicho, que tan
# atractivo es meterse contra ESE competidor puntual.
#
# Formula, explicita para que se pueda discutir y ajustar:
#   40%  demanda      -> cuanto vende (log, porque 2000 u/mes no es "el doble
#                        de bueno" que 1000: ya es mercado grande en los dos casos)
#   25%  hueco de calidad -> rating bajo del competidor = clientes insatisfechos
#   20%  barrera baja  -> pocas resenas = se le puede alcanzar
#   15%  precio        -> precio alto = mas aire para margen
#
# NO mide margen: eso lo decide el pricing con tu costo real. Un potencial alto
# con un landed cost malo sigue siendo un mal negocio.
PESOS_POTENCIAL = {"demanda": 0.40, "calidad": 0.25, "barrera": 0.20, "precio": 0.15}


def _norm_log(valor, techo):
    """Normaliza 0-1 en escala log (rendimientos decrecientes)."""
    import math
    if not valor or valor <= 0:
        return 0.0
    return min(1.0, math.log10(1 + valor) / math.log10(1 + techo))


def potencial_producto(ventas=None, rating=None, resenas=None, precio=None,
                       detalle=False):
    """Potencial 0-100 de competirle a un producto. None si no hay con que.

    Cada componente que falta se excluye y los pesos se renormalizan, para no
    castigar a un producto solo porque el export no traia esa columna.

    OJO CON COMPARAR ENTRE FUENTES: pegando a mano solo hay ventas y precio (2
    de 4 componentes); un export trae ademas rating y resenas (4 de 4). Los dos
    dan un numero 0-100, pero NO miden lo mismo. Por eso `detalle=True` devuelve
    tambien que componentes se usaron, y quien muestra el numero avisa cuando es
    parcial en vez de fingir que son equivalentes."""
    partes = {}
    if ventas:
        partes["demanda"] = _norm_log(ventas, 3000)
    if rating:
        # 5.0 = no hay hueco; 3.5 o menos = hueco grande.
        partes["calidad"] = max(0.0, min(1.0, (5.0 - float(rating)) / 1.5))
    if resenas is not None:
        # 0 resenas = barrera nula; 3000+ = barrera total.
        partes["barrera"] = 1.0 - _norm_log(resenas, 3000)
    if precio:
        partes["precio"] = max(0.0, min(1.0, (float(precio) - 8.0) / 42.0))
    if not partes:
        return None if not detalle else {"potencial": None, "componentes": [],
                                         "parcial": True}
    total_peso = sum(PESOS_POTENCIAL[k] for k in partes)
    score = round(sum(PESOS_POTENCIAL[k] * v for k, v in partes.items())
                  / total_peso * 100, 1)
    if not detalle:
        return score
    return {"potencial": score, "componentes": sorted(partes),
            "parcial": len(partes) < len(PESOS_POTENCIAL)}


# --------------------------------------------------------------------------- #
# Vendedores principales SIN API (camino gratis)
# --------------------------------------------------------------------------- #
_RE_ASIN = re.compile(r"\b(B0[A-Z0-9]{8})\b")
_RE_PRECIO = re.compile(r"(?:US\$|\$|USD\s*)\s*([\d]+(?:[.,]\d{1,2})?)")


def _precio_de(linea):
    m = _RE_PRECIO.search(linea)
    if not m:
        return None
    try:
        return round(float(m.group(1).replace(",", ".")), 2)
    except ValueError:
        return None


def vendedores_principales(texto):
    """Rankea a los vendedores principales de un nicho SIN ninguna API paga.

    Le pegas un bloque con un competidor por linea, con lo que ya ves en la
    pagina de Amazon. Cada linea puede traer ASIN, BSR y precio, en cualquier
    orden y con texto alrededor:

        B08XYZ1234  #1,234 in Home & Kitchen   $24.99
        B07ABC5678  #5,600                     $19.99

    Devuelve {ok, fuente, productos[], competencia, mensaje}: cada producto con
    sus ventas/mes estimadas por la curva del BSR y su CUOTA sobre el total
    pegado. Las lineas sin BSR se listan igual pero sin estimacion -- no se les
    inventa un numero.

    Limite honesto y explicito: la cuota es sobre los competidores QUE PEGASTE,
    no sobre el nicho entero. Si pegas 5 de 300 vendedores, el 40% que muestre
    el lider es 40% de esos 5. Sirve para comparar entre ellos, no para decir
    "tengo el 40% del mercado".
    """
    from data import bsr as bsr_mod

    lineas = [l.strip() for l in (texto or "").splitlines() if l.strip()]
    if not lineas:
        return {"ok": False, "fuente": "sin_datos", "productos": [],
                "competencia": {"ok": False, "n_competidores": 0},
                "mensaje": "Pegá un competidor por línea, con su ASIN y su BSR "
                           "(el que figura en \"Best Sellers Rank\" de cada producto)."}

    productos, sin_bsr = [], 0
    for linea in lineas:
        m_asin = _RE_ASIN.search(linea.upper())
        asin = m_asin.group(1) if m_asin else None
        # Se saca el ASIN antes de buscar el BSR: un ASIN como B08XYZ1234 tiene
        # digitos y podria confundir al parser de ranking.
        resto = linea.upper().replace(asin, " ") if asin else linea
        lectura = bsr_mod.parsear_bloque(resto)
        item = {
            "asin": asin,
            "titulo": re.sub(r"\s+", " ", linea)[:120],
            "precio": _precio_de(linea),
            "bsr": lectura.get("bsr") if lectura.get("ok") else None,
            "categoria": lectura.get("categoria") if lectura.get("ok") else None,
            "link": f"https://www.amazon.com/dp/{asin}" if asin else None,
            "link_resenas": link_resenas(asin) if asin else None,
        }
        if item["bsr"]:
            item["ventas_estim"] = bsr_mod.ventas_desde_bsr(item["bsr"], item["categoria"])
            item["confianza"] = bsr_mod.confianza_de(item["bsr"], item["categoria"])
        else:
            item["ventas_estim"] = None
            item["confianza"] = None
            sin_bsr += 1
        # Pegando a mano no hay rating ni resenas: el potencial sale con 2 de 4
        # componentes y se marca como parcial para no compararlo de igual a
        # igual contra el de un export completo.
        det = potencial_producto(ventas=item["ventas_estim"],
                                 precio=item["precio"], detalle=True)
        item["potencial"] = det["potencial"]
        item["potencial_parcial"] = det["parcial"]
        productos.append(item)

    con_venta = [p for p in productos if p.get("ventas_estim")]
    total = sum(p["ventas_estim"] for p in con_venta)
    for p in productos:
        v = p.get("ventas_estim")
        p["cuota_pct"] = round(v * 100.0 / total, 1) if (v and total) else None
        p["ingreso_estim_mes"] = (round(v * p["precio"], 2)
                                  if v and p.get("precio") else None)

    # Los que tienen estimacion primero, de mayor a menor.
    productos.sort(key=lambda p: (p.get("ventas_estim") or -1), reverse=True)

    avisos = []
    if sin_bsr:
        avisos.append(f"{sin_bsr} línea(s) sin BSR: se listan sin estimación "
                      "(no se inventa el número).")
    if con_venta:
        avisos.append(f"{len(con_venta)} competidor(es) estimados por la curva del "
                      f"BSR: {total:,} u/mes entre ellos.".replace(",", "."))
    return {
        "ok": bool(con_venta),
        "fuente": "BSR de Amazon (curva)",
        "productos": productos,
        "competencia": resumen_competencia(productos),
        "ventas_estim_total": total,
        "ventas_estim_lider": max((p["ventas_estim"] for p in con_venta), default=0),
        "mensaje": (" ".join(avisos) or
                    "Ninguna línea traía un BSR legible, así que no hay estimación.") +
                   " La cuota es sobre los competidores que pegaste, no sobre el nicho entero.",
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
