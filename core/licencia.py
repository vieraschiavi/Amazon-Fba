#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/licencia.py — Registro y demo de 7 dias por usuario, sin servidor.

Nombre comercial del producto: "MV FBA IA" (antes "MV Amazon FBA IA"; se saco
"Amazon" del nombre de marca para reducir riesgo de marca registrada, ver
README). El dominio/identificador interno de la licencia se deja SIN TOCAR
a proposito: "MV-Amazon-Fba". Es invisible para el usuario y cambiar la
formula HMAC invalidaria las licencias ya emitidas a clientes que ya pagaron.

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
DIAS_DEMO = 7

# Build "owner" (interno): el instalador del dueño trae un owner_licencia.json
# con {email, clave} ya adentro, para que el programa se auto-active como Pro
# en el primer arranque sin tener que pegar la clave a mano. NO es un bypass:
# la clave se valida CONTRA EL SERVIDOR igual que cualquier activacion (misma
# funcion activar_licencia) -- sin una clave real y su email, el archivo no
# sirve. El instalador normal (el que compran los clientes) NO incluye este
# archivo (ver el flag skipifsourcedoesntexist en el .iss), asi que para ellos
# no existe. Necesita internet una sola vez, como toda activacion.
RUTA_OWNER = os.path.join(_RAIZ, "owner_licencia.json")
_owner_intentado = False


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
    """Arranca la demo full de 7 dias para este usuario. Idempotente: si ya
    hay un registro en esta instalacion, lo devuelve sin reiniciar el reloj."""
    _tabla()
    ya = obtener()
    if ya:
        return ya
    db.insert("registro", nombre=(nombre or "").strip(), email=(email or "").strip(),
               dominio=DOMINIO, fecha_registro=_ahora().isoformat(),
               clave_licencia=None, fecha_activacion=None)
    _avisar_registro_demo((nombre or "").strip(), (email or "").strip())
    return obtener()


def _avisar_registro_demo(nombre, email):
    """Copia lateral best-effort en el servidor (api/demo-registro.js), SOLO
    para poder mandar el recordatorio de "tu demo vence mañana" -- el reloj
    real de los 7 dias sigue siendo la fila de arriba en SQLite. Si esto
    falla (sin internet en este instante, etc.) la demo funciona exactamente
    igual: nunca se espera ni se revisa esta respuesta."""
    if not email:
        return
    import json
    import urllib.request
    try:
        base = _API_VALIDAR.rsplit("/api/", 1)[0]
        cuerpo = json.dumps({"nombre": nombre, "email": email}).encode("utf-8")
        req = urllib.request.Request(base + "/api/demo-registro", data=cuerpo, method="POST",
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


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


def _api_base():
    return _API_VALIDAR.rsplit("/api/", 1)[0]


def consultar_creditos():
    """Saldo de creditos de IA compartida de la licencia activa (ver
    api/_creditosia.js), o None si no hay licencia, no hay internet, o el
    almacen del servidor no esta configurado. Nunca lanza -- el llamador
    (agents/asistente.py) trata None como 'no se pudo determinar'."""
    reg = obtener()
    if not reg or not reg.get("clave_licencia") or not reg.get("email"):
        return None
    import json
    import urllib.request
    import urllib.parse
    q = urllib.parse.urlencode({"email": reg["email"], "clave": reg["clave_licencia"]})
    try:
        with urllib.request.urlopen(_api_base() + "/api/creditos?" + q, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def preguntar_ia_compartida(pregunta, contexto, historial=None, idioma="es"):
    """Asistente de IA compartido (la clave de Claude vive en el servidor):
    fallback para quien no configuro su propia clave (BYOK) en Config, usando
    el saldo de creditos de la licencia activa (ver api/_creditosia.js) en
    vez de la clave propia. Devuelve:
      - None si no hay licencia activa, no hay internet, o el servidor no
        pudo responder (el llamador cae al modo offline en ese caso);
      - {"sin_creditos": True, "mensaje": ...} si el saldo esta en 0;
      - {"texto": ...} con la respuesta si salio bien.
    Nunca lanza."""
    reg = obtener()
    if not reg or not reg.get("clave_licencia") or not reg.get("email"):
        return None
    import json
    import urllib.request
    import urllib.error
    # El proxy (api/ia.js) recibe una sola pregunta + contexto (tope 4000
    # chars): el hilo reciente del chat va condensado dentro del contexto
    # para que el asistente no pierda de que se venia hablando.
    if historial:
        turnos = [m for m in historial[-4:]
                  if m.get("role") in ("user", "assistant") and m.get("content")]
        if turnos:
            hilo = "\n".join(
                ("Usuario: " if m["role"] == "user" else "Asistente: ")
                + m["content"][:300] for m in turnos)
            contexto = (contexto + "\n\nCONVERSACION RECIENTE:\n" + hilo)[:3900]
    payload = {
        "pregunta": pregunta, "contexto": contexto, "idioma": idioma,
        "email": reg["email"], "clave": reg["clave_licencia"], "dispositivo": "desktop",
    }
    req = urllib.request.Request(
        _api_base() + "/api/ia", data=json.dumps(payload).encode("utf-8"),
        method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {"texto": data.get("texto", "")}
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            data = {}
        if e.code == 429:
            return {"sin_creditos": True,
                    "mensaje": data.get("mensaje", "Se acabaron tus créditos de IA compartida.")}
        return None
    except Exception:
        return None


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


def intentar_activacion_owner():
    """Build owner: auto-activa desde owner_licencia.json en el primer arranque.
    Un solo intento por proceso (si fue offline, se reintenta al reabrir la
    app). Devuelve True si quedo activada. Nunca lanza."""
    global _owner_intentado
    if _owner_intentado or tiene_licencia():
        return False
    _owner_intentado = True
    if not os.path.isfile(RUTA_OWNER):
        return False
    try:
        import json
        with open(RUTA_OWNER, encoding="utf-8") as f:
            d = json.load(f)
        email = (d.get("email") or "").strip()
        clave = (d.get("clave") or "").strip()
    except Exception:
        return False
    if not email or not clave:
        return False
    try:
        return bool(activar_licencia(email, clave).get("ok"))
    except Exception:
        return False


def tiene_licencia(reg=None):
    reg = reg if reg is not None else obtener()
    return bool(reg and reg.get("clave_licencia"))


def demo_vigente(reg=None):
    reg = reg if reg is not None else obtener()
    return tiene_licencia(reg) or dias_restantes(reg) > 0


def estado(reg=None):
    """Resumen listo para la UI."""
    # Build owner: en el primer status check sin licencia, intenta auto-activar
    # desde owner_licencia.json (no-op en el build normal, que no trae el archivo).
    if reg is None and not tiene_licencia():
        intentar_activacion_owner()
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
