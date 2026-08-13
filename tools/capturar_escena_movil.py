#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""Genera landing/media/escena-plataformas-<idioma>.jpg (PWA movil).

Requiere Playwright + el Chromium del entorno. Tras correrlo, convertir los
PNG de /tmp/escenas a JPG y copiarlos a landing/media/.

Captura la escena 'multiplataforma' (la PWA movil) en los 3 idiomas."""
import functools, http.server, json, os, socketserver, threading, time

RAIZ = "/home/user/Amazon-Fba/mobile"
PORT = 8124
SALIDA = "/tmp/escenas"
os.makedirs(SALIDA, exist_ok=True)

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=RAIZ)
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(1)

from playwright.sync_api import sync_playwright

# registro ya hecho -> la app no muestra el gate; fecha de hoy -> 7 dias restantes
registro = {"nombre": "Demo", "email": "demo@mvfbaia.com",
            "fechaRegistro": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())}

with sync_playwright() as p:
    nav = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    for lang in ("es", "en", "pt"):
        ctx = nav.new_context(viewport={"width": 430, "height": 880},
                              device_scale_factor=2, is_mobile=True,
                              has_touch=True)
        ctx.add_init_script(
            f"localStorage.setItem('mvfba_registro_v1', {json.dumps(json.dumps(registro))});"
            f"localStorage.setItem('mvfba_idioma', '{lang}');")
        pag = ctx.new_page()
        pag.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")
        pag.wait_for_timeout(1500)
        # cargar el producto de ejemplo para que el resumen tenga numeros
        # 1) overlay de bienvenida -> "Ver con datos de ejemplo"
        try:
            pag.click("#bienvenida-demo", timeout=5000)
            pag.wait_for_timeout(2000)
        except Exception as e:
            print(f"    aviso: sin bienvenida ({type(e).__name__})")
        # 2) cerrar el tour guiado si aparece
        for _ in range(4):
            try:
                pag.click("#tour-saltar", timeout=1500)
                pag.wait_for_timeout(400)
                break
            except Exception:
                break
        # 3) volver a Inicio (el resumen ejecutivo es la escena del video)
        try:
            pag.click('.nav-btn[data-vista="inicio"]', timeout=4000)
            pag.wait_for_timeout(1500)
        except Exception as e:
            print(f"    aviso: sin inicio ({type(e).__name__})")
        pag.screenshot(path=f"{SALIDA}/escena-plataformas-{lang}.png")
        print(f"  {lang}  escena-plataformas-{lang}.png")
        ctx.close()
    nav.close()
srv.shutdown()
print("listo")
