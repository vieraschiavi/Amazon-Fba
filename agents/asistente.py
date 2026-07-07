#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/asistente.py — Asistente IA (Claude) de MV FBA IA.

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
    "Sos el asistente de MV FBA IA, un cockpit para operar un negocio "
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


_NOMBRE_PROV = {"claude": "Claude", "openai": "OpenAI (ChatGPT)", "gemini": "Gemini"}


def estado():
    """Estado del asistente para el panel: online (proveedor elegido) u offline."""
    prov, clave, modelo = config.ia_provider_activo()
    if not prov:
        return {"ok": False, "modo": "offline", "proveedor": None,
                "mensaje": "Sin clave de IA: respondo desde el glosario. Elegí un "
                           "proveedor (Claude recomendado) y pegá tu clave en Config."}
    if prov == "claude":
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return {"ok": False, "modo": "offline", "proveedor": "claude",
                    "mensaje": "Falta el paquete 'anthropic' (pip install anthropic). "
                               "Mientras tanto respondo desde el glosario."}
    return {"ok": True, "modo": "online", "proveedor": prov,
            "mensaje": f"Asistente {_NOMBRE_PROV.get(prov, prov)} conectado ({modelo})."}


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


def _http_json(url, payload, headers, timeout=45):
    """POST JSON con urllib (sin dependencias). Devuelve dict parseado."""
    import json
    import urllib.request
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _responder_claude(system, mensajes, clave, modelo, max_tokens):
    import anthropic
    client = anthropic.Anthropic(api_key=clave)
    resp = client.messages.create(model=modelo, max_tokens=max_tokens,
                                  system=system, messages=mensajes)
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _responder_openai(system, mensajes, clave, modelo, max_tokens):
    payload = {"model": modelo, "max_tokens": max_tokens,
               "messages": [{"role": "system", "content": system}] + mensajes}
    data = _http_json("https://api.openai.com/v1/chat/completions", payload,
                      {"Authorization": "Bearer " + clave})
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")


