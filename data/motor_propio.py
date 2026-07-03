#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/motor_propio.py — Motor de keywords/nichos EMBEBIDO de MV Amazon FBA IA.

Reemplaza la parte de DESCUBRIMIENTO de Helium 10 / Jungle Scout sin pagar APIs:
usa el autocompletado publico de Amazon (completion.amazon.com), la misma senal
que esas herramientas explotan. Amazon ordena las sugerencias por volumen real
de busqueda, asi que el ranking ES dato real; lo que este motor NO da es el
NUMERO de busquedas/mes (eso vive en la base de datos paga de Helium 10, o se
aproxima con Keepa BSR->ventas).

HONESTIDAD DEL DATO (no negociable en este proyecto):
  - "interes" (0-100) es un PROXY: posicion en el autocompletado + amplitud de
    long-tail. NO es volumen de busqueda y se etiqueta como tal.
  - Sin red / bloqueado -> estado vacio explicado. Nunca inventa keywords.

Solo libreria estandar (urllib). Uso amable: pocas requests, con pausa.

Standalone:
    python data/motor_propio.py --seed "bamboo kitchen"
    python data/motor_propio.py --demo
Importable:
    from data.motor_propio import investigar, keywords_cerebro
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

_URL = "https://completion.amazon.com/api/2017/suggestions"
_MID = "ATVPDKIKX0DER"          # marketplace US
_UA = "Mozilla/5.0 (compatible; mv-amazon-fba-ia/1.0)"
_PAUSA_S = 0.35                  # pausa entre requests (uso amable)
_ABC = "abcdefghijklmnopqrstuvwxyz"


