#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/jungle_scout.py — Fuente programatica de mercado via la API de Jungle Scout.

A diferencia de Helium 10 (que NO expone API, solo export CSV -> ver
data/cerebro.py), Jungle Scout SI tiene API publica (BYOK). Da lo que ni el
motor propio ni Keepa dan bien:
  - volumen de busqueda REAL de keywords (keywords_by_keyword),
  - busqueda de productos por base de datos (product_database_query),
  - estimacion de ventas por ASIN (sales_estimates), sin la curva BSR gruesa.

NO inventa datos: sin las dos claves (nombre + api key) devuelve estado vacio
explicado. Solo libreria estandar (urllib). Nunca lanza al llamador.

Auth de Jungle Scout: header Authorization con el formato "Key_Name:API_Key",
mas los headers de version/tipo que exige su API (JSON:API).

Uso:
    python data/jungle_scout.py --keyword "garlic press"
Importable:
    from data.jungle_scout import estado, buscar_productos, keywords_por_termino
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import config  # noqa: E402

_BASE = "https://developer.junglescout.com/api"
_UA = "mv-amazon-fba-ia/1.0"


def _headers(extra=None):
    """Headers de auth + version que exige la API de Jungle Scout (JSON:API)."""
    h = {
        "Authorization": f"{config.JUNGLE_SCOUT_KEY_NAME}:{config.JUNGLE_SCOUT_API_KEY}",
        "Accept": "application/vnd.junglescout.v1+json",
        "Content-Type": "application/vnd.api+json",
        "X-API-Type": "junglescout",
        "User-Agent": _UA,
    }
    if extra:
        h.update(extra)
    return h


def _configurada():
    return bool(config.JUNGLE_SCOUT_API_KEY and config.JUNGLE_SCOUT_KEY_NAME)


def estado():
    if not _configurada():
        return {"ok": False, "mensaje": (
            "Falta la clave de Jungle Scout en .env (JUNGLE_SCOUT_KEY_NAME + "
            "JUNGLE_SCOUT_API_KEY). Jungle Scout es fuente REAL de volumen de "
            "busqueda y ventas por API. Sin clave no consulta.")}
    return {"ok": True, "mensaje": "Jungle Scout conectado.",
            "marketplace": config.JUNGLE_SCOUT_MARKETPLACE}


