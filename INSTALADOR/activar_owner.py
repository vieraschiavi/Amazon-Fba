#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
activar_owner.py — Deja una instalacion YA HECHA de MV FBA IA en edicion OWNER
(plan Pro, sin limite de dias, sin pantalla de activacion), sin recompilar nada.

QUE HACE, EXACTAMENTE
---------------------
Lo mismo que el paso "Escribir licencia owner" del workflow de GitHub, pero
contra la carpeta donde el programa ya esta instalado:

  1. le pide al servidor la licencia de dueño (/api/licencia?dueno=1),
  2. verifica que la clave devuelta tenga el formato real,
  3. la escribe en owner_licencia.json al lado de app.py.

Al reabrir el programa, core/licencia.py -> intentar_activacion_owner() lee ese
archivo y activa la licencia CONTRA EL SERVIDOR, igual que cualquier activacion.

POR QUE NO PUEDE SER "SIN PONER NADA"
-------------------------------------
La clave se firma con HMAC usando LICENCIA_SECRETO, que vive SOLO en Vercel
(ver api/_licencia.js). Ningun programa local puede calcularla: hay que
pedirsela al servidor. Y el servidor no se la da a cualquiera que diga ser el
dueño -- el mail del dueño es publico, adivinarlo es trivial. Pide UNA prueba:

  * un token de GitHub con acceso de escritura a este repo  (lo normal), o
  * el OWNER_BUILD_TOKEN, si preferis un secreto compartido.

Esa prueba es lo unico que separa "el dueño" de "un cliente que quiere Pro
gratis". Sacarla convertiria este script en un crack de tu propio producto:
cualquiera que lo consiguiera tendria la version completa sin pagar. Por eso
pide el token una vez, y no lo guarda en ningun lado.

USO
    python activar_owner.py [--carpeta RUTA] [--email MAIL]

El token se pide por teclado (no se muestra, no se guarda, no va a disco).
Tambien se puede pasar por variable de entorno MV_GITHUB_TOKEN o
MV_OWNER_BUILD_TOKEN para no tipearlo.
"""
import argparse
import getpass
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("MV_API_BASE", "https://mvfbaia.com")
EMAIL_POR_DEFECTO = "vieraschiavi@gmail.com"

# Mismo formato que exige el CI antes de publicar un build owner: si el
# servidor devolviera cualquier otra cosa (una pagina de error, un JSON raro),
# no se escribe nada -- mejor fallar aca que dejar un owner_licencia.json
# invalido que haga fallar la activacion en silencio al abrir el programa.
FORMATO_CLAVE = re.compile(r"^MVFBA(-[A-F0-9]{4}){4}$")

# Mismo AppId que installer/MV_Amazon_FBA_IA.iss (linea "AppId={{...}"; las
# llaves dobles son el escape de Inno Setup para una llave literal). Hay un
# test de regresion (test_activar_owner.py::test_app_id_coincide_con_el_iss)
# que lo compara contra el .iss para que esta constante nunca quede
# desincronizada si el AppId cambia alla.
APP_ID = "{8F2C1A6E-7B4D-4E1A-9C3F-2D8E5A6B7C90}"

# Carpetas donde el instalador deja el programa (ver CarpetaPorDefecto en el
# .iss): con permisos de admin va a Archivos de programa, si no al perfil.
# Se mantienen como ULTIMO fallback -- ver _buscar_por_registro() abajo, que
# encuentra la instalacion real sin importar donde la haya puesto el usuario.
CANDIDATAS = [
    r"C:\Program Files\MV FBA IA",
    r"C:\Program Files (x86)\MV FBA IA",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\MV FBA IA"),
    os.path.expandvars(r"%USERPROFILE%\Desktop\MV FBA IA"),   # version portable
]


def es_instalacion(ruta):
    """Una carpeta sirve si tiene el motor y el modulo de licencia adentro."""
    return bool(ruta) and os.path.isfile(os.path.join(ruta, "app.py")) \
        and os.path.isfile(os.path.join(ruta, "core", "licencia.py"))


def _buscar_por_registro(winreg_mod=None):
    """Encuentra DONDE SE INSTALO de verdad, leyendo el registro de Windows
    -- funciona sin importar que carpeta haya elegido el usuario en la
    pagina "elegir destino" del instalador (el .iss deja elegir cualquiera,
    ver DisableDirPage=no), a diferencia de CANDIDATAS, que solo adivina las
    4 rutas mas comunes.

    Todo instalador de Inno Setup registra su instalacion en
    "Agregar o quitar programas" bajo una clave con el AppId del .iss, y esa
    entrada SIEMPRE trae "InstallLocation" apuntando a la carpeta real
    ({app} en el .iss) -- es el mismo mecanismo que usa Windows para mostrar
    el programa en el panel de control, no algo que este instalador tenga
    que declarar aparte.

    Revisa primero HKEY_CURRENT_USER (instalacion "solo para mi", sin admin
    -- el caso mas comun, ver PrivilegesRequired=lowest) y despues
    HKEY_LOCAL_MACHINE (instalacion "para todos los usuarios"). `winreg_mod`
    existe para poder inyectar un modulo winreg FALSO desde los tests (en
    Linux no existe winreg de verdad)."""
    winreg = winreg_mod
    if winreg is None:
        try:
            import winreg as winreg  # noqa: F401  -- solo existe en Windows
        except ImportError:
            return None

    subclave = ("SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\"
                + APP_ID + "_is1")
    for raiz in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(raiz, subclave) as clave:
                valor, _tipo = winreg.QueryValueEx(clave, "InstallLocation")
        except OSError:
            continue          # esta rama no tiene la clave (no se instalo asi) -- probar la otra
        valor = (valor or "").strip().rstrip("\\")
        if es_instalacion(valor):
            return os.path.abspath(valor)
    return None


def buscar_instalacion(preferida=None, winreg_mod=None):
    """Orden: lo que pidio el usuario, la carpeta desde donde se corre esto
    (el caso normal: el .bat vive al lado del programa), el registro de
    Windows (encuentra CUALQUIER carpeta que el usuario haya elegido al
    instalar), y recien al final las rutas mas comunes adivinadas a mano."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    for ruta in [preferida, aqui, os.getcwd()]:
        if es_instalacion(ruta):
            return os.path.abspath(ruta)
    por_registro = _buscar_por_registro(winreg_mod)
    if por_registro:
        return por_registro
    for ruta in CANDIDATAS:
        if es_instalacion(ruta):
            return os.path.abspath(ruta)
    return None


