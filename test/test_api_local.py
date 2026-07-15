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
from agents import recomendador  # noqa: E402
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


def test_owner_autoactivacion():
    """Build owner: con owner_licencia.json presente, estado() auto-activa via
    el server (mockeado). Sin el archivo, es un no-op (build normal)."""
    # sin archivo -> no-op, no toca la red
    licencia._owner_intentado = False
    assert licencia.intentar_activacion_owner() is False

    # con archivo + validacion server OK (mockeada) -> queda activada
    ruta_orig, validar_orig = licencia.RUTA_OWNER, licencia.validar_clave
    tmp_owner = os.path.join(_TMP, "owner_licencia.json")
    with open(tmp_owner, "w", encoding="utf-8") as f:
        json.dump({"email": "owner@test.com", "clave": "MVFBA-XXXX-XXXX-XXXX-XXXX"}, f)
    try:
        licencia.RUTA_OWNER = tmp_owner
        licencia.validar_clave = lambda e, c: True   # simula el OK del servidor
        licencia._owner_intentado = False
        assert licencia.intentar_activacion_owner() is True
        assert licencia.tiene_licencia() is True
        assert licencia.estado()["licencia"] is True
    finally:
        licencia.RUTA_OWNER, licencia.validar_clave = ruta_orig, validar_orig
        licencia._owner_intentado = False
        # limpia la activacion en la DB compartida para no filtrar estado
        licencia.db.execute("UPDATE registro SET clave_licencia=NULL, fecha_activacion=NULL")
        os.remove(tmp_owner)


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


def test_demanda_nativa_demo():
    r = cliente.get("/api/demanda", params={"keyword": "bamboo kitchen", "demo": True})
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert 0 <= d["demanda_score"] <= 100
    assert d["nivel"] in ("MUY ALTA", "ALTA", "MEDIA", "BAJA", "NULA")
    from data import demanda_nativa
    _igual(d, demanda_nativa.estimar_demanda("bamboo kitchen", demo=True))


def test_demanda_comparar_demo():
    r = cliente.post("/api/demanda/comparar",
                     json={"keywords": ["bamboo kitchen", "yoga mat", "dog bed"],
                           "demo": True})
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True and len(d["ranking"]) == 3
    # viene ordenado desc por score
    scores = [x["demanda_score"] for x in d["ranking"]]
    assert scores == sorted(scores, reverse=True)


def test_cerebro_acepta_jungle_scout_csv(tmp_path=None):
    # el parser de CSV debe aceptar columnas de Jungle Scout, no solo Helium 10
    from data.cerebro import parse_cerebro_csv
    import tempfile
    d = tempfile.mkdtemp()
    js = os.path.join(d, "js.csv")
    with open(js, "w", encoding="utf-8") as f:
        f.write("Keyword,Estimated Exact Search Volume,Competitor Products\n"
                "yoga mat,45000,1200\n")
    kws = parse_cerebro_csv(js)
    assert len(kws) == 1 and kws[0].search_volume == 45000.0


def test_marketplaces():
    r = cliente.get("/api/marketplaces")
    codigos = [m["codigo"] for m in r.json()["marketplaces"]]
    assert "US" in codigos and "BR" in codigos
    assert all("mid" not in m for m in r.json()["marketplaces"])


def test_recomendador_demo():
    import config
    orig = config.ANTHROPIC_API_KEY
    try:
        config.ANTHROPIC_API_KEY = ""  # offline: rapido y deterministico
        r = cliente.post("/api/recomendador/escanear",
                         json={"demo": True, "precio_min": 15, "precio_max": 45,
                               "top_n": 5})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True and len(d["oportunidades"]) <= 5
        # narrativa_ia siempre viaja (passthrough, mismo criterio que /api/exito)
        assert "narrativa_ia" in d and d["narrativa_ia"]["texto"]
    finally:
        config.ANTHROPIC_API_KEY = orig