def _post(ruta, cuerpo, timeout=30):
    url = f"{_BASE}/{ruta}?marketplace={urllib.parse.quote(config.JUNGLE_SCOUT_MARKETPLACE)}"
    req = urllib.request.Request(
        url, data=json.dumps(cuerpo).encode("utf-8"),
        headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def validar(timeout=20):
    """Valida las claves con una consulta minima (1 producto). Devuelve
    {ok, mensaje}. No distingue costo de tokens (JS no expone un endpoint de
    saldo gratis como Keepa); es la forma mas barata de confirmar el auth."""
    if not _configurada():
        return {"ok": False, "mensaje": estado()["mensaje"]}
    cuerpo = {"data": {"type": "product_database_query",
                       "attributes": {"include_keywords": ["kitchen"]}}}
    try:
        _post("product_database_query?page[size]=1", cuerpo, timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return {"ok": False, "mensaje": "Clave de Jungle Scout invalida "
                                            "o sin permiso (HTTP %d)." % e.code}
        if e.code == 429:
            return {"ok": True, "mensaje": "Clave valida (rate limit momentaneo)."}
        return {"ok": False, "mensaje": f"HTTP {e.code} de Jungle Scout."}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error de red Jungle Scout: {e}"}
    return {"ok": True, "mensaje": "Clave de Jungle Scout valida."}


def _num(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def buscar_productos(keyword, precio_min=10.0, precio_max=50.0, max_n=10, timeout=30):
    """Productos que mejor venden para `keyword` en el rango de precios, via
    Product Database. Mismo shape que consume data/mercado.resumen_competencia:
    {ok, fuente, productos:[{asin, titulo, precio, bsr, ventas_estim, rating,
    resenas, link, link_resenas}], mensaje}."""
    keyword = (keyword or "").strip()
    if not _configurada():
        return {"ok": False, "fuente": "sin_clave", "productos": [],
                "mensaje": estado()["mensaje"]}
    if len(keyword) < 3:
        return {"ok": False, "fuente": "sin_datos", "productos": [],
                "mensaje": "Escribi una keyword de al menos 3 letras."}
    cuerpo = {"data": {"type": "product_database_query", "attributes": {
        "include_keywords": [keyword],
        "min_price": float(precio_min), "max_price": float(precio_max),
        "min_sales": 1}}}
    try:
        data = _post(f"product_database_query?page[size]={max(1, min(50, max_n))}",
                     cuerpo, timeout=timeout)
    except urllib.error.HTTPError as e:
        det = "clave invalida o sin permiso" if e.code in (401, 403) else f"HTTP {e.code}"
        return {"ok": False, "fuente": "error", "productos": [],
                "mensaje": f"Jungle Scout rechazo la consulta ({det})."}
    except Exception as e:
        return {"ok": False, "fuente": "error", "productos": [],
                "mensaje": f"Error de red consultando Jungle Scout: {e}"}
    prods = []
    for item in (data.get("data") or [])[:max_n]:
        a = item.get("attributes") or {}
        asin = a.get("asin") or ""
        precio = _num(a.get("price"))
        bsr = a.get("category_rank") or a.get("rank")
        ventas = a.get("approximate_30_day_units_sold") or a.get("estimated_monthly_sales")
        prods.append({
            "asin": asin, "titulo": (a.get("title") or "")[:120],
            "precio": round(precio, 2) if precio else None,
            "bsr": int(bsr) if bsr else None,
            "ventas_estim": int(ventas) if ventas else 0,
            "rating": _num(a.get("rating")),
            "resenas": int(a.get("reviews") or 0),
            "link": f"https://www.amazon.com/dp/{asin}" if asin else "",
            "link_resenas": (f"https://www.amazon.com/product-reviews/{asin}/"
                             "?sortBy=recent") if asin else "",
        })
    if not prods:
        return {"ok": False, "fuente": "Jungle Scout", "productos": [],
                "mensaje": "Jungle Scout no encontro productos con esos filtros. "
                           "Proba un rango de precios mas amplio."}
    return {"ok": True, "fuente": "Jungle Scout", "productos": prods,
            "mensaje": f"{len(prods)} productos reales via Jungle Scout."}


def keywords_por_termino(termino, max_n=20, timeout=30):
    """Volumen de busqueda REAL de keywords relacionadas a `termino`
    (Keyword by Keyword). Devuelve {ok, keywords:[{keyword, volumen,
    competidores}], mensaje} -- el diferencial vs motor propio (que solo
    aproxima interes) y Keepa (que no da volumen de keywords)."""
    termino = (termino or "").strip()
    if not _configurada():
        return {"ok": False, "keywords": [], "mensaje": estado()["mensaje"]}
    if len(termino) < 3:
        return {"ok": False, "keywords": [], "mensaje": "Escribi un termino de al menos 3 letras."}
    cuerpo = {"data": {"type": "keywords_by_keyword_query", "attributes": {
        "search_terms": termino}}}
    try:
        data = _post(f"keywords/keywords_by_keyword_query?page[size]={max(1, min(50, max_n))}",
                     cuerpo, timeout=timeout)
    except urllib.error.HTTPError as e:
        det = "clave invalida o sin permiso" if e.code in (401, 403) else f"HTTP {e.code}"
        return {"ok": False, "keywords": [], "mensaje": f"Jungle Scout rechazo la consulta ({det})."}
    except Exception as e:
        return {"ok": False, "keywords": [], "mensaje": f"Error de red consultando Jungle Scout: {e}"}
    kws = []
    for item in (data.get("data") or [])[:max_n]:
        a = item.get("attributes") or {}
        vol = a.get("monthly_search_volume_exact") or a.get("estimated_exact_search_volume")
        kws.append({
            "keyword": a.get("name") or a.get("keyword") or "",
            "volumen": int(vol) if vol else 0,
            "competidores": int(a.get("competed_products") or a.get("competitor_products") or 0),
        })
    if not kws:
        return {"ok": False, "keywords": [], "mensaje": "Jungle Scout no devolvio keywords para ese termino."}
    return {"ok": True, "keywords": kws,
            "mensaje": f"{len(kws)} keywords con volumen real via Jungle Scout."}


def ventas_asin(asin, timeout=25):
    """Estimacion de ventas mensuales de un ASIN (Sales Estimates). Devuelve
    {ok, asin, ventas_estim, mensaje}."""
    asin = (asin or "").strip()
    if not _configurada():
        return {"ok": False, "asin": asin, "mensaje": estado()["mensaje"]}
    if not asin:
        return {"ok": False, "asin": asin, "mensaje": "Falta el ASIN."}
    url = (f"{_BASE}/sales_estimates?"
           + urllib.parse.urlencode({"marketplace": config.JUNGLE_SCOUT_MARKETPLACE, "asin": asin}))
    try:
        req = urllib.request.Request(url, headers=_headers(), method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        det = "clave invalida o sin permiso" if e.code in (401, 403) else f"HTTP {e.code}"
        return {"ok": False, "asin": asin, "mensaje": f"Jungle Scout rechazo la consulta ({det})."}
    except Exception as e:
        return {"ok": False, "asin": asin, "mensaje": f"Error de red Jungle Scout: {e}"}
    filas = data.get("data") or []
    total = 0
    for item in filas:
        a = item.get("attributes") or {}
        total += int(a.get("estimated_units_sold") or 0)
    if not filas:
        return {"ok": False, "asin": asin, "mensaje": "ASIN sin datos de ventas en Jungle Scout."}
    return {"ok": True, "asin": asin, "ventas_estim": total,
            "mensaje": "Ventas estimadas reales via Jungle Scout."}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Consulta Jungle Scout (productos + keywords + ventas).")
    ap.add_argument("--keyword", help="Keyword para productos + volumen.")
    ap.add_argument("--asin", help="ASIN para estimacion de ventas.")
    ap.add_argument("--min", type=float, default=10.0)
    ap.add_argument("--max", type=float, default=50.0)
    args = ap.parse_args(argv)
    print("Estado:", json.dumps(estado(), ensure_ascii=False))
    if args.asin:
        print(json.dumps(ventas_asin(args.asin), ensure_ascii=False, indent=2))
    if args.keyword:
        print(json.dumps(buscar_productos(args.keyword, args.min, args.max),
                         ensure_ascii=False, indent=2))
        print(json.dumps(keywords_por_termino(args.keyword), ensure_ascii=False, indent=2))
    if not args.asin and not args.keyword:
        print("Uso: python data/jungle_scout.py --keyword 'garlic press' [--asin B0...]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
