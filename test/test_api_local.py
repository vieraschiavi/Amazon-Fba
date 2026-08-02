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
    assert r2.json()["vigente"] is True     # demo de 7 dias recien arrancada


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


def test_poa_offline_y_endpoint():
    """POA sin clave de IA: plantilla deterministica con las 3 secciones, en el
    idioma pedido, con texto no vacio. Nunca lanza."""
    import config
    orig = config.ANTHROPIC_API_KEY
    try:
        config.ANTHROPIC_API_KEY = ""
        tipos = cliente.get("/api/poa/tipos").json()["tipos"]
        assert "autenticidad" in tipos
        r = cliente.post("/api/poa", json={"motivo": "caja abierta",
                                           "tipo": "condicion", "idioma": "en"}).json()
        assert r["ok"] and r["modo"] == "offline" and len(r["secciones"]) == 3
        assert all(s["titulo"] and s["puntos"] for s in r["secciones"])
        assert r["texto"] and r["nota"]
    finally:
        config.ANTHROPIC_API_KEY = orig


def test_poa_online_mockeado():
    """Con clave + anthropic mockeado, el POA usa el JSON que devuelve Claude."""
    import config, sys, types
    class _Bloque:
        def __init__(self, t): self.type = "text"; self.text = t
    class _Resp:
        content = [_Bloque('{"secciones":[{"titulo":"A","puntos":["x"]},'
                           '{"titulo":"B","puntos":["y"]},{"titulo":"C","puntos":["z"]}]}')]
    class _Msgs:
        def create(self, **k): return _Resp()
    class _Anthropic:
        def __init__(self, api_key): self.messages = _Msgs()
    fake = types.ModuleType("anthropic"); fake.Anthropic = _Anthropic
    from agents import poa
    orig_key, orig_mod = config.ANTHROPIC_API_KEY, sys.modules.get("anthropic")
    try:
        config.ANTHROPIC_API_KEY = "sk-fake"; sys.modules["anthropic"] = fake
        r = poa.generar("motivo", "autenticidad", "es")
        assert r["modo"] == "online" and [s["titulo"] for s in r["secciones"]] == ["A", "B", "C"]
    finally:
        config.ANTHROPIC_API_KEY = orig_key
        if orig_mod is not None: sys.modules["anthropic"] = orig_mod
        else: sys.modules.pop("anthropic", None)


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


def test_estimar_ventas_sin_asin_no_inventa():
    """Sin ASIN no hay forma real de estimar: avisa y NO guarda un numero."""
    from agents import productos
    alta = productos.guardar(nombre="Sin ASIN", asin="", costo=2.0, flete=0.5,
                             arancel_pct=5, prep=0.3, techo_demanda=100)
    pid = alta["id"]
    r = productos.estimar_ventas(pid)
    assert r["ok"] is False and "ASIN" in r["mensaje"]
    fila = productos.listar(solo_activos=False)
    p = next(x for x in fila if x["id"] == pid)
    assert p.get("ventas_estim_mes") is None      # nada inventado, nada guardado


def test_estimar_ventas_jungle_scout_se_guarda_en_ficha():
    """Con Jungle Scout conectado, la ventas reales por ASIN se estiman Y se
    guardan en la ficha, con fuente y fecha (auditable)."""
    import config
    from agents import productos
    from data import jungle_scout
    alta = productos.guardar(nombre="Con JS", asin="B0ESTIMJS1", costo=2.0,
                             flete=0.5, arancel_pct=5, prep=0.3, techo_demanda=100)
    pid = alta["id"]
    orig = jungle_scout.ventas_asin
    try:
        jungle_scout.ventas_asin = lambda asin, timeout=25: {
            "ok": True, "asin": asin, "ventas_estim": 480}
        r = productos.estimar_ventas(pid)
        assert r["ok"] and r["ventas_estim_mes"] == 480
        assert r["ventas_estim_fuente"] == "Jungle Scout" and r["ventas_estim_fecha"]
        # persistido en la ficha, lo lee listar()
        p = next(x for x in productos.listar() if x["id"] == pid)
        assert p["ventas_estim_mes"] == 480
        assert p["ventas_estim_fuente"] == "Jungle Scout"
        assert p["ventas_estim_fecha"] is not None
    finally:
        jungle_scout.ventas_asin = orig


