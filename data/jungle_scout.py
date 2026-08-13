#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
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
from datetime import datetime, timedelta

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


def _get(ruta, params=None, timeout=25):
    p = {"marketplace": config.JUNGLE_SCOUT_MARKETPLACE, **(params or {})}
    url = f"{_BASE}/{ruta}?" + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers=_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _detalle_http(code):
    return "clave invalida o sin permiso" if code in (401, 403) else f"HTTP {code}"


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


def ventas_historicas_asin(asin, dias=30, timeout=30):
    """Ventas Y PRECIO diarios de un ASIN en los ultimos `dias` (Sales
    Estimates, con rango de fechas). Es lo que muestran las capturas de la API
    de Jungle Scout: seguir la venta diaria y los cambios de precio por ASIN.
    Devuelve {ok, asin, serie:[{fecha, unidades, precio}], resumen:{...}}."""
    asin = (asin or "").strip()
    if not _configurada():
        return {"ok": False, "asin": asin, "serie": [], "mensaje": estado()["mensaje"]}
    if not asin:
        return {"ok": False, "asin": asin, "serie": [], "mensaje": "Falta el ASIN."}
    dias = max(1, min(365, int(dias)))
    hoy = datetime.now()
    params = {"asin": asin,
              "start_date": (hoy - timedelta(days=dias)).strftime("%Y-%m-%d"),
              "end_date": hoy.strftime("%Y-%m-%d")}
    try:
        data = _get("sales_estimates", params, timeout=timeout)
    except urllib.error.HTTPError as e:
        return {"ok": False, "asin": asin, "serie": [],
                "mensaje": f"Jungle Scout rechazo la consulta ({_detalle_http(e.code)})."}
    except Exception as e:
        return {"ok": False, "asin": asin, "serie": [],
                "mensaje": f"Error de red Jungle Scout: {e}"}
    serie = []
    for item in (data.get("data") or []):
        a = item.get("attributes") or {}
        unidades = a.get("estimated_units_sold")
        if unidades is None:
            unidades = a.get("units_sold")
        precio = _num(a.get("estimated_price"))
        if precio is None:
            precio = _num(a.get("price")) or _num(a.get("buy_box_price"))
        serie.append({"fecha": a.get("date") or a.get("estimate_date") or "",
                      "unidades": int(unidades or 0),
                      "precio": round(precio, 2) if precio else None})
    if not serie:
        return {"ok": False, "asin": asin, "serie": [],
                "mensaje": "ASIN sin datos de ventas en Jungle Scout para ese rango."}
    precios = [p["precio"] for p in serie if p["precio"] is not None]
    total_u = sum(p["unidades"] for p in serie)
    resumen = {
        "unidades_total": total_u,
        "unidades_prom_dia": round(total_u / len(serie), 1),
        "precio_prom": round(sum(precios) / len(precios), 2) if precios else None,
        "precio_min": round(min(precios), 2) if precios else None,
        "precio_max": round(max(precios), 2) if precios else None,
    }
    return {"ok": True, "asin": asin, "dias": dias, "serie": serie,
            "resumen": resumen,
            "mensaje": f"{len(serie)} dias de ventas y precio reales via Jungle Scout."}


def ventas_asin(asin, timeout=25):
    """Compat: total de ventas estimadas del ASIN (ultimos 30 dias). Reusa
    ventas_historicas_asin, que pasa el rango de fechas que exige el endpoint."""
    r = ventas_historicas_asin(asin, dias=30, timeout=timeout)
    if not r["ok"]:
        return {"ok": False, "asin": r["asin"], "mensaje": r["mensaje"]}
    return {"ok": True, "asin": r["asin"],
            "ventas_estim": r["resumen"]["unidades_total"],
            "mensaje": "Ventas estimadas reales via Jungle Scout."}


