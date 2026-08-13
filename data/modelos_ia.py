#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
data/modelos_ia.py — Lista los modelos disponibles de cada proveedor de IA
usando la clave BYOK del usuario.

POR QUE EXISTE: el panel dejaba elegir PROVEEDOR pero el modelo estaba fijo en
el .env. Elegir el modelo es lo que de verdad regula el gasto de tokens (un
Haiku o un gpt-4o-mini cuesta una fraccion de un Opus), y una lista de modelos
escrita a mano en el codigo envejece: cada proveedor saca versiones nuevas cada
pocas semanas. Por eso la lista se PIDE a la API de cada proveedor con la clave
del usuario, en vez de estar hardcodeada.

Sin clave de un proveedor no se inventa nada: se dice "sin clave" y listo
(misma regla que el resto del sistema — sin CSV ni API key, se avisa).

La lista se cachea en un JSON en la carpeta de datos del usuario para no
pegarle a la API en cada apertura del panel: el boton "Actualizar" es lo que
refresca.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import config                                              # noqa: E402

CACHE_PATH = os.path.join(config.DIR_DATOS, "modelos_ia.json")

# Como se le pregunta a cada proveedor por sus modelos. Tres formas de
# autenticar y dos formas de contestar; se resuelve por proveedor en vez de
# adivinar, porque cada API es como es.
#   auth: "x-api-key" | "bearer" | "query"  (Gemini lleva la clave en la URL)
#   lista: donde viene el array en la respuesta
#   campo: de que campo sale el id del modelo
_FUENTES = {
    "claude": {"url": "https://api.anthropic.com/v1/models?limit=100",
               "auth": "x-api-key", "lista": "data", "campo": "id",
               "extra": {"anthropic-version": "2023-06-01"}},
    "openai": {"url": "https://api.openai.com/v1/models",
               "auth": "bearer", "lista": "data", "campo": "id"},
    "gemini": {"url": "https://generativelanguage.googleapis.com/v1beta/models",
               "auth": "query", "lista": "models", "campo": "name"},
    "grok": {"url": "https://api.x.ai/v1/models",
             "auth": "bearer", "lista": "data", "campo": "id"},
    "deepseek": {"url": "https://api.deepseek.com/models",
                 "auth": "bearer", "lista": "data", "campo": "id"},
}

# OpenAI devuelve TODO el catalogo en el mismo endpoint: embeddings, audio,
# imagenes, moderacion. Nada de eso sirve para chatear y ensuciaria el
# selector. Se filtra por lo que NO es chat (lista negra) y no por lo que si
# lo es: asi un modelo de chat nuevo que saquen mañana aparece igual, en vez
# de quedar invisible hasta que alguien actualice una lista blanca.
_NO_SON_CHAT = ("embedding", "whisper", "tts", "dall-e", "moderation",
                "audio", "realtime", "image", "transcribe", "search",
                "davinci", "babbage", "codex", "sora", "computer-use")


def _es_chat(model_id):
    m = (model_id or "").lower()
    return bool(m) and not any(x in m for x in _NO_SON_CHAT)


