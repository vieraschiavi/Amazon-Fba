#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
desktop.py — MV FBA IA como aplicacion de ESCRITORIO nativa.

Arranca el servidor Streamlit por dentro (headless, en localhost, en un puerto
libre) y lo muestra dentro de una VENTANA NATIVA propia (pywebview): abre como un
programa comun, sin navegador visible ni ventana de consola. Al cerrar la ventana,
apaga el servidor.

Uso:
    pythonw desktop.py     (Windows: sin consola)
    python  desktop.py

Si falta pywebview, cae a abrir el navegador por defecto para no dejar al usuario
sin nada (y avisa como instalarlo).
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request

_RAIZ = os.path.dirname(os.path.abspath(__file__))
TITULO = "MV FBA IA"
APP = os.path.join(_RAIZ, "dashboard_app.py")


def _puerto_libre():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _arrancar_streamlit(puerto):
    """Lanza Streamlit headless. Devuelve el proceso."""
    env = dict(os.environ)
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_PORT"] = str(puerto)
    env["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    env["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    cmd = [sys.executable, "-m", "streamlit", "run", APP,
           "--server.headless=true", f"--server.port={puerto}",
           "--server.address=127.0.0.1", "--browser.gatherUsageStats=false",
           "--global.developmentMode=false"]
    # En Windows, sin ventana de consola para el subproceso.
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(cmd, env=env, cwd=_RAIZ, creationflags=creationflags)


def _esperar(puerto, timeout=60):
    url = f"http://127.0.0.1:{puerto}/"
    fin = time.time() + timeout
    while time.time() < fin:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    puerto = _puerto_libre()
    proc = _arrancar_streamlit(puerto)
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
        # Sin pywebview: al menos abrir el navegador para no dejar la app inservible.
        import webbrowser
        print("pywebview no esta instalado (pip install pywebview); "
              "abro en el navegador. Para la ventana nativa: pip install pywebview")
        webbrowser.open(url)
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
        return

    icono = os.path.join(_RAIZ, "mobile", "icons", "icon-512.png")
    ventana = webview.create_window(
        TITULO, url, width=1360, height=880, min_size=(1024, 680),
        confirm_close=False)
    try:
        # gui por defecto del SO (EdgeChromium en Windows, GTK/Qt en Linux, Cocoa en Mac)
        webview.start(icon=icono if os.path.isfile(icono) else None)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