def test_estimar_ventas_cae_a_keepa_si_no_hay_jungle():
    """Sin Jungle Scout pero con Keepa, usa el BSR real (curva) y lo etiqueta."""
    from agents import productos
    from data import jungle_scout, keepa
    alta = productos.guardar(nombre="Solo Keepa", asin="B0ESTIMKP1", costo=2.0,
                             flete=0.5, arancel_pct=5, prep=0.3, techo_demanda=100)
    pid = alta["id"]
    ojs, okp = jungle_scout.ventas_asin, keepa.producto
    try:
        jungle_scout.ventas_asin = lambda asin, timeout=25: {
            "ok": False, "mensaje": "Falta clave Jungle Scout."}
        keepa.producto = lambda asin, timeout=25: {
            "ok": True, "asin": asin, "ventas_estim": 230, "fuente": "Keepa"}
        r = productos.estimar_ventas(pid)
        assert r["ok"] and r["ventas_estim_mes"] == 230
        assert r["ventas_estim_fuente"] == "Keepa (BSR)"
    finally:
        jungle_scout.ventas_asin, keepa.producto = ojs, okp


def test_estimar_ventas_sin_fuente_no_inventa():
    """Con ASIN pero sin ninguna clave, no se inventa: ok=False y nada guardado."""
    from agents import productos
    from data import jungle_scout, keepa
    alta = productos.guardar(nombre="Sin claves", asin="B0NOKEYS01", costo=2.0,
                             flete=0.5, arancel_pct=5, prep=0.3, techo_demanda=100)
    pid = alta["id"]
    ojs, okp = jungle_scout.ventas_asin, keepa.producto
    try:
        jungle_scout.ventas_asin = lambda asin, timeout=25: {"ok": False, "mensaje": "sin clave JS"}
        keepa.producto = lambda asin, timeout=25: {"ok": False, "mensaje": "sin clave Keepa"}
        r = productos.estimar_ventas(pid)
        assert r["ok"] is False and ("Jungle Scout" in r["mensaje"] or "Keepa" in r["mensaje"])
        p = next(x for x in productos.listar() if x["id"] == pid)
        assert p.get("ventas_estim_mes") is None
    finally:
        jungle_scout.ventas_asin, keepa.producto = ojs, okp


def test_run_rate_propio_necesita_historial_minimo():
    """El fallback GRATIS no extrapola con poco historial: 2 ventas de hoy NO
    son 60 u/mes. Sin dias suficientes devuelve None (no proyecta nada)."""
    from agents import productos, analytics
    asin = "B0RUNRATE1"
    productos.guardar(nombre="Run rate corto", asin=asin, costo=2.0, flete=0.5,
                      arancel_pct=5, prep=0.3, techo_demanda=100)
    analytics.registrar_venta(asin, 2, 20.0, 6.0, alertar=False)   # venta de HOY
    assert productos._run_rate_propio(asin) is None


def test_run_rate_propio_calcula_ritmo_real():
    """Con historial suficiente, el run-rate sale de las ventas REALES: 60
    unidades en 30 dias -> ~60 u/mes. Sin ninguna API."""
    from datetime import datetime, timedelta
    from agents import productos, analytics
    from core import db
    asin = "B0RUNRATE2"
    productos.guardar(nombre="Run rate largo", asin=asin, costo=2.0, flete=0.5,
                      arancel_pct=5, prep=0.3, techo_demanda=100)
    analytics.registrar_venta(asin, 60, 20.0, 6.0, alertar=False)
    # se envejece la orden 30 dias para simular historial real
    hace30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute("UPDATE orders SET fecha=? WHERE asin=?", (hace30, asin))
    r = productos._run_rate_propio(asin)
    assert r is not None
    assert r["unidades_total"] == 60 and 29 <= r["dias"] <= 31
    assert 55 <= r["unidades_mes"] <= 65      # ~60 u/mes


