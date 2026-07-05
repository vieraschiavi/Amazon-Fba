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
La licencia definitiva (post-pago) se valida CONTRA EL SERVIDOR (api/validar):
el secreto de firma vive solo en Vercel, nunca en este cliente, asi no se puede
crackear leyendo el codigo. Activar la licencia pide internet una sola vez;
despues el programa sigue andando offline.
"""
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


# La validacion de la licencia se hace CONTRA EL SERVIDOR: el secreto de firma
# vive solo en Vercel (LICENCIA_SECRETO), nunca en este cliente de PC, asi nadie
# puede auto-generarse una clave leyendo el codigo. Activar pide internet una vez;
# despues la licencia queda guardada en la base local y el programa anda offline.
_API_VALIDAR = config.env("API_VALIDAR_URL",
                          "https://amazon-fba-seven.vercel.app/api/validar")


def validar_clave(email, clave):
    """Devuelve True/False consultando al servidor. Lanza RuntimeError si no hay
    conexion, para que la UI distinga 'sin internet' de 'clave invalida'."""
    import json
    import urllib.request
    import urllib.error
    cuerpo = json.dumps({"email": (email or "").strip(),
                         "clave": (clave or "").strip()}).encode("utf-8")
    req = urllib.request.Request(_API_VALIDAR, data=cuerpo, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        return bool(data.get("valido"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise RuntimeError("sin_conexion") from e


def activar_licencia(email, clave):
    try:
        ok = validar_clave(email, clave)
    except RuntimeError:
        return {"ok": False, "mensaje": "Necesitas internet para activar la "
                "licencia la primera vez. Reintenta con conexion."}
    if not ok:
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