def _get_json(url, headers, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "mvfba/1.0", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def listar(codigo, clave=None, timeout=20):
    """Modelos disponibles de un proveedor, con la clave BYOK del usuario.

    Devuelve {"ok", "proveedor", "modelos": [ids], "mensaje"}. Nunca lanza:
    un proveedor caido o una clave vencida no puede romper la pantalla de
    Configuracion entera.
    """
    prov = config.proveedor_ia(codigo)
    fuente = _FUENTES.get((codigo or "").strip().lower())
    if not prov or not fuente:
        return {"ok": False, "proveedor": codigo, "modelos": [],
                "mensaje": "Proveedor desconocido."}
    clave = (clave if clave is not None else config.clave_ia(codigo)).strip()
    if not clave:
        return {"ok": False, "proveedor": codigo, "modelos": [],
                "mensaje": f"Sin clave de {prov['nombre']}: pegala arriba y guardá."}

    url, headers = fuente["url"], dict(fuente.get("extra") or {})
    if fuente["auth"] == "bearer":
        headers["Authorization"] = "Bearer " + clave
    elif fuente["auth"] == "x-api-key":
        headers["x-api-key"] = clave
    else:                                   # query: la clave va en la URL
        url += ("&" if "?" in url else "?") + "key=" + urllib.parse.quote(clave)

    try:
        data = _get_json(url, headers, timeout)
    except urllib.error.HTTPError as e:
        # Gemini y xAI contestan 400 (no 401) cuando la clave no sirve, y en
        # este endpoint la clave es el UNICO dato que se manda: un 400 aca es,
        # en la practica, una clave mal pegada.
        detalle = ("clave rechazada" if e.code in (400, 401, 403)
                   else f"HTTP {e.code}")
        return {"ok": False, "proveedor": codigo, "modelos": [],
                "mensaje": f"{prov['nombre']}: {detalle}."}
    except Exception as e:
        return {"ok": False, "proveedor": codigo, "modelos": [],
                "mensaje": f"{prov['nombre']}: no se pudo consultar ({type(e).__name__})."}

    modelos = []
    for item in (data.get(fuente["lista"]) or []):
        if not isinstance(item, dict):
            continue
        # Gemini nombra sus modelos "models/gemini-2.0-flash" y ademas dice que
        # sabe hacer cada uno: los que no generan contenido (embeddings) se van.
        if codigo == "gemini":
            metodos = item.get("supportedGenerationMethods") or []
            if metodos and "generateContent" not in metodos:
                continue
        mid = str(item.get(fuente["campo"]) or "").split("/")[-1]
        if _es_chat(mid) and mid not in modelos:
            modelos.append(mid)
    modelos.sort()
    if not modelos:
        return {"ok": False, "proveedor": codigo, "modelos": [],
                "mensaje": f"{prov['nombre']}: la clave sirve pero no devolvió modelos de chat."}
    return {"ok": True, "proveedor": codigo, "modelos": modelos,
            "mensaje": f"{prov['nombre']}: {len(modelos)} modelo(s)."}


def _cache_leer():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _cache_escribir(d):
    try:
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, CACHE_PATH)
    except OSError:
        pass                                 # el cache es una comodidad, no un requisito


def actualizar(timeout=20):
    """Refresca la lista de TODOS los proveedores que tengan clave cargada.

    Es lo que hace el boton "Actualizar modelos" del panel. Los proveedores sin
    clave no se consultan (no hay a quien preguntarle) y se reportan como tales.
    """
    cache, resultados = _cache_leer(), []
    for p in config.PROVEEDORES_IA:
        cod = p["codigo"]
        if not config.clave_ia(cod):
            resultados.append({"ok": False, "proveedor": cod, "nombre": p["nombre"],
                               "modelos": [], "mensaje": "sin clave (no se consulta)"})
            continue
        r = listar(cod, timeout=timeout)
        r["nombre"] = p["nombre"]
        if r["ok"]:
            cache[cod] = r["modelos"]
        resultados.append(r)
    _cache_escribir(cache)
    return {"resultados": resultados, "modelos": disponibles()}


def disponibles():
    """Modelos a mostrar en el selector de cada proveedor.

    Lo ultimo que trajo el boton "Actualizar" y, si nunca se apreto, al menos
    el modelo por defecto + el que el usuario tenga elegido: el selector nunca
    aparece vacio ni pierde el valor actual.
    """
    cache = _cache_leer()
    salida = {}
    for p in config.PROVEEDORES_IA:
        cod = p["codigo"]
        lista = list(cache.get(cod) or [])
        for m in (p["modelo_default"], config.modelo_ia(cod)):
            if m and m not in lista:
                lista.append(m)
        salida[cod] = lista
    return salida


if __name__ == "__main__":
    import pprint
    pprint.pprint(actualizar())