def test_estimar_ventas_fallback_sin_apis_usa_ventas_propias():
    """Sin Jungle Scout ni Keepa, cae al run-rate de ventas propias (gratis) y
    lo guarda en la ficha etiquetado como tal (no como dato de mercado)."""
    from datetime import datetime, timedelta
    from agents import productos, analytics
    from core import db
    from data import jungle_scout, keepa
    asin = "B0FALLBACK1"
    alta = productos.guardar(nombre="Fallback gratis", asin=asin, costo=2.0,
                             flete=0.5, arancel_pct=5, prep=0.3, techo_demanda=100)
    pid = alta["id"]
    analytics.registrar_venta(asin, 90, 20.0, 6.0, alertar=False)
    hace30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute("UPDATE orders SET fecha=? WHERE asin=?", (hace30, asin))
    ojs, okp = jungle_scout.ventas_asin, keepa.producto
    try:
        jungle_scout.ventas_asin = lambda a, timeout=25: {"ok": False, "mensaje": "sin JS"}
        keepa.producto = lambda a, timeout=25: {"ok": False, "mensaje": "sin Keepa"}
        r = productos.estimar_ventas(pid)
        assert r["ok"] is True
        assert 85 <= r["ventas_estim_mes"] <= 95          # ~90 u/mes reales
        assert r["ventas_estim_fuente"].startswith("Tus ventas")
        # persistido en la ficha
        p = next(x for x in productos.listar() if x["id"] == pid)
        assert p["ventas_estim_mes"] == r["ventas_estim_mes"]
    finally:
        jungle_scout.ventas_asin, keepa.producto = ojs, okp


def test_curva_bsr_no_cambio_al_moverla_a_su_modulo():
    """La curva se movio de data/keepa.py a data/bsr.py. REGRESION: sin
    categoria, el resultado tiene que ser IDENTICO al historico, porque
    data/mercado.py y el recomendador ya dependian de esos numeros."""
    from data.bsr import ventas_desde_bsr
    # Valores anclados de la curva historica (Home & Kitchen, factor 1.0).
    esperados = {100: 9000, 500: 3000, 1000: 1800, 5000: 500,
                 10000: 230, 50000: 45, 100000: 18, 500000: 3}
    for bsr, ventas in esperados.items():
        assert ventas_desde_bsr(bsr) == ventas, f"la curva cambio en BSR={bsr}"
    # fuera de rango y basura -> 0, nunca una invencion
    for malo in (0, -1, None, "x", ""):
        assert ventas_desde_bsr(malo) == 0
    # el clamp de los extremos se mantiene
    assert ventas_desde_bsr(1) == 9000 and ventas_desde_bsr(9_000_000) == 3


def test_bsr_parsea_el_bloque_real_de_amazon():
    """Pegar el bloque tal cual sale en Amazon tiene que dar el BSR de la
    categoria PRINCIPAL, no el de la subcategoria."""
    from data import bsr
    bloque = ("Best Sellers Rank: #1,234 in Home & Kitchen "
              "(See Top 100 in Home & Kitchen)\n    #5 in Cutting Boards")
    r = bsr.estimar(bloque)
    assert r["ok"] is True
    # #5 daria una estimacion disparatada: tiene que quedarse con 1.234
    assert r["bsr"] == 1234, "tomo el rank de subcategoria en vez del principal"
    assert r["categoria"] == "Home & Kitchen"
    assert r["ventas_estim"] > 0
    # el precio pegado al lado no se cuela dentro de la categoria
    r2 = bsr.estimar("#1,234 in Home & Kitchen   $24.99")
    assert r2["categoria"] == "Home & Kitchen"
    # numero suelto y formato español
    assert bsr.estimar("4500")["bsr"] == 4500
    assert bsr.estimar("nº1.234 en Hogar y cocina")["bsr"] == 1234


def test_bsr_no_inventa_cuando_no_puede_leer():
    """Sin BSR legible NO hay estimacion: ok=False, ventas=None."""
    from data import bsr
    for basura in ("", "   ", "hola que tal", "sin numeros aca"):
        r = bsr.estimar(basura)
        assert r["ok"] is False and r["ventas_estim"] is None


