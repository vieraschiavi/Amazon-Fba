#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/asistente.py — Asistente IA (Claude) de MV Amazon FBA IA.

Responde preguntas del negocio, las metricas y la estrategia FBA. Se apoya en los
datos REALES del sistema (KPIs de ventas, portafolio, config) como contexto, y en
el glosario para el modo offline. No inventa numeros: el contexto se arma de la DB.

Dos caminos (mismo patron honesto que agents/listing.py):
  - Con ANTHROPIC_API_KEY + SDK anthropic -> responde Claude (modelo config.MODEL_OPUS).
  - Sin clave / sin SDK / si falla -> modo OFFLINE: responde desde el glosario y
    guia al usuario a conectar la clave en la pestana Config. Nunca rompe el panel.
"""
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import config                        # noqa: E402
from agents import glosario          # noqa: E402

_SYSTEM = (
    "Sos el asistente de MV Amazon FBA IA, un cockpit para operar un negocio "
    "Amazon FBA (mercado US). Ayudas al dueno a entender sus metricas, su "
    "portafolio y su estrategia. Respondes con un tono PROFESIONAL PERO AMABLE y "
    "cercano: claro, concreto y sin relleno, pero calido y respetuoso, como un asesor "
    "de confianza. En espanol rioplatense.\n\n"
    "PRINCIPIOS HONESTOS DEL SISTEMA (respetalos siempre):\n"
    "- El techo de demanda es obligatorio: mas capital no vende mas si el nicho no "
    "lo absorbe. El sueldo se estabiliza en meseta (~techo x neto), no crece infinito.\n"
    "- El score mide ganabilidad, no margen. Nada reemplaza una orden de prueba "
    "(USD 1.000-2.000) antes de escalar.\n"
    "- El bot de atencion NO auto-responde texto libre (lo prohibe Amazon): solo FAQs.\n"
    "- Helium 10 no tiene API en Platinum: keywords por CSV de Cerebro. Keepa da "
    "precio + BSR programatico.\n\n"
    "REGLAS: Usa los DATOS DEL NEGOCIO que se te pasan como contexto para responder "
    "con numeros reales; si un dato no esta, decilo en vez de inventarlo. No des "
    "consejo financiero garantizado: el retorno FBA es variable y no esta asegurado."
)


def _contexto_negocio():
    """Arma un contexto compacto con datos REALES del sistema (sin claves)."""
    lineas = []
    try:
        from agents import analytics
        k = analytics.kpis()
        lineas.append(
            f"Ventas acumuladas: facturacion USD {k['facturacion']:.0f}, "
            f"neto USD {k['neto']:.0f}, margen global {k['margen_global_pct']}%, "
            f"{k['ordenes']} ordenes / {k['unidades']} unidades.")
        if k.get("por_producto"):
            top = k["por_producto"][0]
            lineas.append(f"Producto top por ingreso: {top['k']} "
                          f"(USD {top['ingreso']:.0f}).")
    except Exception:
        pass
    try:
        from agents import productos
        rp = productos.resumen_portafolio()
        if rp.get("n_productos"):
            sem = rp["semaforos"]
            lineas.append(
                f"Portafolio: {rp['n_productos']} productos activos "
                f"({sem['verde']} verde / {sem['amarillo']} amarillo / {sem['rojo']} rojo), "
                f"sueldo meseta proyectado USD {rp['sueldo_meseta_proyectado']:.0f}/mes, "
                f"capital en pipeline USD {rp['capital_pipeline_total']:.0f}.")
        else:
            lineas.append("Portafolio: vacio (aun no se cargaron productos).")
    except Exception:
        pass
    try:
        cfg = config.estado_config()
        lineas.append(f"Conexiones: LLM {cfg['llm']}, Keepa {cfg['keepa']}, "
                      f"email {cfg['email']}, marketplace {cfg['marketplace']}.")
    except Exception:
        pass
    return "\n".join(lineas) if lineas else "Sin datos de negocio cargados todavia."


def estado():
    """Estado del asistente para el panel: online (Claude) u offline (glosario)."""
    if not config.ANTHROPIC_API_KEY:
        return {"ok": False, "modo": "offline",
                "mensaje": "Sin ANTHROPIC_API_KEY: respondo desde el glosario. "
                           "Conecta tu clave en Config para respuestas completas."}
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return {"ok": False, "modo": "offline",
                "mensaje": "Falta el paquete 'anthropic' (pip install anthropic). "
                           "Mientras tanto respondo desde el glosario."}
    return {"ok": True, "modo": "online",
            "mensaje": f"Asistente Claude conectado ({config.MODEL_OPUS})."}


_STOP = {"que", "es", "el", "la", "los", "las", "un", "una", "de", "del", "mi", "mis",
         "por", "para", "como", "cual", "y", "o", "en", "con", "se", "su", "al", "a"}


def _responder_offline(pregunta):
    """Fallback sin clave: busca en el glosario (por palabras) y guia al usuario."""
    hits = glosario.buscar(pregunta)
    if not hits:
        # matching por palabra: util para preguntas en lenguaje natural
        vistos, palabras = set(), []
        for w in "".join(c if c.isalnum() else " " for c in pregunta.lower()).split():
            if len(w) > 2 and w not in _STOP:
                palabras.append(w)
        for w in palabras:
            for t, d, c in glosario.buscar(w):
                if t not in vistos:
                    vistos.add(t)
                    hits.append((t, d, c))
    if hits:
        cuerpo = "\n\n".join(f"**{t}** — {d}" for t, d, _ in hits[:4])
        return ("Modo offline (sin clave de Claude). Segun el glosario:\n\n" + cuerpo +
                "\n\nPara analisis personalizado de TUS numeros, conecta tu "
                "ANTHROPIC_API_KEY en la pestana Config.")
    return ("Modo offline (sin clave de Claude). No encontre ese termino en el "
            "glosario. Conecta tu ANTHROPIC_API_KEY en la pestana Config y te "
            "respondo con el analisis de tu negocio; mientras tanto, mira la "
            "pestana Ayuda para los conceptos base.")


def responder(pregunta, historial=None, max_tokens=1400):
    """
    Responde `pregunta`. `historial`: lista de {"role","content"} previos (opcional).
    Devuelve {"texto", "modo"}. Nunca lanza: si Claude falla, cae a offline.
    """
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return {"texto": "Escribime una pregunta sobre tu negocio FBA.", "modo": "offline"}

    if not config.ANTHROPIC_API_KEY:
        return {"texto": _responder_offline(pregunta), "modo": "offline"}
    try:
        import anthropic
    except ImportError:
        return {"texto": _responder_offline(pregunta), "modo": "offline"}

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        system = (_SYSTEM
                  + "\n\n=== DATOS DEL NEGOCIO (reales, del sistema) ===\n"
                  + _contexto_negocio()
                  + "\n\n=== GLOSARIO DE REFERENCIA ===\n"
                  + glosario.contexto_para_ia())
        mensajes = []
        for m in (historial or [])[-8:]:
            rol = m.get("role")
            if rol in ("user", "assistant") and m.get("content"):
                mensajes.append({"role": rol, "content": m["content"]})
        mensajes.append({"role": "user", "content": pregunta})
        resp = client.messages.create(
            model=config.MODEL_OPUS, max_tokens=max_tokens,
            system=system, messages=mensajes)
        texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return {"texto": texto.strip() or _responder_offline(pregunta), "modo": "online"}
    except anthropic.AuthenticationError:
        return {"texto": "Tu ANTHROPIC_API_KEY fue rechazada. Revisala en Config.\n\n"
                         + _responder_offline(pregunta), "modo": "offline"}
    except anthropic.RateLimitError:
        return {"texto": "Claude esta rate-limited ahora mismo; proba en unos "
                         "segundos.\n\n" + _responder_offline(pregunta), "modo": "offline"}
    except Exception as e:
        return {"texto": f"No pude consultar a Claude ({type(e).__name__}). "
                         "Respondo offline:\n\n" + _responder_offline(pregunta),
                "modo": "offline"}


if __name__ == "__main__":
    print("Estado:", estado())
    print(responder("Que es el techo de demanda?")["texto"][:200])
