#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/recomendador.py — Descubrimiento PROACTIVO de nichos (FBA).

Todos los demas modulos son REACTIVOS: el usuario ya tiene que traer una
keyword (Investigacion), un rango de precio (Mercado) o un producto cargado
(Pricing/Exito) para que el sistema responda. Este modulo da vuelta el flujo:
sin ninguna keyword, escanea una lista de categorias FBA probadas y devuelve
una lista rankeada de "oportunidades" — nichos con buen precio, demanda y
poca competencia — usando SOLO datos propios:

  1) Motor propio (data/motor_propio.py): autocompletado real de Amazon,
     gratis, sin Helium 10. Da el ranking de popularidad real (no el volumen
     numerico), igual que en Investigacion.
  2) Si hay Jungle Scout o Keepa conectados (opcional, no obligatorio, ver
     data/mercado.py que decide cual usar): cruza cada candidato con
     productos_estrella para afinar con precio real, ventas estimadas y
     competencia — pero el escaneo funciona igual de bien sin ninguna clave,
     solo que con menos precision.
  3) Rankea con la MISMA formula de agents/exito.py (probabilidad de exito),
     no una formula nueva: demanda + baja competencia + hueco de calidad +
     precio sweet-spot + margen.
  4) Con ANTHROPIC_API_KEY conectada, Claude sintetiza cual es el nicho mas
     rentable del top rankeado (narrativa_top) — sin clave, un resumen
     deterministico del top 1 (nunca deja el campo vacio).

Dos pasadas para no hacer 200+ requests por click:
  Pasada 1 (amplia, rapida): 1 request de autocompletado por seed -> hasta
  10 sugerencias rankeadas por Amazon mismo. Barato: ~len(seeds) requests.
  Pasada 2 (angosta, precisa): de esas, solo el shortlist (12 por defecto)
  se evalua con agents/exito.py (+ Jungle Scout/Keepa si esta conectado).

HONESTIDAD: "potencial" ordena candidatos con datos parciales, no promete
ganancias. Ninguna oportunidad reemplaza pedir muestra y validar con una
orden de prueba chica antes de escalar (mismo caveat que agents/exito.py).
La narrativa de Claude tampoco es una garantia: hereda el mismo caveat.

Standalone:
    python agents/recomendador.py --min 15 --max 40 --demo
    python agents/recomendador.py --min 15 --max 40 --marketplace US
Importable:
    from agents.recomendador import escanear_oportunidades
