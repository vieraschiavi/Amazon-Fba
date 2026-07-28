#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera landing/media/escena-*-<idioma>.jpg (6 pantallas del SPA).

Requiere Playwright + el Chromium del entorno. Tras correrlo, convertir los
PNG de /tmp/escenas a JPG y copiarlos a landing/media/.

Captura las escenas del video-tour de la landing en los 3 idiomas.

El escenario del player es 16:9 con object-fit:cover desde arriba, asi que
capturamos con viewport 1600x900 (exactamente lo que se ve).
"""
import os, subprocess, sys, tempfile, time, urllib.request, json, shutil

RAIZ = "/home/user/Amazon-Fba"
PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"
SALIDA = "/tmp/escenas"
os.makedirs(SALIDA, exist_ok=True)

# escena -> (ruta hash, nombre de archivo)
ESCENAS = [
    ("investigacion", "/investigacion", "escena-investigacion"),
    ("pricing",       "/pricing",       "escena-pricing"),
    ("portafolio",    "/portafolio",    "escena-portafolio"),
    ("caja",          "/caja",          "escena-ganancias"),
    ("mercado",       "/mercado",       "escena-mercado"),
    ("asistente",     "/asistente",     "escena-asistente"),
]

def api(ruta, metodo="GET", cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

# ---------- levantar la app ----------
tmpdb = tempfile.mkdtemp(prefix="capturas_")
env = dict(os.environ, DB_PATH=os.path.join(tmpdb, "capturas.db"), ANTHROPIC_API_KEY="")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(PORT),
                        "--log-level", "warning"], cwd=RAIZ, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/health", timeout=2); break
        except Exception:
            time.sleep(0.5)
    else:
        raise SystemExit("la app no levanto")
    print("app arriba")

    # registro (para pasar el gate) + producto de ejemplo (datos realistas)
    api("/api/licencia/registro", "POST", {"nombre": "Demo", "email": "demo@mvfbaia.com"})
    api("/api/demo/ejemplo", "POST")
    print("demo registrada + producto de ejemplo cargado")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        navegador = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        for lang in ("es", "en", "pt"):
            api("/api/prefs", "PUT", {"idioma": lang})
            ctx = navegador.new_context(viewport={"width": 1600, "height": 900},
                                        device_scale_factor=1)
            pag = ctx.new_page()
            for clave, ruta, archivo in ESCENAS:
                pag.goto(f"{BASE}/#{ruta}", wait_until="networkidle")
                pag.wait_for_timeout(900)
                # acciones para que la pantalla muestre resultados, no formularios vacios
                try:
                    if clave == "caja":
                        pag.get_by_role("button").filter(
                            has_text=__import__("re").compile(
                                r"Proyectar|Project|Projetar", __import__("re").I)).first.click()
                        pag.wait_for_timeout(1200)
                    elif clave == "investigacion":
                        pag.get_by_role("button").filter(
                            has_text=__import__("re").compile(
                                r"Investigar|Research|Pesquisar", __import__("re").I)).first.click()
                        pag.wait_for_timeout(2500)
                    elif clave == "mercado":
                        pag.get_by_role("button").filter(
                            has_text=__import__("re").compile(
                                r"Explorar|Explore", __import__("re").I)).first.click()
                        pag.wait_for_timeout(2500)
                except Exception as e:
                    print(f"  aviso {lang}/{clave}: sin accion ({type(e).__name__})")
                pag.wait_for_timeout(400)
                destino = f"{SALIDA}/{archivo}-{lang}.png"
                pag.screenshot(path=destino)
                print(f"  {lang}  {archivo}-{lang}.png")
            ctx.close()
        navegador.close()
finally:
    srv.terminate()
    try: srv.wait(timeout=10)
    except Exception: srv.kill()
    shutil.rmtree(tmpdb, ignore_errors=True)
print("listo ->", SALIDA)
