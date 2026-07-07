#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/demanda_nativa.py — Estimador de demanda GRATIS (sin Keepa, sin Helium 10).

El problema: Keepa/Helium 10 cobran (~19-49 USD/mes) por su base de BSR->ventas.
Ninguna fuente gratis y legal da el numero absoluto "X unidades/mes" — ese dato
vive en bases propietarias o en la PA-API de Amazon (gratis pero requiere ser
Afiliado con ventas). Lo que SI se puede medir gratis y sin violar los terminos
de Amazon es la SEÑAL DE DEMANDA RELATIVA, a partir del autocompletado publico de
Amazon (completion.amazon.com) — la misma senal que esas herramientas explotan.

Que mide (y que NO):
  - MIDE: cuanta INTENCION DE COMPRA real existe para un producto, via la
    AMPLITUD de long-tail que Amazon autocompleta (mas variantes que la gente
    busca = mas demanda) y el RANKING del termino. Discrimina de verdad: un
    producto real da 25-40 variantes; uno sin demanda da 0.
  - NO MIDE: unidades/mes absolutas. Eso NO se puede sacar gratis y legal. Para
    el numero fino sigue haciendo falta Keepa (BSR->ventas) o la PA-API.

Uso honesto: ordenar y comparar nichos entre si (¿cual tiene mas demanda?),
que es exactamente la decision del Recomendador y del Mercado — sin pagar nada.

Reutiliza data/motor_propio.investigar() (con su pausa cortesia entre requests),
no duplica la logica de red.

Standalone:
    python data/demanda_nativa.py --keyword "yoga mat"
    python data/demanda_nativa.py --keyword "yoga mat" --marketplace ES --json
Importable:
    from data.demanda_nativa import estimar_demanda
"""
import argparse
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from data import motor_propio  # noqa: E402

_NOTA = ("Señal de demanda RELATIVA (amplitud de autocompletado de Amazon, gratis). "
         "NO son unidades/mes: sirve para comparar nichos entre sí, no como volumen "
         "absoluto. Para el número fino de ventas hace falta Keepa (BSR->ventas).")

# Umbrales de amplitud (long-tail unicos) -> etiqueta cualitativa. Calibrados con
# sondeos reales: producto fuerte ~30-40, medio ~15-25, debil <10, nulo 0.
_NIVELES = [(35, "MUY ALTA"), (22, "ALTA"), (12, "MEDIA"), (4, "BAJA"), (0, "NULA")]


def _nivel(amplitud):
    for umbral, etiqueta in _NIVELES:
        if amplitud >= umbral:
            return etiqueta
    return "NULA"


def _score(amplitud, top_interes, rank_seed):
    """Score 0-100 de demanda RELATIVA. Pesos explicitos y auditables:
       amplitud long-tail 60% (la señal mas fuerte de intencion diversa),
       interes del top 25% (que tan arriba rankea el mejor termino),
       presencia del seed exacto 15% (intencion directa por el termino base)."""
    amp = min(amplitud / 40.0, 1.0)                 # 40 variantes = techo
    inter = min((top_interes or 0) / 100.0, 1.0)
    directo = 1.0 if rank_seed else 0.0
    return round((0.60 * amp + 0.25 * inter + 0.15 * directo) * 100)


def estimar_demanda(keyword, marketplace="US", profundidad=1, demo=False):
    """
    Estima la demanda RELATIVA de `keyword` sin Keepa, via autocompletado.
    Devuelve {ok, keyword, marketplace, amplitud, demanda_score, nivel,
              top_interes, n_nichos, requests, fuente, nota_honesta}.
    """
    keyword = (keyword or "").strip()
    res = motor_propio.investigar(keyword, profundidad=profundidad, demo=demo,
                                  marketplace=marketplace)
    if not res.get("ok"):
        return {"ok": False, "keyword": keyword, "marketplace": marketplace,
                "amplitud": 0, "demanda_score": 0, "nivel": "NULA",
                "requests": res.get("requests", 0),
                "fuente": "motor_propio (autocompletado Amazon, gratis)",
                "mensaje": res.get("mensaje", "Sin sugerencias de Amazon."),
                "nota_honesta": _NOTA}

    kws = res["keywords"]
    amplitud = len(kws)
    top_interes = kws[0]["interes"] if kws else 0
    seed_l = keyword.lower()
    # ¿aparece el termino exacto (o casi) entre las sugerencias directas?
    rank_seed = any(k["keyword"].lower() == seed_l or k["keyword"].lower().startswith(seed_l)
                    for k in kws[:15])
    score = _score(amplitud, top_interes, rank_seed)
    return {
        "ok": True, "keyword": keyword, "marketplace": marketplace,
        "amplitud": amplitud, "demanda_score": score, "nivel": _nivel(amplitud),
        "top_interes": top_interes, "n_nichos": len(res.get("nichos", [])),
        "seed_directo": rank_seed, "requests": res.get("requests", 0),
        "fuente": "motor_propio (autocompletado Amazon, gratis)",
        "nota_honesta": _NOTA,
    }


def comparar(keywords, marketplace="US", demo=False):
    """Estima varios productos y los ordena por demanda_score (para nichos)."""
    out = [estimar_demanda(k, marketplace=marketplace, demo=demo) for k in keywords]
    out.sort(key=lambda d: d.get("demanda_score", 0), reverse=True)
    return {"ok": any(d["ok"] for d in out), "marketplace": marketplace,
            "ranking": out, "nota_honesta": _NOTA}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Estimador de demanda gratis (autocompletado Amazon, sin Keepa).")
    ap.add_argument("--keyword", required=True)
    ap.add_argument("--marketplace", default="US")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    r = estimar_demanda(args.keyword, marketplace=args.marketplace, demo=args.demo)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"DEMANDA (gratis) — '{r['keyword']}'  ({r['marketplace']})")
        print("=" * 60)
        if r["ok"]:
            print(f"Demanda relativa : {r['demanda_score']}/100  [{r['nivel']}]")
            print(f"Amplitud long-tail: {r['amplitud']} variantes reales de Amazon")
            print(f"Nichos candidatos : {r['n_nichos']}")
            print(f"Consultas gratis  : {r['requests']}")
        else:
            print("Sin datos:", r.get("mensaje"))
        print("-" * 60)
        print("NOTA:", r["nota_honesta"])
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