def keywords_por_asin(asin, max_n=20, timeout=30):
    """Keywords por las que INDEXA un ASIN (Keywords by ASIN), con volumen
    mensual real. Sirve para leer un competidor: por que terminos aparece y con
    cuanta demanda. Devuelve {ok, asin, keywords:[{keyword, volumen, tendencia,
    competidores}], mensaje}."""
    asin = (asin or "").strip()
    if not _configurada():
        return {"ok": False, "asin": asin, "keywords": [], "mensaje": estado()["mensaje"]}
    if not asin:
        return {"ok": False, "asin": asin, "keywords": [], "mensaje": "Falta el ASIN."}
    cuerpo = {"data": {"type": "keywords_by_asin_query", "attributes": {
        "asin": [asin], "include_variants": True}}}
    try:
        data = _post(f"keywords/keywords_by_asin_query?page[size]={max(1, min(50, max_n))}",
                     cuerpo, timeout=timeout)
    except urllib.error.HTTPError as e:
        return {"ok": False, "asin": asin, "keywords": [],
                "mensaje": f"Jungle Scout rechazo la consulta ({_detalle_http(e.code)})."}
    except Exception as e:
        return {"ok": False, "asin": asin, "keywords": [],
                "mensaje": f"Error de red consultando Jungle Scout: {e}"}
    kws = []
    for item in (data.get("data") or [])[:max_n]:
        a = item.get("attributes") or {}
        vol = a.get("monthly_search_volume_exact") or a.get("estimated_exact_search_volume")
        kws.append({
            "keyword": a.get("name") or a.get("keyword") or "",
            "volumen": int(vol) if vol else 0,
            "tendencia": _num(a.get("monthly_trend")),
            "competidores": int(a.get("organic_product_count")
                                or a.get("competed_products") or 0),
        })
    if not kws:
        return {"ok": False, "asin": asin, "keywords": [],
                "mensaje": "Jungle Scout no devolvio keywords para ese ASIN."}
    kws.sort(key=lambda k: k["volumen"], reverse=True)
    return {"ok": True, "asin": asin, "keywords": kws,
            "mensaje": f"{len(kws)} keywords que indexa el ASIN via Jungle Scout."}


_MESES_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def volumen_historico(keyword, meses=12, timeout=30):
    """Volumen de busqueda semanal historico de una keyword (Historical Search
    Volume) + ESTACIONALIDAD derivada: que mes concentra mas demanda. Es el caso
    de uso de estacionalidad de las capturas de la API. Devuelve {ok, keyword,
    serie:[{fecha, volumen}], estacionalidad:{mejor_mes, ...}, mensaje}."""
    keyword = (keyword or "").strip()
    if not _configurada():
        return {"ok": False, "keyword": keyword, "serie": [], "mensaje": estado()["mensaje"]}
    if len(keyword) < 3:
        return {"ok": False, "keyword": keyword, "serie": [],
                "mensaje": "Escribi una keyword de al menos 3 letras."}
    meses = max(1, min(24, int(meses)))
    hoy = datetime.now()
    cuerpo = {"data": {"type": "historical_search_volume_query", "attributes": {
        "keyword": keyword,
        "start_date": (hoy - timedelta(days=meses * 30)).strftime("%Y-%m-%d"),
        "end_date": hoy.strftime("%Y-%m-%d")}}}
    try:
        data = _post("keywords/historical_search_volume_query", cuerpo, timeout=timeout)
    except urllib.error.HTTPError as e:
        return {"ok": False, "keyword": keyword, "serie": [],
                "mensaje": f"Jungle Scout rechazo la consulta ({_detalle_http(e.code)})."}
    except Exception as e:
        return {"ok": False, "keyword": keyword, "serie": [],
                "mensaje": f"Error de red consultando Jungle Scout: {e}"}
    serie, por_mes = [], {}
    for item in (data.get("data") or []):
        a = item.get("attributes") or {}
        fecha = a.get("estimate_start_date") or a.get("date") or ""
        vol = int(a.get("estimated_exact_search_volume") or 0)
        serie.append({"fecha": fecha, "volumen": vol})
        if len(fecha) >= 7:
            try:
                por_mes[int(fecha[5:7])] = por_mes.get(int(fecha[5:7]), 0) + vol
            except ValueError:
                pass
    if not serie:
        return {"ok": False, "keyword": keyword, "serie": [],
                "mensaje": "Jungle Scout no devolvio historico para esa keyword."}
    total = sum(p["volumen"] for p in serie)
    estacionalidad = None
    if por_mes:
        mejor = max(por_mes, key=por_mes.get)
        estacionalidad = {
            "mejor_mes": _MESES_ES[mejor], "mejor_mes_num": mejor,
            "volumen_mejor_mes": por_mes[mejor],
            "volumen_total": total,
            "volumen_prom_semana": round(total / len(serie)),
        }
    return {"ok": True, "keyword": keyword, "serie": serie,
            "estacionalidad": estacionalidad,
            "mensaje": f"{len(serie)} semanas de volumen historico via Jungle Scout."}