def pedir_licencia(email, token_github="", token_build=""):
    """Le pide la licencia de dueño al servidor. Devuelve (clave, plan) o lanza
    RuntimeError con un mensaje explicando que paso."""
    url = f"{API}/api/licencia?dueno=1&email={urllib.parse.quote(email)}"
    cabeceras = {"x-mv-app": "mvfba-web-1"}
    if token_github:
        cabeceras["x-mv-github-token"] = token_github
    if token_build:
        cabeceras["x-mv-owner-build"] = token_build
    req = urllib.request.Request(url, headers=cabeceras)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise RuntimeError(
                "El servidor no autorizo el pedido (403).\n"
                "  - Si usaste un token de GitHub: tiene que tener acceso de\n"
                "    ESCRITURA a vieraschiavi/Amazon-Fba (scope 'repo').\n"
                f"  - Y el email tiene que ser exactamente el OWNER_EMAIL\n"
                f"    configurado en Vercel (probaste con: {email}).")
        raise RuntimeError(f"El servidor respondio HTTP {e.code}.")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"No se pudo contactar a {API} ({e}). Revisa tu conexion.")
    except ValueError:
        raise RuntimeError("El servidor devolvio algo que no es JSON.")

    clave = str(d.get("licencia") or "").strip().upper()
    if not clave:
        raise RuntimeError("El servidor no devolvio ninguna licencia.")
    if not FORMATO_CLAVE.match(clave):
        # No se imprime la clave: podria ser cualquier cosa y no vale la pena
        # dejarla en pantalla/logs.
        raise RuntimeError("La clave devuelta no tiene el formato "
                           "MVFBA-XXXX-XXXX-XXXX-XXXX. No se escribio nada.")
    return clave, str(d.get("plan") or "pro")


def escribir(carpeta, email, clave):
    destino = os.path.join(carpeta, "owner_licencia.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump({"email": email, "clave": clave}, f, ensure_ascii=False, indent=2)
    return destino


def main():
    ap = argparse.ArgumentParser(description="Activa una instalacion como OWNER")
    ap.add_argument("--carpeta", help="carpeta del programa (si no, se busca sola)")
    ap.add_argument("--email", default=EMAIL_POR_DEFECTO, help="email del dueño")
    a = ap.parse_args()

    carpeta = buscar_instalacion(a.carpeta)
    if not carpeta:
        print("[X] No encontre una instalacion de MV FBA IA.")
        print("    Busque en el registro de Windows (deberia encontrar CUALQUIER")
        print("    carpeta que hayas elegido al instalar) y tambien en estas rutas:")
        for c in CANDIDATAS:
            print("      " + c)
        print("    Si aun asi no aparece, copia este archivo (y ACTIVAR_OWNER.bat)")
        print("    DENTRO de la carpeta del programa -- la que tiene app.py adentro")
        print("    -- y volve a correrlo.")
        return 1

    print(f"    Instalacion: {carpeta}")
    print(f"    Email:       {a.email}")

    token_build = os.environ.get("MV_OWNER_BUILD_TOKEN", "").strip()
    token_github = os.environ.get("MV_GITHUB_TOKEN", "").strip()
    if not token_github and not token_build:
        print()
        print("    Hace falta UNA prueba de que sos el dueño (el servidor no")
        print("    entrega la licencia Pro solo con el mail: es publico).")
        print("    Pega un token de GitHub con acceso a este repo y Enter.")
        print("    No se muestra mientras escribis, y no se guarda en ningun lado.")
        try:
            token_github = getpass.getpass("    Token: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[X] Cancelado.")
            return 1
    if not token_github and not token_build:
        print("[X] Sin token no se puede pedir la licencia.")
        return 1

    print()
    print("    Pidiendo la licencia de dueño al servidor...")
    try:
        clave, plan = pedir_licencia(a.email, token_github, token_build)
    except RuntimeError as e:
        print(f"[X] {e}")
        return 1

    destino = escribir(carpeta, a.email, clave)
    # La clave NO se imprime: queda en el archivo y nada mas.
    print(f"    Listo. Escrito: {destino}   (plan: {plan})")
    print()
    print("    Cerra el programa si esta abierto y volve a abrirlo:")
    print("    se activa solo, sin pedirte nada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
