#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/keepa.py — Fuente programatica de mercado (Keepa API) para el sistema FBA.

Keepa SI tiene API publica (de pago, ~19 EUR/mes) y da: precio actual, BSR (sales rank)
e historico. Es la alternativa real a Helium 10 (que no expone API en Platinum).

NO inventa datos: sin KEEPA_API_KEY devuelve estado vacio explicado.
Solo libreria estandar (urllib). domain=1 => amazon.com (US).

LIMITE HONESTO: Keepa da BSR, no ventas. La conversion BSR->ventas/mes es una
ESTIMACION gruesa por curva de categoria (documentada abajo), no un dato exacto.
Sirve para ordenar candidatos y alimentar el precio de competencia, no como verdad fina.

Uso:
    python data/keepa.py --asin B08XXXXX
Importable:
    from data.keepa import producto, estado
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

_BASE = "https://api.keepa.com/product"

# Curva BSR -> ventas/mes (aprox, categoria Home & Kitchen US). GRUESA y editable.
# Pares (bsr, ventas_mensuales) interpolados en escala log.
_CURVA = [(100, 9000), (500, 3000), (1000, 1800), (5000, 500),
          (10000, 230), (50000, 45), (100000, 18), (500000, 3)]


def _estim_ventas(bsr):
    if not bsr or bsr <= 0:
        return 0
    import math
    if bsr <= _CURVA[0][0]:
        return _CURVA[0][1]
    if bsr >= _CURVA[-1][0]:
        return _CURVA[-1][1]
    for (b1, v1), (b2, v2) in zip(_CURVA, _CURVA[1:]):
        if b1 <= bsr <= b2:
            t = (math.log10(bsr) - math.log10(b1)) / (math.log10(b2) - math.log10(b1))
            return int(round(v1 * (v2 / v1) ** t))
    return 0


def tokens_left(timeout: int = 20) -> dict:
    """Valida la clave SIN gastar tokens de producto (endpoint /token)."""
    if not config.KEEPA_API_KEY:
        return {"ok": False, "mensaje": "Falta KEEPA_API_KEY."}
    url = ("https://api.keepa.com/token?" +
           urllib.parse.urlencode({"key": config.KEEPA_API_KEY, "domain": config.KEEPA_DOMAIN}))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "fba-system/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (400, 401, 403):
            return {"ok": False, "mensaje": "Clave invalida o sin suscripcion activa "
                                            "(HTTP %d)." % e.code}
        return {"ok": False, "mensaje": f"HTTP {e.code} de Keepa."}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error de red Keepa: {e}"}
    return {"ok": True, "tokens_left": data.get("tokensLeft"),
            "refill_in_min": round((data.get("refillIn", 0) or 0) / 60000.0, 1),
            "mensaje": "Clave Keepa valida."}


def estado():
    if not config.KEEPA_API_KEY:
        return {"ok": False, "mensaje": ("Falta KEEPA_API_KEY en .env. Keepa es la fuente "
                                         "programatica (precio + BSR). Sin clave no consulta.")}
    return {"ok": True, "mensaje": "Keepa conectado.", "domain": config.KEEPA_DOMAIN}


def producto(asin: str, timeout: int = 25) -> dict:
    """Devuelve {ok, asin, titulo, precio, bsr, ventas_estim, fuente} o estado vacio."""
    if not config.KEEPA_API_KEY:
        return {"ok": False, "asin": asin, "mensaje": estado()["mensaje"]}
    params = urllib.parse.urlencode({"key": config.KEEPA_API_KEY,
                                     "domain": config.KEEPA_DOMAIN,
                                     "asin": asin, "stats": 90})
    url = f"{_BASE}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "fba-system/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "asin": asin, "mensaje": f"Error Keepa: {e}"}
    prods = data.get("products") or []
    if not prods:
        return {"ok": False, "asin": asin, "mensaje": "ASIN sin datos en Keepa."}
    p = prods[0]
    titulo = p.get("title") or ""
    stats = p.get("stats") or {}
    cur = stats.get("current") or []
    # indices Keepa csv: 0=AMAZON,1=NEW,3=SALES rank. Precio en centavos (-1 = sin dato).
    precio = None
    for idx in (1, 0):  # NEW, luego AMAZON
        if len(cur) > idx and cur[idx] is not None and cur[idx] >= 0:
            precio = round(cur[idx] / 100.0, 2)
            break
    bsr = cur[3] if len(cur) > 3 and cur[3] and cur[3] > 0 else None
    return {"ok": True, "asin": asin, "titulo": titulo, "precio": precio,
            "bsr": bsr, "ventas_estim": _estim_ventas(bsr), "fuente": "Keepa"}


def demanda_mensual(asins) -> dict:
    """Suma ventas estimadas de una lista de ASIN (demanda agregada del nicho)."""
    total, detalle = 0, []
    for a in asins:
        pr = producto(a)
        if pr.get("ok"):
            total += pr.get("ventas_estim", 0)
            detalle.append(pr)
    return {"ok": bool(detalle), "demanda_mensual": total, "detalle": detalle}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Consulta Keepa (precio + BSR) de un ASIN.")
    ap.add_argument("--asin", required=False)
    args = ap.parse_args(argv)
    if not args.asin:
        print("Estado:", estado())
        print("Uso: python data/keepa.py --asin B08XXXXX")
        return 0
    print(json.dumps(producto(args.asin), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