def share_of_voice(keyword, timeout=25):
    """Share of Voice de una keyword: que marcas dominan la primera pagina y con
    que porcentaje (organico/pago/combinado), mas el PPC bid y el volumen 30d.
    Devuelve {ok, keyword, marcas:[{marca, sov_pct}], ppc_bid, volumen_30d, mensaje}."""
    keyword = (keyword or "").strip()
    if not _configurada():
        return {"ok": False, "keyword": keyword, "marcas": [], "mensaje": estado()["mensaje"]}
    if len(keyword) < 3:
        return {"ok": False, "keyword": keyword, "marcas": [],
                "mensaje": "Escribi una keyword de al menos 3 letras."}
    cuerpo = {"data": {"type": "share_of_voice_query",
                       "attributes": {"keyword": keyword}}}
    try:
        data = _post("keywords/share_of_voice_query", cuerpo, timeout=timeout)
    except urllib.error.HTTPError as e:
        return {"ok": False, "keyword": keyword, "marcas": [],
                "mensaje": f"Jungle Scout rechazo la consulta ({_detalle_http(e.code)})."}
    except Exception as e:
        return {"ok": False, "keyword": keyword, "marcas": [],
                "mensaje": f"Error de red consultando Jungle Scout: {e}"}
    a = ((data.get("data") or {}).get("attributes")
         if isinstance(data.get("data"), dict) else {}) or {}
    marcas = []
    for b in (a.get("brands") or a.get("brand_share_of_voice") or [])[:15]:
        if not isinstance(b, dict):
            continue
        sov = _num(b.get("combined_share_of_voice") or b.get("share_of_voice")
                   or b.get("combined_product_share_of_voice"))
        marcas.append({"marca": b.get("brand") or b.get("name") or "s/marca",
                       "sov_pct": round(sov, 1) if sov is not None else None})
    return {"ok": True, "keyword": keyword, "marcas": marcas,
            "ppc_bid": _num(a.get("ppc_bid_exact") or a.get("ppc_bid")),
            "volumen_30d": int(a.get("estimated_30_day_search_volume")
                               or a.get("monthly_search_volume_exact") or 0),
            "mensaje": (f"Share of voice de {len(marcas)} marcas via Jungle Scout."
                        if marcas else "Jungle Scout no devolvio share of voice "
                        "para esa keyword.")}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Consulta Jungle Scout (productos + keywords + ventas).")
    ap.add_argument("--keyword", help="Keyword para productos + volumen.")
    ap.add_argument("--asin", help="ASIN para estimacion de ventas.")
    ap.add_argument("--min", type=float, default=10.0)
    ap.add_argument("--max", type=float, default=50.0)
    args = ap.parse_args(argv)
    print("Estado:", json.dumps(estado(), ensure_ascii=False))
    if args.asin:
        print(json.dumps(ventas_historicas_asin(args.asin), ensure_ascii=False, indent=2))
        print(json.dumps(keywords_por_asin(args.asin), ensure_ascii=False, indent=2))
    if args.keyword:
        print(json.dumps(buscar_productos(args.keyword, args.min, args.max),
                         ensure_ascii=False, indent=2))
        print(json.dumps(keywords_por_termino(args.keyword), ensure_ascii=False, indent=2))
        print(json.dumps(volumen_historico(args.keyword), ensure_ascii=False, indent=2))
        print(json.dumps(share_of_voice(args.keyword), ensure_ascii=False, indent=2))
    if not args.asin and not args.keyword:
        print("Uso: python data/jungle_scout.py --keyword 'garlic press' [--asin B0...]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