def _responder_gemini(system, mensajes, clave, modelo, max_tokens):
    import urllib.parse
    contents = [{"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]} for m in mensajes]
    payload = {"systemInstruction": {"parts": [{"text": system}]},
               "contents": contents,
               "generationConfig": {"maxOutputTokens": max_tokens}}
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + urllib.parse.quote(modelo) + ":generateContent?key="
           + urllib.parse.quote(clave))
    data = _http_json(url, payload, {})
    cand = (data.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts)


_DISPATCH = {"claude": _responder_claude, "openai": _responder_openai,
             "gemini": _responder_gemini}


def responder(pregunta, historial=None, max_tokens=1400):
    """
    Responde `pregunta` con el proveedor de IA elegido (Claude/OpenAI/Gemini).
    `historial`: lista de {"role","content"} previos (opcional).
    Devuelve {"texto", "modo", "proveedor"}. Nunca lanza: si la IA falla, cae a offline.
    """
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return {"texto": "Escribime una pregunta sobre tu negocio FBA.", "modo": "offline"}

    prov, clave, modelo = config.ia_provider_activo()
    if not prov:
        return {"texto": _responder_offline(pregunta), "modo": "offline"}
    if prov == "claude":
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return {"texto": _responder_offline(pregunta), "modo": "offline"}

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

    try:
        texto = _DISPATCH[prov](system, mensajes, clave, modelo, max_tokens)
        return {"texto": (texto or "").strip() or _responder_offline(pregunta),
                "modo": "online", "proveedor": prov}
    except Exception as e:
        nom = _NOMBRE_PROV.get(prov, prov)
        return {"texto": f"No pude consultar a {nom} ({type(e).__name__}). "
                         "Revisá tu clave en Config. Respondo offline:\n\n"
                         + _responder_offline(pregunta),
                "modo": "offline", "proveedor": prov}


_SYSTEM_PROGRAMA = (
    "Sos el asistente de AYUDA de MV FBA IA: respondes dudas sobre COMO USAR el "
    "programa (que hace cada pestana, donde esta cada funcion, como encadenar el "
    "flujo, demo/licencia/idioma). Tono profesional pero amable, claro y concreto, "
    "en espanol rioplatense — pero si te preguntan en ingles o portugues, "
    "respondes en ese idioma.\n\n"
    "REGLAS: Respondete SOLO desde el manual que se te pasa abajo; si algo no "
    "esta en el manual, decilo honestamente y sugeri escribir a soporte desde la "
    "seccion Contacto de la pestana Ayuda. Guia con pasos concretos ('anda a la "
    "pestana X, toca Y'). No inventes funciones que el programa no tiene. Si la "
    "pregunta es del NEGOCIO (sus numeros, estrategia FBA), deriva amablemente a "
    "la pestana Asistente IA, que tiene los datos reales del negocio."
)


_OFFLINE_PROGRAMA_TXT = {
    "es": {"pre": "Modo offline (sin clave de IA). Del manual, ",
           "post": "Para respuestas conversacionales, conecta una clave de IA en Config.",
           "nada": "Modo offline (sin clave de IA). No encontre esa duda en el manual: "
                   "revisa el tutorial de arriba seccion por seccion, o escribinos desde "
                   "la seccion Contacto de esta misma pestana."},
    "en": {"pre": "Offline mode (no AI key). From the manual, ",
           "post": "For conversational answers, connect an AI key in Settings.",
           "nada": "Offline mode (no AI key). I couldn't find that in the manual: "
                   "check the tutorial above section by section, or write to us from "
                   "the Contact section on this same tab."},
    "pt": {"pre": "Modo offline (sem chave de IA). Do manual, ",
           "post": "Para respostas conversacionais, conecte uma chave de IA em Config.",
           "nada": "Modo offline (sem chave de IA). Nao encontrei essa duvida no manual: "
                   "confira o tutorial acima secao por secao, ou escreva para nos pela "
                   "secao Contato desta mesma aba."},
}


def _responder_programa_offline(pregunta, idioma="es"):
    """Fallback sin clave: busca la seccion del tutorial que mejor matchee."""
    from agents import tutorial
    txt = _OFFLINE_PROGRAMA_TXT.get(idioma, _OFFLINE_PROGRAMA_TXT["es"])
    hits = tutorial.buscar(pregunta, idioma)
    if not hits:
        vistos, out = set(), []
        for w in "".join(c if c.isalnum() else " " for c in pregunta.lower()).split():
            if len(w) > 3 and w not in _STOP:
                for s in tutorial.buscar(w, idioma):
                    if s["clave"] not in vistos:
                        vistos.add(s["clave"])
                        out.append(s)
        hits = out
    if hits:
        s = hits[0]
        pasos = "\n".join(f"{i}. {p}" for i, p in enumerate(s["pasos"], 1))
        return (f"{txt['pre']}**{s['titulo']}**:\n\n"
                f"_{s['para_que']}_\n\n{pasos}\n\n{txt['post']}")
    return txt["nada"]


_IDIOMA_NOMBRE = {"es": "espanol", "en": "ingles (English)", "pt": "portugues (Portuguese)"}


def responder_programa(pregunta, historial=None, max_tokens=1000, idioma="es"):
    """
    Responde dudas sobre COMO USAR el programa (pestana Ayuda), con el manual
    completo (agents/tutorial.py) como unico contexto, en el `idioma` activo
    del panel. Mismo patron honesto que responder(): con clave usa el
    proveedor elegido; sin clave/error cae al tutorial offline. Nunca lanza.
    """
    from agents import tutorial
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return {"texto": "Escribime tu duda sobre el programa.", "modo": "offline"}

    prov, clave, modelo = config.ia_provider_activo()
    if not prov:
        return {"texto": _responder_programa_offline(pregunta, idioma), "modo": "offline"}
    if prov == "claude":
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return {"texto": _responder_programa_offline(pregunta, idioma), "modo": "offline"}

    system = (_SYSTEM_PROGRAMA
              + f"\n\nIDIOMA DEL PANEL: el usuario tiene el programa en "
                f"{_IDIOMA_NOMBRE.get(idioma, 'espanol')} — responde en ese idioma "
                "salvo que pregunte en otro.\n\n=== MANUAL COMPLETO DEL PROGRAMA ===\n"
              + tutorial.contexto_para_ia(idioma))
    mensajes = []
    for m in (historial or [])[-8:]:
        rol = m.get("role")
        if rol in ("user", "assistant") and m.get("content"):
            mensajes.append({"role": rol, "content": m["content"]})
    mensajes.append({"role": "user", "content": pregunta})

    try:
        texto = _DISPATCH[prov](system, mensajes, clave, modelo, max_tokens)
        return {"texto": (texto or "").strip() or _responder_programa_offline(pregunta, idioma),
                "modo": "online", "proveedor": prov}
    except Exception as e:
        nom = _NOMBRE_PROV.get(prov, prov)
        return {"texto": f"No pude consultar a {nom} ({type(e).__name__}). "
                         "Respondo desde el manual:\n\n"
                         + _responder_programa_offline(pregunta, idioma),
                "modo": "offline", "proveedor": prov}


if __name__ == "__main__":
    print("Estado:", estado())
    print(responder("Que es el techo de demanda?")["texto"][:200])
    print(responder_programa("Como uso el recomendador?")["texto"][:200])
