#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/exito.py — Asesor de probabilidad de exito de MV Amazon FBA IA.

Estima la probabilidad de exito de un producto dado el segmento, la demanda,
los competidores, las reseñas/calidad y el precio — con una formula de pesos
EXPLICITOS y auditables (misma filosofia que el score de nicho):

    demanda        0.30  ventas estimadas del nicho (o interes del motor propio)
    entrada        0.25  que tan defendido esta el nicho (mediana de reseñas de
                         los competidores: mas reseñas = mas dificil entrar)
    calidad_gap    0.20  rating promedio de la competencia: bajo = hueco para
                         diferenciarse con mejor producto
    precio         0.15  sweet spot FBA (USD 15-45: margen absoluto sin ser
                         territorio de marcas grandes)
    margen         0.10  el margen calculado por el pricing (si se pasa)

HONESTIDAD: es una ESTIMACION para ordenar candidatos, no una garantia. La
salida lo dice siempre, y ninguna probabilidad reemplaza la orden de prueba
(USD 1.000-2.000). Con ANTHROPIC_API_KEY, Claude agrega un analisis razonado;
sin clave, el desglose deterministico ya es utilizable.
"""
import argparse
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import config  # noqa: E402

PESOS = {"demanda": 0.30, "entrada": 0.25, "calidad_gap": 0.20,
         "precio": 0.15, "margen": 0.10}


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def evaluar(keyword, competencia=None, interes_kw=None, precio_objetivo=None,
            margen_pct=None):
    """
    keyword: nicho/producto evaluado.
    competencia: dict de data.mercado.resumen_competencia (opcional).
    interes_kw: interes 0-100 del motor propio (fallback de demanda).
    precio_objetivo: tu precio de venta previsto (USD).
    margen_pct: margen % del pricing (opcional).
    Devuelve {probabilidad, veredicto, factores{}, recomendaciones[], caveat}.
    """
    c = competencia or {}
    factores, faltantes = {}, []

    # 1) demanda
    if c.get("ventas_estim_total"):
        demanda = _clamp(c["ventas_estim_total"] / 3000.0)
        det_d = f"~{c['ventas_estim_total']:,} ventas/mes estimadas entre los lideres"
    elif interes_kw is not None:
        demanda = _clamp(interes_kw / 100.0) * 0.8   # proxy, techo 0.8 por honestidad
        det_d = f"proxy de interes del motor propio ({interes_kw}/100), sin ventas"
        faltantes.append("ventas estimadas (conecta Keepa)")
    else:
        demanda, det_d = 0.4, "sin dato de demanda: se asume neutral-bajo"
        faltantes.append("demanda (motor propio o Keepa)")
    factores["demanda"] = {"valor": round(demanda, 2), "detalle": det_d}

    # 2) barrera de entrada (reseñas de la competencia)
    if c.get("n_competidores"):
        med = c.get("resenas_mediana") or 0
        entrada = _clamp(1 - med / 1500.0)
        det_e = (f"mediana de {med:,} reseñas entre {c['n_competidores']} "
                 f"competidores" + (" — nicho muy defendido" if med > 1000 else
                                    " — entrada viable" if med < 300 else ""))
    else:
        entrada, det_e = 0.5, "sin datos de competidores: se asume neutral"
        faltantes.append("competidores (Productos estrella)")
    factores["entrada"] = {"valor": round(entrada, 2), "detalle": det_e}

    # 3) hueco de calidad
    if c.get("rating_promedio"):
        rp = c["rating_promedio"]
        gap = _clamp((4.6 - rp) / 1.2)
        det_c = (f"rating promedio {rp}/5 de la competencia" +
                 (" — hay espacio para un producto mejor" if rp < 4.3 else
                  " — competencia muy bien calificada, diferenciarse cuesta"))
    else:
        gap, det_c = 0.5, "sin ratings: se asume neutral"
        faltantes.append("calidad de competidores")
    factores["calidad_gap"] = {"valor": round(gap, 2), "detalle": det_c}

    # 4) precio (sweet spot FBA)
    p = precio_objetivo or c.get("precio_mediana")
    if p:
        if 15 <= p <= 45:
            fp, det_p = 1.0, f"USD {p:.2f} en el sweet spot FBA (15-45)"
        elif 10 <= p < 15 or 45 < p <= 70:
            fp, det_p = 0.6, f"USD {p:.2f} en el borde del sweet spot"
        else:
            fp, det_p = 0.25, (f"USD {p:.2f} fuera del sweet spot: margen absoluto "
                               "chico o territorio de marcas establecidas")
    else:
        fp, det_p = 0.5, "sin precio de referencia"
        faltantes.append("precio objetivo")
    factores["precio"] = {"valor": round(fp, 2), "detalle": det_p}

    # 5) margen
    if margen_pct is not None:
        fm = _clamp(margen_pct / 30.0)
        det_m = f"margen calculado {margen_pct:.1f}% (verde >= 25%)"
    else:
        fm, det_m = 0.5, "sin pricing cargado: se asume neutral"
        faltantes.append("margen (pestana Pricing)")
    factores["margen"] = {"valor": round(fm, 2), "detalle": det_m}

    prob = round(sum(PESOS[k] * factores[k]["valor"] for k in PESOS) * 100)
    if prob >= 65:
        veredicto, tono = "VERDE", "Candidato fuerte: avanzar a muestra y orden de prueba."
    elif prob >= 45:
        veredicto, tono = "AMARILLO", ("Marginal: solo avanzar con una diferenciacion "
                                       "clara (mejor producto, bundle, nicho mas fino).")
    else:
        veredicto, tono = "ROJO", "Desfavorable: no invertir capital aca."

    recomendaciones = []
    if factores["entrada"]["valor"] < 0.4:
        recomendaciones.append("Nicho defendido por reseñas: apunta a un sub-nicho "
                               "long-tail (del motor propio) en vez del head keyword.")
    if factores["calidad_gap"]["valor"] > 0.6:
        recomendaciones.append("La competencia tiene ratings flojos: lee sus reseñas "
                               "de 1-3 estrellas (link en Productos estrella) y arregla "
                               "ESO en tu producto; pegalas al Asistente IA para el resumen.")
    if factores["demanda"]["valor"] < 0.35:
        recomendaciones.append("Demanda debil o sin medir: valida con Keepa antes de "
                               "gastar en muestras.")
    if factores["margen"]["valor"] < 0.5 and margen_pct is not None:
        recomendaciones.append("El margen no llega al verde: renegocia costo/flete o "
                               "sube el precio objetivo antes de avanzar.")
    if not recomendaciones:
        recomendaciones.append("Pedi muestras a 3 proveedores verificados y valida "
                               "con la orden de prueba antes de escalar.")

    return {
        "ok": True, "keyword": keyword, "probabilidad": prob,
        "veredicto": veredicto, "comentario": tono,
        "factores": factores, "pesos": PESOS,
        "datos_faltantes": faltantes,
        "recomendaciones": recomendaciones,
        "caveat": ("Estimacion para ordenar candidatos, NO una garantia: el exito "
                   "real depende del proveedor, el listing y la ejecucion. Ninguna "
                   "probabilidad reemplaza la orden de prueba (USD 1.000-2.000)."),
    }


def narrativa(evaluacion, competencia=None):
    """Analisis razonado con Claude si hay clave; sin clave, resumen deterministico."""
    ev = evaluacion
    base = (f"{ev['veredicto']} ({ev['probabilidad']}/100): {ev['comentario']}\n"
            + "\n".join(f"- {k} ({PESOS[k]:.0%}): {v['detalle']}"
                        for k, v in ev["factores"].items()))
    if not config.ANTHROPIC_API_KEY:
        return {"texto": base, "modo": "offline"}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=config.MODEL_OPUS, max_tokens=900,
            system=("Sos el asesor de MV Amazon FBA IA. Analiza la evaluacion de "
                    "exito de un producto FBA y da un veredicto razonado en espanol "
                    "rioplatense: 3-5 parrafos cortos, concreto, sin humo. Respeta "
                    "el caveat: es una estimacion, no una garantia, y la orden de "
                    "prueba es obligatoria antes de escalar."),
            messages=[{"role": "user", "content":
                       "Evaluacion:\n" + json.dumps(ev, ensure_ascii=False) +
                       ("\nCompetencia:\n" + json.dumps(competencia, ensure_ascii=False)
                        if competencia else "")}])
        texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return {"texto": texto.strip() or base, "modo": "online"}
    except Exception:
        return {"texto": base, "modo": "offline"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Asesor de probabilidad de exito FBA.")
    ap.add_argument("--keyword", default="bamboo kitchen utensils")
    ap.add_argument("--precio", type=float, default=24.0)
    ap.add_argument("--margen", type=float, default=None)
    ap.add_argument("--demo", action="store_true",
                    help="Evalua contra los productos estrella [DEMO].")
    args = ap.parse_args(argv)
    comp = None
    if args.demo:
        from data import mercado
        r = mercado.productos_estrella(args.keyword, 10, 50, demo=True)
        comp = mercado.resumen_competencia(r["productos"])
    ev = evaluar(args.keyword, competencia=comp, precio_objetivo=args.precio,
                 margen_pct=args.margen)
    print(json.dumps(ev, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