def sugerencias(prefix, timeout=10):
    """Sugerencias del autocompletado de Amazon US para `prefix` (lista de str)."""
    params = urllib.parse.urlencode({"mid": _MID, "alias": "aps",
                                     "prefix": prefix.strip()})
    req = urllib.request.Request(f"{_URL}?{params}", headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [s.get("value", "").strip().lower()
            for s in data.get("suggestions", [])
            if s.get("type") == "KEYWORD" and s.get("value")]


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def expandir(seed, profundidad=1, max_requests=30):
    """
    Expande `seed` con el patron estandar de descubrimiento:
      1) seed tal cual (ranking directo)
      2) seed + " a".."z" (long-tail alfabetico)
      3) si profundidad>1: re-expande las mejores sugerencias directas.
    Devuelve {keyword: {"mejor_rank", "apariciones", "origen"}} y el nro de
    requests hechas. Corta suave en max_requests.
    """
    hallazgos, hechos = {}, 0

    def registrar(kw, rank, origen):
        d = hallazgos.setdefault(kw, {"mejor_rank": rank, "apariciones": 0,
                                      "origen": origen})
        d["apariciones"] += 1
        if rank < d["mejor_rank"]:
            d["mejor_rank"] = rank

    def consultar(prefix, origen):
        nonlocal hechos
        if hechos >= max_requests:
            return []
        hechos += 1
        try:
            res = sugerencias(prefix)
        except Exception:
            return []
        for i, kw in enumerate(res, 1):
            registrar(kw, i, origen)
        time.sleep(_PAUSA_S)
        return res

    directas = consultar(seed, "directa")
    for letra in _ABC:
        consultar(f"{seed} {letra}", "alfabeto")
    if profundidad > 1:
        for kw in directas[:5]:
            if kw != seed.lower():
                consultar(kw, "nivel2")
    return hallazgos, hechos


def _score_interes(info, max_apariciones):
    """Proxy 0-100: rank en autocomplete (70%) + amplitud long-tail (30%)."""
    rank = _clamp(1 - (info["mejor_rank"] - 1) / 10.0)
    amplitud = _clamp(info["apariciones"] / max(1, max_apariciones))
    return round((0.70 * rank + 0.30 * amplitud) * 100)


def _nichos(seed, keywords):
    """Agrupa keywords por el modificador que sigue al seed -> nichos candidatos."""
    seed_l = seed.strip().lower()
    grupos = {}
    for k in keywords:
        kw = k["keyword"].lower()
        resto = kw[len(seed_l):].strip() if kw.startswith(seed_l) else ""
        etiqueta = resto.split()[0] if resto else "(seed exacto)"
        g = grupos.setdefault(etiqueta, {"nicho": f"{seed_l} {etiqueta}".strip(),
                                         "keywords": [], "interes_max": 0})
        g["keywords"].append(kw)
        g["interes_max"] = max(g["interes_max"], k["interes"])
    nichos = [g for e, g in grupos.items() if e != "(seed exacto)"]
    nichos.sort(key=lambda g: (g["interes_max"], len(g["keywords"])), reverse=True)
    return nichos


def demo_investigar(seed="bamboo kitchen"):
    """Resultado [DEMO] con la misma forma que investigar(), sin tocar la red."""
    kws = [
        {"keyword": f"[DEMO] {seed} utensils", "interes": 93, "mejor_rank": 1, "apariciones": 9},
        {"keyword": f"[DEMO] {seed} utensils set", "interes": 88, "mejor_rank": 1, "apariciones": 7},
        {"keyword": f"[DEMO] {seed} drawer organizer", "interes": 81, "mejor_rank": 2, "apariciones": 6},
        {"keyword": f"[DEMO] {seed} shelf", "interes": 64, "mejor_rank": 4, "apariciones": 4},
        {"keyword": f"[DEMO] {seed} towels", "interes": 52, "mejor_rank": 6, "apariciones": 3},
        {"keyword": f"[DEMO] {seed} cutting board", "interes": 76, "mejor_rank": 3, "apariciones": 5},
    ]
    return {"ok": True, "fuente": "DEMO", "seed": seed, "requests": 0,
            "keywords": kws, "nichos": _nichos(f"[demo] {seed}", kws),
            "mensaje": "Datos [DEMO] ilustrativos (no reales).",
            "nota_honesta": _NOTA}


_NOTA = ("'interes' es un proxy del autocompletado de Amazon (posicion + "
         "long-tail), NO volumen de busqueda. Para demanda numerica usa Keepa "
         "(BSR->ventas) o un CSV de Cerebro.")


def investigar(seed, profundidad=1, demo=False):
    """
    Investigacion completa de un seed. Devuelve:
      {ok, fuente, seed, keywords[{keyword,interes,mejor_rank,apariciones}],
       nichos[{nicho,keywords,interes_max}], requests, mensaje, nota_honesta}
    """
    seed = (seed or "").strip()
    if demo:
        return demo_investigar(seed or "bamboo kitchen")
    if len(seed) < 3:
        return {"ok": False, "fuente": "motor_propio", "seed": seed, "keywords": [],
                "nichos": [], "requests": 0, "nota_honesta": _NOTA,
                "mensaje": "Escribi un seed de al menos 3 letras."}
    hallazgos, hechos = expandir(seed, profundidad=profundidad)
    if not hallazgos:
        return {"ok": False, "fuente": "motor_propio", "seed": seed, "keywords": [],
                "nichos": [], "requests": hechos, "nota_honesta": _NOTA,
                "mensaje": ("Amazon no devolvio sugerencias (sin red, bloqueado o "
                            "seed sin resultados). El sistema no inventa keywords: "
                            "proba otro seed o usa el CSV de Cerebro.")}
    max_ap = max(i["apariciones"] for i in hallazgos.values())
    kws = [{"keyword": k, "interes": _score_interes(i, max_ap),
            "mejor_rank": i["mejor_rank"], "apariciones": i["apariciones"]}
           for k, i in hallazgos.items()]
    kws.sort(key=lambda x: (x["interes"], x["apariciones"]), reverse=True)
    return {"ok": True, "fuente": "motor_propio (autocompletado Amazon, gratis)",
            "seed": seed, "requests": hechos, "keywords": kws,
            "nichos": _nichos(seed, kws),
            "mensaje": f"{len(kws)} keywords reales en {hechos} consultas gratis.",
            "nota_honesta": _NOTA}


def keywords_cerebro(resultado, top=25):
    """
    Convierte el resultado del motor a objetos data.cerebro.Keyword para
    alimentar el generador de listing (ordena por 'interes' como proxy).
    """
    from data.cerebro import Keyword
    out = []
    for k in resultado.get("keywords", [])[:top]:
        kw = Keyword(keyword=k["keyword"], search_volume=float(k["interes"]),
                     match_type="O")
        kw.word_count = len(k["keyword"].split())
        out.append(kw)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Motor propio de keywords/nichos (autocompletado Amazon, gratis).")
    ap.add_argument("--seed", default="bamboo kitchen")
    ap.add_argument("--profundidad", type=int, default=1)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    r = investigar(args.seed, profundidad=args.profundidad, demo=args.demo)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r["ok"] else 1
    print("=" * 64)
    print(f"MOTOR PROPIO — '{r['seed']}'  ({r['fuente']})")
    print("=" * 64)
    print(r["mensaje"])
    for k in r["keywords"][:15]:
        print(f"  [{k['interes']:>3}] {k['keyword']:<48} rank={k['mejor_rank']} "
              f"apar={k['apariciones']}")
    print("\nNICHOS CANDIDATOS:")
    for n in r["nichos"][:8]:
        print(f"  [{n['interes_max']:>3}] {n['nicho']:<40} ({len(n['keywords'])} kw)")
    print("\nNOTA: " + r["nota_honesta"])
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