"""
import argparse
import json
import os
import sys
import time

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import config                              # noqa: E402
from data import motor_propio              # noqa: E402
from data import mercado                   # noqa: E402
from agents import exito                   # noqa: E402

# Seeds de arranque: categorias FBA livianas, no fragiles, sin marcas
# dominantes — el punto de partida clasico para buscar nichos, no el
# resultado final (el motor propio los expande a keywords reales).
SEEDS = {
    "en": ["kitchen utensils", "yoga mat", "dog toys", "baby bottle",
           "desk organizer", "garden tools", "phone stand", "makeup brush",
           "water bottle", "pet bed", "resistance bands", "kitchen storage",
           "bathroom organizer", "car accessories", "travel bag",
           "hair accessories", "office supplies", "cleaning brush",
           "camping gear", "baby carrier"],
    "es": ["utensilios de cocina", "esterilla de yoga", "juguetes para perro",
           "biberon bebe", "organizador de escritorio", "herramientas de jardin",
           "soporte de celular", "brocha de maquillaje", "botella de agua",
           "cama para mascota", "bandas de resistencia", "organizador de cocina",
           "organizador de baño", "accesorios para auto", "bolso de viaje",
           "accesorios para el cabello", "utiles de oficina",
           "cepillo de limpieza", "equipo de camping", "portabebe"],
    "pt": ["utensilios de cozinha", "tapete de yoga", "brinquedos para cachorro",
           "mamadeira bebe", "organizador de mesa", "ferramentas de jardim",
           "suporte de celular", "pincel de maquiagem", "garrafa de agua",
           "cama para pet", "faixas de resistencia", "organizador de cozinha",
           "organizador de banheiro", "acessorios para carro", "bolsa de viagem",
           "acessorios de cabelo", "material de escritorio", "escova de limpeza",
           "equipamento de camping", "canguru para bebe"],
}

_NOTA = ("'potencial' ordena candidatos con los datos disponibles (motor propio "
         "gratis, y Keepa si esta conectado) — NO es una garantia de ganancia. "
         "Ninguna oportunidad reemplaza pedir muestra y validar con una orden de "
         "prueba chica (USD 1.000-2.000) antes de escalar.")


def _idioma_de(marketplace):
    return motor_propio._mkt(marketplace).get("idioma", "en")


def _pasada_amplia(seeds, marketplace, demo):
    """Autocompletado real por seed -> candidatos {keyword, interes_proxy, seed}."""
    candidatos, vistos = [], set()
    if demo:
        for seed in seeds:
            r = motor_propio.demo_investigar(seed)
            for k in r["keywords"][:4]:
                kw = k["keyword"].lower()
                if kw in vistos:
                    continue
                vistos.add(kw)
                candidatos.append({"keyword": k["keyword"],
                                   "interes_proxy": k["interes"], "seed": seed})
        return candidatos, 0

    hechos = 0
    for seed in seeds:
        try:
            sugs = motor_propio.sugerencias(seed, marketplace=marketplace)
        except Exception:
            sugs = []
        hechos += 1
        time.sleep(motor_propio._PAUSA_S)
        n = len(sugs) or 1
        for rank, kw in enumerate(sugs[:10], 1):
            kwl = kw.lower()
            if kwl in vistos:
                continue
            vistos.add(kwl)
            interes = round(100 * (1 - (rank - 1) / max(1, n)))
            candidatos.append({"keyword": kw, "interes_proxy": interes, "seed": seed})
    return candidatos, hechos


def _pasada_angosta(shortlist, precio_min, precio_max, demo, usar_datos_reales):
    """Shortlist -> evaluacion real (agents/exito.py) + Jungle Scout/Keepa opcional
    (data/mercado.py decide sola cual de las dos usar, si hay mas de una clave)."""
    precio_obj = (precio_min + precio_max) / 2.0
    oportunidades = []
    for c in shortlist:
        comp, fuente_precio = None, "sin datos de productos"
        if demo:
            prods = mercado.demo_estrellas(c["keyword"], precio_min, precio_max)
            if prods:
                comp = mercado.resumen_competencia(prods)
                fuente_precio = "DEMO"
        elif usar_datos_reales:
            try:
                r = mercado.productos_estrella(c["keyword"], precio_min, precio_max, max_n=8)
                if r.get("ok"):
                    comp = mercado.resumen_competencia(r["productos"])
                    fuente_precio = r.get("fuente") or "datos reales"
            except Exception:
                comp = None

        ev = exito.evaluar(c["keyword"], competencia=(comp if comp and comp.get("ok") else None),
                           interes_kw=c["interes_proxy"], precio_objetivo=precio_obj)
        oportunidades.append({
            "nicho": c["keyword"], "seed_origen": c["seed"],
            "interes_proxy": c["interes_proxy"],
            "potencial": ev["probabilidad"], "veredicto": ev["veredicto"],
            "comentario": ev["comentario"],
            "n_competidores": (comp or {}).get("n_competidores"),
            "ventas_estim_total": (comp or {}).get("ventas_estim_total"),
            "precio_mediana": (comp or {}).get("precio_mediana"),
            "fuente_precio": fuente_precio,
            "recomendaciones": ev["recomendaciones"],
            "datos_faltantes": ev["datos_faltantes"],
        })
    return oportunidades


def escanear_oportunidades(precio_min=10.0, precio_max=50.0, marketplace="US",
                           seeds=None, max_seeds=8, shortlist=12, top_n=10,
                           usar_keepa=True, demo=False):
    """
    Escaneo proactivo de oportunidades: sin keyword de entrada. Devuelve
    {ok, fuente, marketplace, precio_min, precio_max, seeds_usadas,
     n_candidatos_evaluados, oportunidades[], mensaje, nota_honesta}.
    """
    if precio_min <= 0 or precio_max <= 0 or precio_max < precio_min:
        return {"ok": False, "oportunidades": [], "seeds_usadas": [],
                "mensaje": "El rango de precio no es valido (minimo <= maximo, ambos > 0).",
                "nota_honesta": _NOTA}

    idioma = _idioma_de(marketplace)
    seeds_usadas = list(seeds) if seeds else SEEDS.get(idioma, SEEDS["en"])
    seeds_usadas = seeds_usadas[:max(1, max_seeds)]

    candidatos, hechos = _pasada_amplia(seeds_usadas, marketplace, demo)
    if not candidatos:
        return {"ok": False, "fuente": "motor_propio", "marketplace": marketplace,
                "precio_min": precio_min, "precio_max": precio_max,
                "seeds_usadas": seeds_usadas, "oportunidades": [],
                "mensaje": ("Amazon no devolvio sugerencias para ninguna de las "
                            "categorias de arranque (sin red o bloqueado). El "
                            "sistema no inventa oportunidades: reintenta en unos "
                            "minutos."),
                "nota_honesta": _NOTA}

    candidatos.sort(key=lambda c: c["interes_proxy"], reverse=True)
    # usar_keepa: nombre historico del parametro publico (no se renombra para
    # no romper la firma), pero ahora gatea CUALQUIER fuente real conectada
    # (Jungle Scout o Keepa) -- data/mercado.py decide sola cual usar.
    usar_datos_reales = bool(usar_keepa and not demo and (
        config.KEEPA_API_KEY or (config.JUNGLE_SCOUT_API_KEY and config.JUNGLE_SCOUT_KEY_NAME)))
    oportunidades = _pasada_angosta(candidatos[:max(1, shortlist)], precio_min,
                                    precio_max, demo, usar_datos_reales)
    oportunidades.sort(key=lambda o: o["potencial"], reverse=True)
    top = oportunidades[:max(1, top_n)]

    fuente = ("DEMO" if demo else
             "motor propio + datos reales (Jungle Scout/Keepa)" if usar_datos_reales else
             "motor propio (autocompletado Amazon, gratis, sin Helium 10)")
    narrativa_ia = narrativa_top(top, marketplace, precio_min, precio_max) if top else None
    return {
        "ok": True, "fuente": fuente, "marketplace": marketplace,
        "precio_min": precio_min, "precio_max": precio_max,
        "seeds_usadas": seeds_usadas, "requests": hechos,
        "n_candidatos_evaluados": len(oportunidades),
        "oportunidades": top,
        "mensaje": f"{len(top)} oportunidades rankeadas de {len(oportunidades)} candidatos evaluados.",
        "nota_honesta": _NOTA,
        "narrativa_ia": narrativa_ia,
    }


def narrativa_top(oportunidades, marketplace, precio_min, precio_max):
    """Con ANTHROPIC_API_KEY, Claude elige el nicho mas rentable del top
    rankeado y explica por que (mismo molde que agents/exito.py::narrativa).
    Sin clave (o si Claude falla), resumen deterministico del top 1 -- nunca
    lanza, nunca deja el campo vacio."""
    top1 = oportunidades[0]
    base = (f"Mejor candidato segun el ranking: '{top1['nicho']}' "
            f"({top1['potencial']}/100, {top1['veredicto']}). {top1['comentario']}")
    if not config.ANTHROPIC_API_KEY:
        return {"texto": base, "modo": "offline"}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=config.MODEL_OPUS, max_tokens=900,
            system=("Sos el asesor de MV FBA IA. Te paso una lista de nichos ya "
                    "rankeados (con potencial 0-100, veredicto, competidores, "
                    "ventas estimadas y precio mediana cuando hay datos reales de "
                    "Jungle Scout/Keepa, o solo un proxy de interes si no). Elegi "
                    "CUAL es el nicho mas rentable para entrar y explica por que "
                    "en 3-5 parrafos cortos, en espanol rioplatense, tono "
                    "profesional pero calido y cercano. Nombra 1-2 runner-ups si "
                    "hay candidatos cerca en potencial pero con algun matiz "
                    "distinto (mas defendido, precio mas ajustado, etc). Aclara "
                    "siempre que es una estimacion para ordenar candidatos, NO una "
                    "garantia, y que la orden de prueba (USD 1.000-2.000) sigue "
                    "siendo obligatoria antes de escalar."),
            messages=[{"role": "user", "content":
                       f"Rango de precio: USD {precio_min:.0f}-{precio_max:.0f} | "
                       f"Marketplace: {marketplace}\n\nNichos rankeados:\n" +
                       json.dumps(oportunidades, ensure_ascii=False)}])
        texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return {"texto": texto.strip() or base, "modo": "online"}
    except Exception:
        return {"texto": base, "modo": "offline"}


def _texto(r):
    out = ["=" * 66, "RECOMENDADOR — oportunidades detectadas (proactivo)", "=" * 66]
    if not r["ok"]:
        out.append("Sin resultados: " + r["mensaje"])
        out.append("=" * 66)
        return "\n".join(out)
    out.append(f"Fuente: {r['fuente']}  |  Precio USD {r['precio_min']:.0f}-{r['precio_max']:.0f}")
    out.append(f"Seeds escaneadas: {', '.join(r['seeds_usadas'])}")
    out.append("-" * 66)
    for i, o in enumerate(r["oportunidades"], 1):
        out.append(f"{i:>2}. [{o['potencial']:>3}/100 {o['veredicto']:<9}] {o['nicho']}")
        detalle = f"     interes(proxy)={o['interes_proxy']}"
        if o["n_competidores"] is not None:
            detalle += f"  competidores={o['n_competidores']}  precio_mediana=USD {o['precio_mediana']}"
        out.append(detalle)
        out.append(f"     {o['comentario']}")
    out.append("-" * 66)
    if r.get("narrativa_ia"):
        out.append(f"RECOMENDACION DE IA ({r['narrativa_ia']['modo']}):")
        out.append(r["narrativa_ia"]["texto"])
        out.append("-" * 66)
    out.append("NOTA: " + r["nota_honesta"])
    out.append("=" * 66)
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Recomendador proactivo de nichos FBA (con Jungle Scout/Keepa opcional).")
    ap.add_argument("--min", type=float, default=15.0, dest="precio_min")
    ap.add_argument("--max", type=float, default=45.0, dest="precio_max")
    ap.add_argument("--marketplace", default="US")
    ap.add_argument("--seeds", help="Lista separada por comas (si no, usa las de arranque).")
    ap.add_argument("--max-seeds", type=int, default=8)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--sin-keepa", action="store_true", help="No cruzar con Keepa aunque haya clave.")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    seeds = [s.strip() for s in args.seeds.split(",")] if args.seeds else None
    r = escanear_oportunidades(precio_min=args.precio_min, precio_max=args.precio_max,
                               marketplace=args.marketplace, seeds=seeds,
                               max_seeds=args.max_seeds, top_n=args.top,
                               usar_keepa=not args.sin_keepa, demo=args.demo)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.json else _texto(r))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BrokenPipeError, KeyboardInterrupt):
        sys.exit(130)