def test_bsr_factor_por_categoria_ordena_bien():
    """Mismo BSR en una categoria grande vende mas que en una chica."""
    from data.bsr import ventas_desde_bsr
    grande = ventas_desde_bsr(1000, "Clothing, Shoes & Jewelry")
    base = ventas_desde_bsr(1000)
    chica = ventas_desde_bsr(1000, "Musical Instruments")
    assert grande > base > chica
    # una categoria desconocida NO inventa un factor: cae en la curva base
    assert ventas_desde_bsr(1000, "Categoria Que No Existe") == base


def test_estimar_ventas_gratis_por_bsr_de_producto_que_no_vendo():
    """EL CASO DE USO REAL: un ASIN que nunca vendi y sin ninguna clave de API.
    Antes no habia numero. Ahora se estima pegando el BSR publico de Amazon."""
    from agents import productos
    from data import jungle_scout, keepa
    alta = productos.guardar(nombre="Competidor ajeno", asin="B0AJENO001",
                             costo=2.0, flete=0.5, arancel_pct=5, prep=0.3,
                             techo_demanda=100)
    pid = alta["id"]
    ojs, okp = jungle_scout.ventas_asin, keepa.producto
    try:
        jungle_scout.ventas_asin = lambda a, timeout=25: {"ok": False, "mensaje": "sin JS"}
        keepa.producto = lambda a, timeout=25: {"ok": False, "mensaje": "sin Keepa"}
        # sin BSR todavia no hay nada que estimar, y NO se inventa
        assert productos.estimar_ventas(pid)["ok"] is False
        # con el BSR pegado, si
        r = productos.estimar_ventas(
            pid, bsr="Best Sellers Rank: #1,234 in Home & Kitchen")
        assert r["ok"] is True
        assert r["ventas_estim_mes"] > 0
        assert r["ventas_estim_fuente"].startswith("BSR de Amazon")
        assert r["ventas_estim_confianza"] == "alta"
        # queda guardado en la ficha, con el BSR, para re-estimar y auditar
        p = next(x for x in productos.listar() if x["id"] == pid)
        assert p["ventas_estim_mes"] == r["ventas_estim_mes"]
        assert p["bsr"] == 1234 and p["bsr_categoria"] == "Home & Kitchen"
        # re-estimar sin volver a pegar nada reusa el BSR guardado
        r2 = productos.estimar_ventas(pid)
        assert r2["ok"] and r2["ventas_estim_mes"] == r["ventas_estim_mes"]
    finally:
        jungle_scout.ventas_asin, keepa.producto = ojs, okp


def test_estimar_ventas_bsr_ilegible_no_pisa_lo_guardado():
    """Si el BSR pegado no se entiende, se avisa y NO se toca la ficha."""
    from agents import productos
    from data import jungle_scout, keepa
    alta = productos.guardar(nombre="BSR ilegible", asin="B0ILEGIB01", costo=2.0,
                             flete=0.5, arancel_pct=5, prep=0.3, techo_demanda=100)
    pid = alta["id"]
    ojs, okp = jungle_scout.ventas_asin, keepa.producto
    try:
        jungle_scout.ventas_asin = lambda a, timeout=25: {"ok": False, "mensaje": "sin JS"}
        keepa.producto = lambda a, timeout=25: {"ok": False, "mensaje": "sin Keepa"}
        productos.estimar_ventas(pid, bsr="#900 in Home & Kitchen")
        antes = next(x for x in productos.listar() if x["id"] == pid)["ventas_estim_mes"]
        r = productos.estimar_ventas(pid, bsr="cualquier cosa")
        assert r["ok"] is False
        despues = next(x for x in productos.listar() if x["id"] == pid)["ventas_estim_mes"]
        assert despues == antes, "un BSR ilegible piso la estimacion buena"
    finally:
        jungle_scout.ventas_asin, keepa.producto = ojs, okp


def test_estimar_ventas_bsr_no_le_gana_a_jungle_scout():
    """El orden de fuentes importa: ventas reales de JS mandan sobre la curva."""
    from agents import productos
    from data import jungle_scout
    alta = productos.guardar(nombre="Orden fuentes", asin="B0ORDEN001", costo=2.0,
                             flete=0.5, arancel_pct=5, prep=0.3, techo_demanda=100)
    pid = alta["id"]
    orig = jungle_scout.ventas_asin
    try:
        jungle_scout.ventas_asin = lambda a, timeout=25: {
            "ok": True, "asin": a, "ventas_estim": 777}
        r = productos.estimar_ventas(pid, bsr="#1,234 in Home & Kitchen")
        assert r["ventas_estim_mes"] == 777
        assert r["ventas_estim_fuente"] == "Jungle Scout"
    finally:
        jungle_scout.ventas_asin = orig