def test_recomendador_narrativa_top_offline():
    """Sin ANTHROPIC_API_KEY, narrativa_top devuelve un resumen deterministico
    del top 1 -- nunca vacio, nunca lanza."""
    import config
    orig = config.ANTHROPIC_API_KEY
    try:
        config.ANTHROPIC_API_KEY = ""
        oport = [{"nicho": "test niche", "potencial": 70, "veredicto": "VERDE",
                  "comentario": "candidato fuerte"}]
        n = recomendador.narrativa_top(oport, "US", 15, 40)
        assert n["modo"] == "offline" and "test niche" in n["texto"]
    finally:
        config.ANTHROPIC_API_KEY = orig


def test_recomendador_narrativa_top_online_mockeado():
    """Con ANTHROPIC_API_KEY seteada, narrativa_top llama al cliente de
    anthropic (mockeado aca, sin red real) y devuelve modo online con el
    texto que "respondio" Claude, tal cual."""
    import config
    import types

    class _Bloque:
        def __init__(self, texto):
            self.type = "text"
            self.text = texto

    class _Respuesta:
        def __init__(self, texto):
            self.content = [_Bloque(texto)]

    class _Mensajes:
        def create(self, **kwargs):
            return _Respuesta("el nicho ganador es test niche porque si")

    class _Anthropic:
        def __init__(self, api_key):
            self.messages = _Mensajes()

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.Anthropic = _Anthropic

    orig_key = config.ANTHROPIC_API_KEY
    orig_mod = sys.modules.get("anthropic")
    try:
        config.ANTHROPIC_API_KEY = "sk-test-fake"
        sys.modules["anthropic"] = fake_anthropic
        oport = [{"nicho": "test niche", "potencial": 70, "veredicto": "VERDE",
                  "comentario": "candidato fuerte"}]
        n = recomendador.narrativa_top(oport, "US", 15, 40)
        assert n["modo"] == "online"
        assert n["texto"] == "el nicho ganador es test niche porque si"
    finally:
        config.ANTHROPIC_API_KEY = orig_key
        if orig_mod is not None:
            sys.modules["anthropic"] = orig_mod
        else:
            sys.modules.pop("anthropic", None)


def test_recomendador_detecta_jungle_scout_sin_keepa():
    """Bugfix: con Jungle Scout conectado (sin Keepa), la Pasada 2 real se
    activa igual -- antes solo miraba KEEPA_API_KEY y estos usuarios se
    quedaban con el proxy gratis aunque data/mercado.py ya sepa usar JS."""
    import config
    from data import mercado, motor_propio as mp
    orig_js_key, orig_js_name, orig_keepa, orig_anthropic = (
        config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME, config.KEEPA_API_KEY,
        config.ANTHROPIC_API_KEY)
    orig_prod_estrella, orig_sugerencias = mercado.productos_estrella, mp.sugerencias
    try:
        config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME = "k", "n"
        config.KEEPA_API_KEY = ""
        config.ANTHROPIC_API_KEY = ""  # offline: no hace falta pegarle a Anthropic para este test
        mp.sugerencias = lambda prefix, timeout=10, marketplace="US": [f"{prefix} pro"]
        canned = {"ok": True, "fuente": "Jungle Scout", "productos": [
            {"asin": "B0X", "titulo": "t", "precio": 22.0, "bsr": 3000,
             "ventas_estim": 900, "rating": 4.5, "resenas": 500,
             "link": "", "link_resenas": ""}]}
        mercado.productos_estrella = lambda *a, **k: canned
        r = recomendador.escanear_oportunidades(
            precio_min=15, precio_max=40, marketplace="US",
            seeds=["kitchen utensils"], max_seeds=1, shortlist=1, top_n=1, demo=False)
        assert r["ok"] is True
        assert r["oportunidades"][0]["n_competidores"] == 1
        assert r["oportunidades"][0]["fuente_precio"] == "Jungle Scout"
        assert "datos reales" in r["fuente"]
    finally:
        (config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME,
         config.KEEPA_API_KEY, config.ANTHROPIC_API_KEY) = (
            orig_js_key, orig_js_name, orig_keepa, orig_anthropic)
        mercado.productos_estrella, mp.sugerencias = orig_prod_estrella, orig_sugerencias


