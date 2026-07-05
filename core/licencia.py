#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/licencia.py — Registro y demo de 3 dias por usuario, sin servidor.

Nombre comercial del producto: "MV Amazon FBA IA" (no cambia).
Dominio/identificador interno usado para la clave de licencia: "MV-Amazon-Fba".

Como no hay backend de cuentas (el sistema corre 100% local, sin depender de
internet), el registro y el conteo de dias viven en la base local (SQLite en
PC, localStorage en el telefono via su propio modulo JS equivalente). Esto
significa que reinstalar y volver a registrarse con otro email reinicia la
demo — es una limitacion conocida y aceptada de un esquema sin servidor.
La licencia definitiva (post-pago) se valida offline con una firma HMAC
derivada del email, asi el vendedor puede emitir claves sin necesitar un
servidor de licencias.
"""
import hashlib
import hmac
import os
import sys
from datetime import datetime, timezone

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import config  # noqa: E402
from core import db  # noqa: E402

DOMINIO = "MV-Amazon-Fba"
DIAS_DEMO = 3
_SECRETO = config.env("LICENCIA_SECRETO", "mv-amazon-fba-2026-clave-de-firma")


def _ahora():
    return datetime.now(timezone.utc)


def _tabla():
    db.execute("""CREATE TABLE IF NOT EXISTS registro(
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, email TEXT,
        dominio TEXT, fecha_registro TEXT, clave_licencia TEXT,
        fecha_activacion TEXT)""")


def obtener():
    _tabla()
    filas = db.rows("SELECT * FROM registro ORDER BY id DESC LIMIT 1")
    return filas[0] if filas else None


def registrar(nombre, email):
    """Arranca la demo full de 3 dias para este usuario. Idempotente: si ya
    hay un registro en esta instalacion, lo devuelve sin reiniciar el reloj."""
    _tabla()
    ya = obtener()
    if ya:
        return ya
    db.insert("registro", nombre=(nombre or "").strip(), email=(email or "").strip(),
               dominio=DOMINIO, fecha_registro=_ahora().isoformat(),
               clave_licencia=None, fecha_activacion=None)
    return obtener()


def dias_restantes(reg=None):
    reg = reg if reg is not None else obtener()
    if not reg or not reg.get("fecha_registro"):
        return 0.0
    try:
        inicio = datetime.fromisoformat(reg["fecha_registro"])
    except ValueError:
        return 0.0
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    transcurrido_dias = (_ahora() - inicio).total_seconds() / 86400.0
    return max(0.0, DIAS_DEMO - transcurrido_dias)


def generar_clave(email):
    """Clave de licencia definitiva para un email (la emite el vendedor tras
    el pago). Determinista: el mismo email siempre da la misma clave."""
    base = (email or "").strip().lower().encode("utf-8")
    firma = hmac.new(_SECRETO.encode("utf-8"), base + DOMINIO.encode("utf-8"),
                      hashlib.sha256).hexdigest().upper()[:16]
    grupos = "-".join(firma[i:i + 4] for i in range(0, 16, 4))
    return f"MVFBA-{grupos}"


def validar_clave(email, clave):
    return (clave or "").strip().upper() == generar_clave(email)


def activar_licencia(email, clave):
    if not validar_clave(email, clave):
        return {"ok": False, "mensaje": "Clave invalida para ese email."}
    reg = obtener() or registrar("", email)
    db.execute("UPDATE registro SET clave_licencia=?, fecha_activacion=?, email=? WHERE id=?",
               (clave.strip().upper(), _ahora().isoformat(), (email or "").strip(), reg["id"]))
    return {"ok": True, "mensaje": "Licencia activada. Acceso completo sin limite de dias."}


def tiene_licencia(reg=None):
    reg = reg if reg is not None else obtener()
    return bool(reg and reg.get("clave_licencia"))


def demo_vigente(reg=None):
    reg = reg if reg is not None else obtener()
    return tiene_licencia(reg) or dias_restantes(reg) > 0


def estado(reg=None):
    """Resumen listo para la UI."""
    reg = reg if reg is not None else obtener()
    restantes = dias_restantes(reg)
    return {
        "registrado": bool(reg),
        "licencia": tiene_licencia(reg),
        "vigente": demo_vigente(reg),
        "dias_restantes": int(restantes) + (1 if restantes % 1 else 0),
        "nombre": (reg or {}).get("nombre", ""),
        "email": (reg or {}).get("email", ""),
        "dominio": DOMINIO,
    }