def test_vendedores_principales_sin_api():
    """Vendedores principales pegando lo que se ve en Amazon, sin API."""
    from data.mercado import vendedores_principales
    bloque = (
        "B08XYZ1234  Bamboo cutting board  #1,234 in Home & Kitchen   $24.99\n"
        "B07ABC5678  Cutting board pro     #5,600 in Home & Kitchen   $19.99\n"
        "B09QWE1111  Eco board bundle      #18,900 in Home & Kitchen  $31.50\n"
        "B01NOBSR99  Sin rank a la vista                              $22.00\n")
    r = vendedores_principales(bloque)
    assert r["ok"] is True
    assert len(r["productos"]) == 4
    lider = r["productos"][0]
    assert lider["asin"] == "B08XYZ1234"          # ordenado por ventas desc
    assert lider["bsr"] == 1234 and lider["ventas_estim"] > 0
    assert lider["precio"] == 24.99
    assert lider["ingreso_estim_mes"] == round(lider["ventas_estim"] * 24.99, 2)
    # el ASIN no confunde al parser de BSR
    assert r["productos"][1]["bsr"] == 5600
    # la linea sin BSR se lista pero NO se le inventa un numero
    sin = [p for p in r["productos"] if p["asin"] == "B01NOBSR99"][0]
    assert sin["ventas_estim"] is None and sin["cuota_pct"] is None
    # las cuotas de los estimados suman ~100
    cuotas = [p["cuota_pct"] for p in r["productos"] if p["cuota_pct"]]
    assert abs(sum(cuotas) - 100.0) < 0.5
    assert r["ventas_estim_total"] == sum(
        p["ventas_estim"] for p in r["productos"] if p["ventas_estim"])
    # sin datos no inventa
    assert vendedores_principales("")["ok"] is False


def test_endpoints_bsr_y_vendedores():
    """Los dos endpoints nuevos == la funcion Python equivalente."""
    from data import bsr as bsr_mod
    from data.mercado import vendedores_principales
    bloque = "B08XYZ1234 #1,234 in Home & Kitchen $24.99\nB07ABC5678 #5,600 $19.99"
    api = cliente.post("/api/mercado/vendedores", json={"texto": bloque}).json()
    directo = vendedores_principales(bloque)
    assert api["ok"] == directo["ok"]
    assert api["ventas_estim_total"] == directo["ventas_estim_total"]
    assert [p["asin"] for p in api["productos"]] == [p["asin"] for p in directo["productos"]]

    api2 = cliente.post("/api/mercado/bsr",
                        json={"bsr": "#1,234 in Home & Kitchen"}).json()
    assert api2 == bsr_mod.estimar("#1,234 in Home & Kitchen")
    # basura por la API tampoco inventa
    assert cliente.post("/api/mercado/bsr", json={"bsr": "nada"}).json()["ok"] is False


def test_estimar_ventas_endpoint_passthrough():
    """POST /api/productos/{pid}/estimar-ventas == productos.estimar_ventas(pid)."""
    from agents import productos
    from data import jungle_scout
    alta = cliente.post("/portfolio/producto",
                        json={"nombre": "Endpoint estim", "asin": "B0ESTIMEP1",
                              "costo": 2.0, "flete": 0.5, "arancel_pct": 5,
                              "prep": 0.3, "techo_demanda": 100}).json()
    pid = alta["id"]
    orig = jungle_scout.ventas_asin
    try:
        jungle_scout.ventas_asin = lambda asin, timeout=25: {
            "ok": True, "asin": asin, "ventas_estim": 310}
        api = cliente.post(f"/api/productos/{pid}/estimar-ventas").json()
        assert api["ok"] and api["ventas_estim_mes"] == 310
        assert api["ventas_estim_fuente"] == "Jungle Scout"
    finally:
        jungle_scout.ventas_asin = orig


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