def test_exito_demo_con_narrativa():
    import config
    orig = config.ANTHROPIC_API_KEY
    try:
        config.ANTHROPIC_API_KEY = ""  # offline: rapido y deterministico
        r = cliente.get("/api/exito", params={"keyword": "bamboo", "demo": True,
                                              "precio": 24.0,
                                              "con_narrativa": True})
        d = r.json()
        assert d["evaluacion"]["ok"] is True
        assert "narrativa" in d and d["narrativa"]["texto"]
        assert d["pesos"] == json.loads(json.dumps(exito.PESOS))
    finally:
        config.ANTHROPIC_API_KEY = orig


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


# ---------------------- jungle scout (BYOK) ---------------------- #
def test_jungle_sin_clave_estado_vacio_honesto():
    from data import jungle_scout, mercado
    # estado honesto sin claves + productos_estrella cae a links libres (intacto)
    assert jungle_scout.estado()["ok"] is False
    r = mercado.productos_estrella("garlic press", 10, 50)
    assert r["ok"] is False and r["fuente"] == "sin_clave"
    assert len(r["links_amazon"]) >= 2       # los links gratis siempre estan
    # passthrough del endpoint: sin clave devuelve el mismo estado honesto
    api = cliente.get("/api/jungle/keywords", params={"termino": "garlic press"})
    assert api.status_code == 200
    _igual(api.json(), jungle_scout.keywords_por_termino("garlic press"))
    assert api.json()["ok"] is False


def test_jungle_mapeo_y_preferencia(monkeypatch=None):
    """Con claves + red mockeada: buscar_productos/keywords mapean el shape
    esperado, y productos_estrella prefiere Jungle Scout sobre Keepa."""
    import config
    from data import jungle_scout, mercado
    prod_json = {"data": [{"attributes": {
        "asin": "B0JS000001", "title": "JS garlic press pro", "price": 21.5,
        "category_rank": 4200, "approximate_30_day_units_sold": 900,
        "rating": 4.6, "reviews": 1800}}]}
    kw_json = {"data": [{"attributes": {
        "name": "garlic press", "monthly_search_volume_exact": 40500,
        "competed_products": 3000}}]}
    orig = (config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME, jungle_scout._post)
    try:
        config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME = "k", "n"
        jungle_scout._post = lambda ruta, cuerpo, timeout=30: (
            kw_json if "keywords" in ruta else prod_json)
        bp = jungle_scout.buscar_productos("garlic press", 10, 50)
        assert bp["ok"] and bp["productos"][0]["asin"] == "B0JS000001"
        assert bp["productos"][0]["ventas_estim"] == 900
        kw = jungle_scout.keywords_por_termino("garlic press")
        assert kw["ok"] and kw["keywords"][0]["volumen"] == 40500
        # productos_estrella prefiere Jungle Scout (sin Keepa configurado)
        pe = mercado.productos_estrella("garlic press", 10, 50)
        assert pe["ok"] and pe["fuente"] == "Jungle Scout"
    finally:
        config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME, jungle_scout._post = orig


def test_jungle_endpoints_avanzados_sin_clave():
    """Los 4 endpoints nuevos (keywords-asin, ventas-historicas,
    volumen-historico, sov) devuelven estado vacio honesto sin claves y no
    inventan datos."""
    from data import jungle_scout
    assert jungle_scout.keywords_por_asin("B0X")["ok"] is False
    assert jungle_scout.ventas_historicas_asin("B0X")["ok"] is False
    assert jungle_scout.volumen_historico("garlic press")["ok"] is False
    assert jungle_scout.share_of_voice("garlic press")["ok"] is False
    for ruta, params in [
        ("/api/jungle/keywords-asin", {"asin": "B0X"}),
        ("/api/jungle/ventas-historicas", {"asin": "B0X"}),
        ("/api/jungle/volumen-historico", {"keyword": "garlic press"}),
        ("/api/jungle/sov", {"keyword": "garlic press"}),
    ]:
        r = cliente.get(ruta, params=params)
        assert r.status_code == 200 and r.json()["ok"] is False


