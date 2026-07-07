#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test/test_api_local.py — Tests de la API local (app.py + api_rutas.py).

Principio: cada endpoint nuevo es un PASSTHROUGH a una funcion Python — el
test compara la response contra la llamada directa a esa funcion con los
mismos argumentos. Cualquier divergencia es un bug de serializacion/ruteo,
nunca "otro resultado valido".

Usa una base de datos temporal (DB_PATH) para no tocar fba.db.
Correr:  python -m pytest test/test_api_local.py -q
     o:  python test/test_api_local.py   (fallback sin pytest)
"""
import json
import os
import sys
import tempfile

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

# DB temporal ANTES de importar config/app (config lee DB_PATH al importar)
_TMP = tempfile.mkdtemp(prefix="mvfba_test_")
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")

from fastapi.testclient import TestClient  # noqa: E402

import app as modapp  # noqa: E402
from agents import exito, glosario, pricing, tutorial  # noqa: E402
from agents import portafolio as agente_portafolio  # noqa: E402
from agents.capital_planner import escenario_inversor, proyeccion_realista  # noqa: E402
from agents import ganancias  # noqa: E402
from core import licencia, prefs  # noqa: E402
from data import motor_propio  # noqa: E402

cliente = TestClient(modapp.app)


def _igual(api_resp, directo):
    """Igualdad tras un round-trip JSON (la API serializa tuplas->listas)."""
    assert json.loads(json.dumps(api_resp)) == json.loads(json.dumps(directo))


# ---------------------- legacy (regresion n8n/mobile) ---------------------- #
def test_legacy_health():
    r = cliente.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_legacy_dashboard():
    assert cliente.get("/dashboard").status_code == 200


def test_legacy_ganancias():
    body = {"inversion": 1000, "techo_demanda": 290}
    r = cliente.post("/ganancias", json=body)
    assert r.status_code == 200
    directo = ganancias.simular(inversion=1000, unidades=None, costo=2.10,
                                flete=0.80, arancel_pct=6.0, prep=0.50,
                                fba_fee=None, precio=None,
                                precio_competencia=None, techo_demanda=290)
    _igual(r.json(), directo)


# ---------------------- licencia / prefs / demo ---------------------- #
def test_licencia_estado_y_registro():
    r = cliente.get("/api/licencia")
    assert r.status_code == 200
    _igual(r.json(), licencia.estado())
    r2 = cliente.post("/api/licencia/registro",
                      json={"nombre": "Test", "email": "test@test.com"})
    assert r2.status_code == 200
    assert r2.json()["registrado"] is True
    assert r2.json()["vigente"] is True     # demo de 3 dias recien arrancada


def test_prefs_roundtrip():
    r = cliente.put("/api/prefs", json={"idioma": "pt", "producto_activo_id": "7"})
    assert r.status_code == 200
    assert r.json()["idioma"] == "pt"
    assert r.json()["producto_activo_id"] == "7"
    _igual(cliente.get("/api/prefs").json(), prefs.obtener_todas())


def test_prefs_whitelist():
    antes = prefs.obtener_todas()
    r = cliente.put("/api/prefs", json={"idioma": "en"})
    assert r.status_code == 200
    # claves fuera del modelo no llegan; las permitidas si
    assert r.json()["idioma"] == "en"
    assert set(r.json().keys()) == set(antes.keys())


def test_demo_ejemplo_ciclo():
    assert cliente.post("/api/demo/ejemplo").json()["cargado"] is True
    assert cliente.get("/api/demo/ejemplo").json()["cargado"] is True
    assert cliente.delete("/api/demo/ejemplo").json()["cargado"] is False


# ---------------------- config ---------------------- #
def test_config_get_enmascara():
    r = cliente.get("/api/config")
    assert r.status_code == 200
    d = r.json()
    assert "claves" in d and "umbral_verde" in d
    for v in d["claves"].values():          # nunca claves en texto plano
        assert "sk-" not in v or "…" in v or v == ""


# ---------------------- finanzas (passthrough exacto) ---------------------- #
def test_pricing():
    body = {"costo": 2.10, "flete": 0.80, "arancel_pct": 6.0, "prep": 0.50,
            "precio_competencia": 19.99}
    r = cliente.post("/api/pricing", json=body)
    assert r.status_code == 200
    directo = pricing.evaluar({"costo": 2.10, "flete": 0.80,
                               "arancel_pct": 6.0, "prep": 0.50},
                              fba_fee=None, precio_competencia=19.99,
                              margen_obj=None)
    _igual(r.json(), directo)


def test_pricing_acos():
    r = cliente.get("/api/pricing/acos",
                    params={"margen_actual_pct": 37.0, "margen_minimo_pct": 12.0})
    assert r.json()["acos_maximo"] == pricing.acos_bancable(37.0, 12.0)


def test_caja_proyeccion():
    body = {"budget": 8000, "landed": 5.5, "precio": 24.0, "net_unit": 6.9,
            "techo_demanda": 290, "meses": 12}
    r = cliente.post("/api/caja/proyeccion", json=body)
    directo = proyeccion_realista(8000, 5.5, 24.0, 6.9, techo_demanda=290,
                                  meses=12)
    _igual(r.json(), directo)


def test_inversores_escenario():
    body = {"capital_propio": 10000, "n_productos": 2, "techo": 290,
            "precio": 24.0, "net_unit": 6.9, "landed": 5.5,
            "capital_inversor": 5000, "pct_facturacion": 10}
    r = cliente.post("/api/inversores/escenario", json=body)
    directo = escenario_inversor(10000, 2, 290, 24.0, 6.9, 5.5,
                                 capital_inversor=5000, pct_facturacion=10)
    _igual(r.json(), directo)


def test_inversores_retorno():
    r = cliente.post("/api/inversores/retorno", json={"ticket": 2000})
    directo = agente_portafolio.retorno_inversor(ticket=2000)
    _igual(r.json(), directo)


def test_plan_interes_compuesto():
    body = {"aporte_inicial": 5000, "aporte_periodico": 200,
            "tasa_anual_pct": 60, "anios": 3}
    r = cliente.post("/api/plan/interes-compuesto", json=body)
    directo = agente_portafolio.interes_compuesto(5000, 200, 60, 3)
    _igual(r.json(), directo)


def test_plan_portafolio():
    body = {"objetivo_mensual": 2500, "capital_propio": 10000}
    r = cliente.post("/api/plan/portafolio", json=body)
    directo = agente_portafolio.recomendar_portafolio(2500, 10000)
    _igual(r.json(), directo)


def test_plan_pitch_html():
    r = cliente.get("/api/plan/pitch", params={"ticket": 1000})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "<html" in r.text.lower()


# ---------------------- mercado / investigacion (modo demo) ---------------------- #
def test_motor_keywords_demo():
    r = cliente.get("/api/motor/keywords",
                    params={"seed": "bamboo kitchen", "demo": True,
                            "marketplace": "MX"})
    directo = motor_propio.investigar("bamboo kitchen", profundidad=1,
                                      demo=True, marketplace="MX")
    _igual(r.json(), directo)


def test_marketplaces():
    r = cliente.get("/api/marketplaces")
    codigos = [m["codigo"] for m in r.json()["marketplaces"]]
    assert "US" in codigos and "BR" in codigos
    assert all("mid" not in m for m in r.json()["marketplaces"])


def test_recomendador_demo():
    r = cliente.post("/api/recomendador/escanear",
                     json={"demo": True, "precio_min": 15, "precio_max": 45,
                           "top_n": 5})
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True and len(d["oportunidades"]) <= 5


def test_exito_demo_con_narrativa():
    r = cliente.get("/api/exito", params={"keyword": "bamboo", "demo": True,
                                          "precio": 24.0,
                                          "con_narrativa": True})
    d = r.json()
    assert d["evaluacion"]["ok"] is True
    assert "narrativa" in d and d["narrativa"]["texto"]
    assert d["pesos"] == json.loads(json.dumps(exito.PESOS))


def test_investigacion_demo():
    r = cliente.post("/api/investigacion",
                     json={"keyword": "bamboo kitchen", "demo": True})
    d = r.json()
    assert d["nicho"]["ok"] is True and "listing" in d


def test_subida_cerebro_rechaza_no_csv():
    r = cliente.post("/api/archivos/cerebro",
                     files={"file": ("malo.exe", b"xx", "application/o")})
    assert r.json()["ok"] is False


def test_subida_cerebro_csv():
    r = cliente.post("/api/archivos/cerebro",
                     files={"file": ("t.csv", b"Keyword Phrase,Search Volume\na,1",
                                     "text/csv")})
    d = r.json()
    assert d["ok"] is True and os.path.isfile(d["csv_path"])


# ---------------------- productos / ventas / alertas ---------------------- #
def test_productos_crud():
    alta = cliente.post("/portfolio/producto",
                        json={"nombre": "Test API", "costo": 2.0, "flete": 0.5,
                              "arancel_pct": 5, "prep": 0.3,
                              "techo_demanda": 100}).json()
    assert alta["ok"] is True
    pid = alta["id"]
    lst = cliente.get("/api/productos").json()["productos"]
    assert any(p["id"] == pid for p in lst)
    upd = cliente.put(f"/api/productos/{pid}", json={"costo": 3.0}).json()
    assert upd["ok"] is True
    baja = cliente.delete(f"/api/productos/{pid}").json()
    assert baja["ok"] is True
    lst2 = cliente.get("/api/productos").json()["productos"]
    assert not any(p["id"] == pid for p in lst2)


def test_ventas_y_alertas():
    r = cliente.post("/api/ventas",
                     json={"asin": "B0TESTAPI1", "unidades": 3, "precio": 24.0,
                           "neto_unitario": 6.9})
    assert r.status_code == 200 and r.json()["neto"] == 20.7
    a = cliente.get("/api/alertas").json()
    assert "alertas" in a       # la venta genero una alerta en el outbox


# ---------------------- ayuda / asistente ---------------------- #
def test_tutorial_idiomas():
    for idi in ("es", "en", "pt"):
        d = cliente.get("/api/tutorial", params={"idioma": idi}).json()
        _igual(d["secciones"], tutorial.secciones(idi))
        assert len(d["secciones"]) == 13


def test_tutorial_buscar():
    d = cliente.get("/api/tutorial",
                    params={"idioma": "en", "buscar": "recommender"}).json()
    assert d["secciones"][0]["clave"] == "recomendador"


def test_glosario():
    d = cliente.get("/api/glosario").json()
    assert set(d["categorias"].keys()) == set(g for g in glosario.CATEGORIAS)
    b = cliente.get("/api/glosario", params={"buscar": "ROI"}).json()
    assert any(x["termino"] == "ROI" for x in b["resultados"])


def test_asistente_estado_y_programa_offline():
    assert cliente.get("/api/asistente/estado").status_code == 200
    # sin clave => modo offline responde desde el manual, nunca 500
    r = cliente.post("/api/asistente/programa",
                     json={"pregunta": "como uso el recomendador?",
                           "idioma": "es"})
    assert r.status_code == 200 and r.json()["texto"]


# ---------------------- publicar / creativos ---------------------- #
def test_publicar_demo():
    r = cliente.post("/api/publicar",
                     json={"nombre": "bamboo kitchen set", "costo": 2.1,
                           "flete": 0.8, "arancel_pct": 6, "prep": 0.5,
                           "demo": True})
    d = r.json()
    assert "paquete" in d and "<html" in d["html"].lower()


def test_creativos_kit():
    r = cliente.post("/api/creativos/kit",
                     json={"titulo": "Set Bambu", "bullets": ["Eco", "12pz"]})
    d = r.json()["imagenes_b64"]
    assert d, "kit vacio"
    import base64
    primera = next(v for v in d.values() if isinstance(v, str) and len(v) > 100)
    assert base64.b64decode(primera)[:8] == b"\x89PNG\r\n\x1a\n"


def _correr_sin_pytest():
    import traceback
    fallos = 0
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    for nombre, fn in tests:
        try:
            fn()
            print(f"ok    {nombre}")
        except Exception:
            fallos += 1
            print(f"FALLO {nombre}")
            traceback.print_exc()
    print(f"\n{len(tests) - fallos}/{len(tests)} tests OK")
    return fallos


if __name__ == "__main__":
    sys.exit(_correr_sin_pytest())
