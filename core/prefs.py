#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/prefs.py — Preferencias de UI persistidas en SQLite (tabla ui_prefs).

Por que server-side y no localStorage: la app de escritorio sirve el frontend
desde http://127.0.0.1:{puerto}, y el puerto puede variar entre arranques si el
preferido esta ocupado. localStorage se particiona por origen (host:puerto),
asi que cualquier estado guardado ahi se "perderia" al cambiar el puerto. En
SQLite las preferencias sobreviven a cualquier puerto, reinstalacion parcial o
cambio de navegador.

Solo se aceptan claves de la whitelist — esto no es un key/value generico.
"""
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from core import db  # noqa: E402

# Whitelist explicita: agregar aca antes de usar una clave nueva desde el SPA.
CLAVES_PERMITIDAS = ("idioma", "producto_activo_id", "tema", "modo_demo")

_DEFAULTS = {"idioma": "es", "producto_activo_id": "", "tema": "claro",
             "modo_demo": "1"}


def _tabla():
    db.execute("""CREATE TABLE IF NOT EXISTS ui_prefs (
        clave TEXT PRIMARY KEY,
        valor TEXT NOT NULL DEFAULT ''
    )""")


def obtener_todas():
    """Devuelve todas las prefs (defaults completados para claves faltantes)."""
    _tabla()
    guardadas = {r["clave"]: r["valor"]
                 for r in db.rows("SELECT clave, valor FROM ui_prefs")}
    return {k: guardadas.get(k, _DEFAULTS[k]) for k in CLAVES_PERMITIDAS}


def guardar(**pares):
    """Upsert de las claves permitidas; ignora silenciosamente el resto.
    Devuelve el estado completo resultante."""
    _tabla()
    for k, v in pares.items():
        if k not in CLAVES_PERMITIDAS or v is None:
            continue
        db.execute(
            "INSERT INTO ui_prefs (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
            (k, str(v)))
    return obtener_todas()


if __name__ == "__main__":
    db.init()
    print("antes:", obtener_todas())
    print("tras guardar:", guardar(idioma="en", producto_activo_id="3"))
