#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api_rutas.py — Rutas /api/* del panel SaaS (frontend React).

Completa la API local (app.py) con TODO lo que el dashboard Streamlit hacia
inline, para que el frontend web pueda cubrir las 14 pestañas. Cada endpoint
es un passthrough fino a la funcion Python correspondiente (agents/, core/,
config): la response es el dict que ya devuelve esa funcion — aca no se
inventan formatos nuevos ni se duplica logica de negocio.

Los endpoints legacy de app.py (usados por n8n y mobile/) NO se tocan: este
router agrega el prefijo /api para el SPA y convive con ellos.
"""
import base64
import os
import re
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
if _AQUI not in sys.path:
    sys.path.insert(0, _AQUI)

from fastapi import APIRouter, Response, UploadFile
from pydantic import BaseModel

import config
import generar_pitch
from core import db
from core import demo_seed
from core import licencia
from core import prefs
from agents import asistente
from agents import creativos
from agents import exito
from agents import glosario
from agents import portafolio as agente_portafolio
from agents import productos
from agents import publicador
from agents import pricing
from agents import recomendador
from agents import tutorial
from agents.capital_planner import escenario_inversor, proyeccion_realista
from agents.listing import generar as generar_listing
from agents.market_intel import market_intel
from data import demanda_nativa
from data import jungle_scout
from data import mercado as data_mercado
from data import motor_propio

router = APIRouter(prefix="/api")


# ============================ modelos ============================ #
class RegistroIn(BaseModel):
    nombre: str = ""
    email: str


class ActivarIn(BaseModel):
    email: str
    clave: str


class PrefsIn(BaseModel):
    idioma: str | None = None
    producto_activo_id: str | None = None
    tema: str | None = None
    modo_demo: str | None = None


class ConfigIn(BaseModel):
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    IA_PROVIDER: str | None = None
    KEEPA_API_KEY: str | None = None
    JUNGLE_SCOUT_API_KEY: str | None = None
    JUNGLE_SCOUT_KEY_NAME: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASS: str | None = None
    ALERT_TO: str | None = None


class InvestigacionIn(BaseModel):
    keyword: str
    marketplace: str = "US"
    demo: bool = False
    csv_path: str | None = None
    con_listing: bool = True


class RecomendadorIn(BaseModel):
    precio_min: float = 10.0
    precio_max: float = 50.0
    marketplace: str = "US"
    seeds: list[str] | None = None
    max_seeds: int = 8
    shortlist: int = 12
    top_n: int = 10
    usar_keepa: bool = True
    demo: bool = False


class PricingIn(BaseModel):
    costo: float = 0.0
    flete: float = 0.0
    arancel_pct: float = 0.0
    prep: float = 0.0
    fba_fee: float | None = None
    precio_competencia: float | None = None
    margen_obj: float | None = None


class CajaIn(BaseModel):
    budget: float
    landed: float
    precio: float
    net_unit: float
    sell_through: float = 0.5
    devoluciones: float = 0.05
    lead_time_meses: int = 2
    payout_delay_meses: int = 1
    techo_demanda: int = 290
    meses: int = 12


class EscenarioInversorIn(BaseModel):
    capital_propio: float
    n_productos: int = 1
    techo: int = 290
    precio: float = 24.0
    net_unit: float = 6.9
    landed: float = 5.5
    capital_inversor: float = 0.0
    pct_facturacion: float = 10.0
    pipeline_meses: int = 4


class RetornoInversorIn(BaseModel):
    ticket: float = 1000.0
    pct_facturacion: float = 10.0
    techo: int = 290
    precio: float = 24.0
    landed: float = 5.5
    meses: int = 24
    productos_financia: float = 1.0
    pipeline_meses: int = 4
    devoluciones: float = 0.05
    mes_arranque: int = 2


class InteresCompuestoIn(BaseModel):
    aporte_inicial: float
    aporte_periodico: float = 0.0
    tasa_anual_pct: float = 60.0
    anios: int = 5
    frecuencia: str = "mensual"
    techo_capital: float = 0.0


class PlanPortafolioIn(BaseModel):
    objetivo_mensual: float
    capital_propio: float
    techo: int = 290
    precio: float = 24.0
    net_unit: float = 6.9
    usar_inversores: bool = False
    pct_comision: float = 5.0


class ChatIn(BaseModel):
    pregunta: str
    historial: list[dict] | None = None
    idioma: str = "es"


class ProductoUpdateIn(BaseModel):
    nombre: str | None = None
    asin: str | None = None
    costo: float | None = None
    flete: float | None = None
    arancel_pct: float | None = None
    prep: float | None = None
    fba_fee: float | None = None
    precio_competencia: float | None = None
    techo_demanda: int | None = None
    notas: str | None = None
    activo: int | None = None


class PublicarIn(BaseModel):
    nombre: str
    costo: float = 0.0
    flete: float = 0.0
    arancel_pct: float = 0.0
    prep: float = 0.0
    fba_fee: float | None = None
    precio_competencia: float | None = None
    techo_demanda: int = 290
    usar_motor_propio: bool = True
    demo: bool = False


class KitCreativoIn(BaseModel):
    titulo: str
    bullets: list[str] = []


class VentaIn(BaseModel):
    asin: str
    unidades: int
    precio: float
    neto_unitario: float
    pais: str = "US"
    segmento: str = "general"
    product_id: int | None = None


# ============================ licencia / demo ============================ #
@router.get("/licencia")
def licencia_estado():
    return licencia.estado()


@router.post("/licencia/registro")
def licencia_registro(r: RegistroIn):
    licencia.registrar(r.nombre, r.email)
    return licencia.estado()


@router.post("/licencia/activar")
def licencia_activar(a: ActivarIn):
    res = licencia.activar_licencia(a.email, a.clave)
    return {**res, "estado": licencia.estado()}


# ============================ prefs / config ============================ #
@router.get("/prefs")
def prefs_get():
    return prefs.obtener_todas()


@router.put("/prefs")
def prefs_put(p: PrefsIn):
    return prefs.guardar(**p.model_dump(exclude_none=True))


@router.get("/config")
def config_get():
    estado = config.estado_config()
    claves = {k: config.mask(config.env(k)) for k in config.CLAVES_GUARDABLES}
    return {**estado, "claves": claves, "ia_provider": config.IA_PROVIDER,
            "acos_pct": config.ACOS_PCT,
            "umbral_verde": config.UMBRAL_VERDE,
            "umbral_amarillo": config.UMBRAL_AMARILLO}


@router.post("/config")
def config_post(c: ConfigIn):
    return config.guardar_env(**c.model_dump(exclude_none=True))


@router.get("/config/conexiones")
def config_conexiones(asin: str | None = None):
    import test_conexiones
    return {"resultados": test_conexiones.verificar_todo(asin or None)}


@router.get("/demo/ejemplo")
def demo_ejemplo_estado():
    return {"cargado": demo_seed.hay_ejemplo()}


@router.post("/demo/ejemplo")
def demo_ejemplo_cargar():
    demo_seed.cargar_ejemplo()
    return {"cargado": True}


@router.delete("/demo/ejemplo")
def demo_ejemplo_quitar():
    demo_seed.quitar_ejemplo()
    return {"cargado": False}


# ============================ investigacion / mercado ============================ #
@router.post("/archivos/cerebro")
async def subir_cerebro(file: UploadFile):
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "cerebro.csv")
    if not nombre.lower().endswith(".csv"):
        return {"ok": False, "mensaje": "Solo se aceptan archivos .csv de Cerebro."}
    os.makedirs(config.CEREBRO_CSV_DIR, exist_ok=True)
    destino = os.path.join(config.CEREBRO_CSV_DIR, nombre)
    with open(destino, "wb") as f:
        f.write(await file.read())
    return {"ok": True, "csv_path": destino, "nombre": nombre}


@router.post("/investigacion")
def investigacion(i: InvestigacionIn):
    mi = market_intel(i.keyword, i.marketplace, csv_path=i.csv_path, demo=i.demo)
    out = {"nicho": mi}
    if mi["ok"] and i.con_listing:
        out["listing"] = generar_listing(i.keyword, i.marketplace,
                                         csv_path=i.csv_path, demo=i.demo)
    return out


@router.get("/motor/keywords")
def motor_keywords(seed: str, profundidad: int = 1, marketplace: str = "US",
                   demo: bool = False):
    res = motor_propio.investigar(seed, profundidad=profundidad, demo=demo,
                                  marketplace=marketplace)
    return res


@router.post("/investigacion/listing")
def investigacion_listing(i: InvestigacionIn):
    """Listing desde el motor propio (flujo 'Motor propio' de Investigacion)."""
    res = motor_propio.investigar(i.keyword, demo=i.demo, marketplace=i.marketplace)
    kws = motor_propio.keywords_cerebro(res) if res["ok"] else None
    return {"motor": res,
            "listing": generar_listing(i.keyword, i.marketplace, keywords=kws,
                                       demo=i.demo)}


@router.get("/demanda")
def demanda(keyword: str, marketplace: str = "US", demo: bool = False):
    """Demanda RELATIVA gratis (autocompletado Amazon, sin Keepa)."""
    return demanda_nativa.estimar_demanda(keyword, marketplace=marketplace, demo=demo)


@router.get("/jungle/keywords")
def jungle_keywords(termino: str, max_n: int = 20):
    """Volumen de busqueda REAL de keywords via Jungle Scout (BYOK). Sin clave
    devuelve estado vacio explicado (no inventa datos)."""
    return jungle_scout.keywords_por_termino(termino, max_n=max_n)


@router.get("/jungle/ventas")
def jungle_ventas(asin: str):
    """Estimacion de ventas mensuales de un ASIN via Jungle Scout (BYOK)."""
    return jungle_scout.ventas_asin(asin)


class CompararIn(BaseModel):
    keywords: list[str]
    marketplace: str = "US"
    demo: bool = False


@router.post("/demanda/comparar")
def demanda_comparar(c: CompararIn):
    """Rankea varios nichos por demanda relativa (gratis). Max 8 por request."""
    kws = [k.strip() for k in c.keywords if k.strip()][:8]
    return demanda_nativa.comparar(kws, marketplace=c.marketplace, demo=c.demo)


@router.get("/marketplaces")
def marketplaces():
    return {"marketplaces": [
        {"codigo": cod, **{k: v for k, v in d.items() if k != "mid"}}
        for cod, d in motor_propio.MARKETPLACES.items()]}


@router.post("/recomendador/escanear")
def recomendador_escanear(r: RecomendadorIn):
    return recomendador.escanear_oportunidades(
        precio_min=r.precio_min, precio_max=r.precio_max,
        marketplace=r.marketplace, seeds=r.seeds, max_seeds=r.max_seeds,
        shortlist=r.shortlist, top_n=r.top_n, usar_keepa=r.usar_keepa,
        demo=r.demo)


@router.get("/exito")
def exito_get(keyword: str, precio: float | None = None,
              margen_pct: float | None = None, demo: bool = False,
              con_narrativa: bool = False):
    comp = None
    if demo:
        r = data_mercado.productos_estrella(keyword, 10, 50, demo=True)
        comp = data_mercado.resumen_competencia(r["productos"])
    elif config.KEEPA_API_KEY:
        r = data_mercado.productos_estrella(keyword, 10, 50)
        if r["ok"]:
            comp = data_mercado.resumen_competencia(r["productos"])
    ev = exito.evaluar(keyword, competencia=comp, precio_objetivo=precio,
                       margen_pct=margen_pct)
    out = {"evaluacion": ev, "pesos": exito.PESOS}
    if con_narrativa:
        out["narrativa"] = exito.narrativa(ev, comp)
    return out


# ============================ finanzas ============================ #
@router.post("/pricing")
def pricing_post(p: PricingIn):
    prod = {"costo": p.costo, "flete": p.flete, "arancel_pct": p.arancel_pct,
            "prep": p.prep}
    return pricing.evaluar(prod, fba_fee=p.fba_fee,
                           precio_competencia=p.precio_competencia,
                           margen_obj=p.margen_obj)


@router.get("/pricing/acos")
def pricing_acos(margen_actual_pct: float, margen_minimo_pct: float,
                 acos_supuesto_pct: float | None = None):
    return {"acos_maximo": pricing.acos_bancable(margen_actual_pct,
                                                 margen_minimo_pct,
                                                 acos_supuesto_pct)}


@router.post("/caja/proyeccion")
def caja_proyeccion(c: CajaIn):
    return proyeccion_realista(c.budget, c.landed, c.precio, c.net_unit,
                               sell_through=c.sell_through,
                               devoluciones=c.devoluciones,
                               lead_time_meses=c.lead_time_meses,
                               payout_delay_meses=c.payout_delay_meses,
                               techo_demanda=c.techo_demanda, meses=c.meses)


@router.post("/inversores/escenario")
def inversores_escenario(e: EscenarioInversorIn):
    return escenario_inversor(e.capital_propio, e.n_productos, e.techo,
                              e.precio, e.net_unit, e.landed,
                              capital_inversor=e.capital_inversor,
                              pct_facturacion=e.pct_facturacion,
                              pipeline_meses=e.pipeline_meses)


@router.post("/inversores/retorno")
def inversores_retorno(r: RetornoInversorIn):
    return agente_portafolio.retorno_inversor(
        ticket=r.ticket, pct_facturacion=r.pct_facturacion, techo=r.techo,
        precio=r.precio, landed=r.landed, meses=r.meses,
        productos_financia=r.productos_financia,
        pipeline_meses=r.pipeline_meses, devoluciones=r.devoluciones,
        mes_arranque=r.mes_arranque)


@router.get("/plan/pitch")
def plan_pitch(ticket: float = 1000, pct: float = 10.0, techo: int = 290,
               precio: float = 24.0, landed: float = 5.5, meses: int = 24,
               productos_financia: float = 1.0):
    html = generar_pitch.html_pitch(ticket=ticket, pct=pct, techo=techo,
                                    precio=precio, landed=landed, meses=meses,
                                    productos_financia=productos_financia)
    return Response(content=html, media_type="text/html")


@router.post("/plan/interes-compuesto")
def plan_interes_compuesto(i: InteresCompuestoIn):
    return agente_portafolio.interes_compuesto(
        i.aporte_inicial, i.aporte_periodico, i.tasa_anual_pct, i.anios,
        frecuencia=i.frecuencia, techo_capital=i.techo_capital)


@router.post("/plan/portafolio")
def plan_portafolio(p: PlanPortafolioIn):
    return agente_portafolio.recomendar_portafolio(
        p.objetivo_mensual, p.capital_propio, techo=p.techo, precio=p.precio,
        net_unit=p.net_unit, usar_inversores=p.usar_inversores,
        pct_comision=p.pct_comision)


# ============================ productos / ventas / alertas ============================ #
@router.get("/productos")
def productos_listar(solo_activos: bool = True):
    return {"productos": productos.listar(solo_activos=solo_activos)}


@router.put("/productos/{pid}")
def productos_actualizar(pid: int, p: ProductoUpdateIn):
    return productos.actualizar(pid, **p.model_dump(exclude_none=True))


@router.delete("/productos/{pid}")
def productos_baja(pid: int):
    return productos.desactivar(pid)


@router.post("/ventas")
def ventas_registrar(v: VentaIn):
    from agents import analytics
    return analytics.registrar_venta(v.asin, v.unidades, v.precio,
                                     v.neto_unitario, pais=v.pais,
                                     segmento=v.segmento,
                                     product_id=v.product_id)


@router.get("/alertas")
def alertas(limit: int = 50):
    limit = max(1, min(int(limit), 500))
    filas = db.rows("SELECT fecha, asunto, para, enviado FROM alerts_outbox "
                    "ORDER BY id DESC LIMIT ?", (limit,))
    return {"alertas": filas}


# ============================ publicar / creativos ============================ #
@router.post("/publicar")
def publicar_post(p: PublicarIn):
    kws = None
    if p.usar_motor_propio:
        res = motor_propio.investigar(p.nombre, demo=p.demo)
        if res["ok"]:
            kws = motor_propio.keywords_cerebro(res)
    paq = publicador.paquete(p.nombre, costo=p.costo, flete=p.flete,
                             arancel_pct=p.arancel_pct, prep=p.prep,
                             fba_fee=p.fba_fee,
                             precio_competencia=p.precio_competencia,
                             techo_demanda=p.techo_demanda, keywords=kws,
                             demo=p.demo)
    return {"paquete": paq, "html": publicador.html_paquete(paq)}


@router.post("/creativos/kit")
def creativos_kit(k: KitCreativoIn):
    kit = creativos.kit_creativo(k.titulo, k.bullets)
    out = {}
    for nombre, png in kit.items():
        if isinstance(png, (bytes, bytearray)):
            out[nombre] = base64.b64encode(bytes(png)).decode("ascii")
        else:
            out[nombre] = png
    return {"imagenes_b64": out}


# ============================ asistente / ayuda ============================ #
@router.get("/asistente/estado")
def asistente_estado():
    return asistente.estado()


@router.post("/asistente/negocio")
def asistente_negocio(c: ChatIn):
    return asistente.responder(c.pregunta, c.historial)


@router.post("/asistente/programa")
def asistente_programa(c: ChatIn):
    return asistente.responder_programa(c.pregunta, c.historial,
                                        idioma=c.idioma)


@router.get("/tutorial")
def tutorial_get(idioma: str = "es", buscar: str = ""):
    if buscar.strip():
        return {"secciones": tutorial.buscar(buscar, idioma)}
    return {"secciones": tutorial.secciones(idioma)}


@router.get("/glosario")
def glosario_get(buscar: str = ""):
    if buscar.strip():
        return {"resultados": [
            {"termino": t, "definicion": d, "categoria": c}
            for t, d, c in glosario.buscar(buscar)]}
    return {"categorias": {
        cat: [{"termino": t, "definicion": d} for t, d in items]
        for cat, items in glosario.por_categoria().items()}}
