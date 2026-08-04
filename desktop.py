#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
desktop.py — MV FBA IA como aplicacion de ESCRITORIO nativa.

Arranca el servidor local (FastAPI/uvicorn: API + panel web SaaS compilado en
frontend/dist) en localhost y lo muestra dentro de una VENTANA NATIVA propia
(pywebview sobre Edge WebView2): abre como un programa comun, sin navegador
visible ni ventana de consola. Al cerrar la ventana, apaga el servidor.

Puerto: intenta primero el puerto fijo MVFBA_PUERTO (default 8765) para que el
origen sea estable entre arranques; si esta ocupado, cae a un puerto libre.
Las preferencias criticas (idioma, producto activo, reloj de demo/licencia)
viven en SQLite del lado del servidor, asi que un cambio de puerto no pierde
nada.

Uso:
    pythonw desktop.py     (Windows: sin consola)
    python  desktop.py

Si falta pywebview (o el runtime WebView2), cae a abrir el navegador por
defecto para no dejar al usuario sin nada.
"""
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request

# SIGTERM -> SystemExit, para que los bloques finally (que apagan el servidor
# hijo) corran tambien si el sistema/el usuario mata este proceso. Sin esto,
# el uvicorn hijo quedaba huerfano en el camino de fallback a navegador.
try:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
except Exception:
    pass  # plataformas sin SIGTERM configurable

_RAIZ = os.path.dirname(os.path.abspath(__file__))
TITULO = "MV FBA IA"
PUERTO_PREFERIDO = int(os.environ.get("MVFBA_PUERTO", "8765"))


def _puerto_disponible(puerto):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", puerto))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _puerto_libre():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _elegir_puerto():
    """Puerto fijo preferido (origen estable) o, si esta ocupado, uno libre."""
    if _puerto_disponible(PUERTO_PREFERIDO):
        return PUERTO_PREFERIDO
    return _puerto_libre()


def _arrancar_servidor(puerto):
    """Lanza uvicorn (app.py: API local + panel SaaS). Devuelve el proceso."""
    cmd = [sys.executable, "-m", "uvicorn", "app:app",
           "--host", "127.0.0.1", "--port", str(puerto), "--log-level", "warning"]
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(cmd, cwd=_RAIZ, creationflags=creationflags)


def _esperar(puerto, timeout=60):
    url = f"http://127.0.0.1:{puerto}/health"
    fin = time.time() + timeout
    while time.time() < fin:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def _avisar(texto):
    """Aviso VISIBLE al usuario.

    Se lanza con pythonw (sin consola) desde el acceso directo, asi que un
    print() no lo lee nadie: la app caia al navegador en silencio y parecia
    "un programa que abre una web". Con esto el usuario se entera de por que.
    """
    print(texto, file=sys.stderr)
    if os.name != "nt":
        return
    try:
        import ctypes
        # 0x40 = MB_ICONINFORMATION. Modal, pero es un solo clic y evita que
        # el usuario quede sin explicacion.
        ctypes.windll.user32.MessageBoxW(0, texto, TITULO, 0x40)
    except Exception:
        pass


def _icono():
    """Ruta del icono de la ventana, entre las que SI empaqueta el instalador.

    Antes apuntaba a mobile/icons/icon-512.png, pero el instalador no
    distribuye mobile/ (ver [Files] del .iss): instalado, la ventana quedaba
    siempre sin icono."""
    for rel in (("frontend", "dist", "icon.png"),
                ("assets", "icon.ico"),
                ("mobile", "icons", "icon-512.png")):
        p = os.path.join(_RAIZ, *rel)
        if os.path.isfile(p):
            return p
    return None


def _abrir_navegador(url, proc):
    import webbrowser
    webbrowser.open(url)
    try:
        proc.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def main():
    puerto = _elegir_puerto()
    proc = _arrancar_servidor(puerto)
    url = f"http://127.0.0.1:{puerto}/"
    if not _esperar(puerto):
        try:
            proc.terminate()
        except Exception:
            pass
        print("No se pudo iniciar el motor de la app.", file=sys.stderr)
        sys.exit(1)

    try:
        import webview  # pywebview
    except Exception:
        _avisar("MV FBA IA se va a abrir en el navegador porque falta la "
                "librería pywebview.\n\n"
                "Si INSTALASTE el programa, reinstalalo: el runtime incluido "
                "está incompleto.\n"
                "Si estás corriendo el código del repositorio, instalá las "
                "dependencias:\n\n"
                "    pip install -r requirements.txt")
        _abrir_navegador(url, proc)
        return

    icono = _icono()
    webview.create_window(
        TITULO, url, width=1360, height=880, min_size=(1024, 680),
        confirm_close=False)
    try:
        # gui="edgechromium" FORZADO en Windows: el SPA moderno no corre en el
        # fallback MSHTML (IE11) de pywebview — si no hay WebView2, preferimos
        # el navegador del usuario antes que una pantalla blanca.
        if os.name == "nt":
            webview.start(gui="edgechromium", icon=icono)
        else:
            webview.start(icon=icono)
    except Exception as e:
        # Causa casi siempre: falta el runtime WebView2 de Microsoft Edge. Es un
        # componente del SISTEMA, no viaja dentro de runtime\; el instalador lo
        # pone solo, pero si se corre desde el codigo hay que instalarlo a mano.
        _avisar("MV FBA IA no pudo abrir su ventana propia, así que se abre en "
                "el navegador.\n\n"
                "Falta el runtime WebView2 de Microsoft Edge, que es el que "
                "dibuja la ventana.\n\n"
                "Solución: instalalo gratis desde\n"
                "https://developer.microsoft.com/microsoft-edge/webview2/\n"
                "(opción \"Evergreen Bootstrapper\") y volvé a abrir el programa.\n\n"
                f"Detalle técnico: {e}")
        _abrir_navegador(url, proc)
        return
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
