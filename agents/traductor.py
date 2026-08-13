#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/traductor.py — Traduce una keyword/seed al idioma de un marketplace de
Amazon, para investigar nichos en otros paises SIN escribir a mano en cada idioma.

Con ANTHROPIC_API_KEY traduce con Claude (natural, entiende jerga de producto).
Sin clave, deja el texto igual y avisa (el autocompletado del marketplace igual
localiza los resultados; la traduccion del seed solo ayuda a arrancar en idioma).
"""
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import config  # noqa: E402

_IDIOMAS = {
    "en": "inglés", "es": "español", "de": "alemán", "fr": "francés",
    "it": "italiano", "pt": "portugués", "ja": "japonés",
}


def traducir(texto, idioma_destino="en"):
    """Devuelve {ok, texto, original, fuente, mensaje}. Nunca lanza excepcion:
    si algo falla, devuelve el texto original para no cortar la investigacion."""
    texto = (texto or "").strip()
    idioma = _IDIOMAS.get(idioma_destino, idioma_destino)
    if not texto:
        return {"ok": False, "texto": "", "original": texto, "fuente": "-",
                "mensaje": "Escribí una keyword para traducir."}
    if not config.ANTHROPIC_API_KEY:
        return {"ok": True, "texto": texto, "original": texto, "fuente": "sin traducir",
                "mensaje": f"Sin ANTHROPIC_API_KEY no traduzco el seed, pero el "
                           f"buscador igual trae keywords localizadas del marketplace. "
                           f"Para traducir automáticamente, cargá la clave en Config."}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=config.MODEL_HAIKU, max_tokens=120,
            system=(f"Sos un traductor de keywords de e-commerce. Traducí el término "
                    f"de producto al {idioma} tal como lo buscaría un comprador en "
                    f"Amazon (natural, no literal). Respondé SOLO la traducción, sin "
                    f"comillas ni explicación."),
            messages=[{"role": "user", "content": texto}])
        bloque = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
        trad = (bloque or "").strip().strip('"').strip()
        if not trad:
            return {"ok": True, "texto": texto, "original": texto, "fuente": "sin traducir",
                    "mensaje": "No obtuve traducción; uso el término original."}
        return {"ok": True, "texto": trad, "original": texto, "fuente": f"Claude → {idioma}",
                "mensaje": f"'{texto}' → '{trad}' ({idioma})."}
    except Exception as e:
        return {"ok": True, "texto": texto, "original": texto, "fuente": "sin traducir",
                "mensaje": f"No pude traducir ({type(e).__name__}); uso el término original."}


if __name__ == "__main__":
    print(traducir("bamboo kitchen utensils", "es"))