def test_jungle_volumen_historico_estacionalidad():
    """Con red mockeada, volumen_historico arma la serie y deriva el mejor mes."""
    import config
    from data import jungle_scout
    js_json = {"data": [
        {"attributes": {"estimate_start_date": "2025-11-03", "estimated_exact_search_volume": 9000}},
        {"attributes": {"estimate_start_date": "2025-11-10", "estimated_exact_search_volume": 8000}},
        {"attributes": {"estimate_start_date": "2025-06-02", "estimated_exact_search_volume": 1000}},
    ]}
    orig = (config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME, jungle_scout._post)
    try:
        config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME = "k", "n"
        jungle_scout._post = lambda ruta, cuerpo, timeout=30: js_json
        r = jungle_scout.volumen_historico("garlic press")
        assert r["ok"] and len(r["serie"]) == 3
        assert r["estacionalidad"]["mejor_mes"] == "noviembre"
        assert r["estacionalidad"]["volumen_total"] == 18000
    finally:
        config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME, jungle_scout._post = orig


def test_jungle_ventas_historicas_precio():
    """Con red mockeada, ventas_historicas_asin mapea unidades + precio diarios."""
    import config
    from data import jungle_scout
    js_json = {"data": [
        {"attributes": {"date": "2026-07-01", "estimated_units_sold": 30, "estimated_price": 19.99}},
        {"attributes": {"date": "2026-07-02", "estimated_units_sold": 25, "estimated_price": 21.99}},
    ]}
    orig = (config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME, jungle_scout._get)
    try:
        config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME = "k", "n"
        jungle_scout._get = lambda ruta, params=None, timeout=25: js_json
        r = jungle_scout.ventas_historicas_asin("B0X", dias=30)
        assert r["ok"] and r["resumen"]["unidades_total"] == 55
        assert r["resumen"]["precio_min"] == 19.99 and r["resumen"]["precio_max"] == 21.99
        # el wrapper de compat reusa el mismo camino
        assert jungle_scout.ventas_asin("B0X")["ventas_estim"] == 55
    finally:
        config.JUNGLE_SCOUT_API_KEY, config.JUNGLE_SCOUT_KEY_NAME, jungle_scout._get = orig


def test_inventario_restock_pronostico():
    """Con un producto + stock + ventas reales, el panel pronostica quiebre,
    cuando pedir y cuanto reponer. Sin stock/ventas, estado honesto."""
    from agents import inventario, productos, analytics
    from core import db
    asin = "B0RESTOCK1"
    alta = productos.guardar(nombre="Restock test", asin=asin, costo=2.0,
                             flete=0.5, arancel_pct=5, prep=0.3, techo_demanda=100)
    pid = alta["id"]
    try:
        # sin stock cargado -> honesto
        p0 = next(i for i in inventario.panel()["items"] if i["id"] == pid)
        assert p0["estado"] == "sin_ventas"  # todavia sin ventas
        analytics.registrar_venta(asin, 60, 20.0, 6.0, alertar=False)
        # con ventas pero sin stock cargado
        p1 = next(i for i in inventario.panel()["items"] if i["id"] == pid)
        assert p1["estado"] == "sin_stock" and p1["velocidad_diaria"] > 0
        # cargamos stock -> pronostico real
        r = inventario.set_stock(pid, 30, lead_time_dias=45)
        assert r["ok"] and r["stock"] == 30
        p2 = next(i for i in inventario.panel()["items"] if i["id"] == pid)
        assert p2["estado"] in ("rojo", "amarillo", "verde")
        assert p2["cantidad_sugerida"] >= 0 and "fecha_quiebre" in p2
        assert "capital_reposicion" in p2
        # endpoint passthrough
        api = cliente.get("/api/inventario/panel").json()
        assert api["ok"] and any(i["id"] == pid for i in api["items"])
        assert set(("n_reponer", "capital_reposicion_total")) <= set(api["resumen"])
    finally:
        db.execute("DELETE FROM orders WHERE asin=?", (asin,))
        db.execute("DELETE FROM products WHERE id=?", (pid,))


def test_inventario_set_stock_validacion():
    from agents import inventario
    assert inventario.set_stock(999999, 10)["ok"] is False  # producto inexistente
    assert inventario.set_stock("x", "y")["ok"] is False     # no numerico


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
