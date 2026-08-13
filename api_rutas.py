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

from fastapi import APIRouter, Body, Response, UploadFile
from pydantic import BaseModel, Field

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
from agents import inventario
from agents import portafolio as agente_portafolio
from agents import productos
from agents import publicador
from agents import poa as agente_poa
from agents import pricing
from agents import recomendador
from agents import tutorial
from agents.capital_planner import escenario_inversor, proyeccion_realista
from agents.listing import generar as generar_listing
from agents.market_intel import market_intel
from data import demanda_nativa
from data import jungle_scout
from data import modelos_ia
from data import bsr as data_bsr
from data import helium_productos
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
    # extra="allow" para no repetir aca la lista de proveedores de IA: las
    # claves y el modelo elegido de cada uno salen de config.PROVEEDORES_IA
    # (ANTHROPIC_API_KEY, ANTHROPIC_MODEL, GROK_API_KEY, ...). Agregar un
    # proveedor no obliga a tocar tambien este modelo. Lo que se acepta de
    # verdad lo decide config.CLAVES_GUARDABLES: guardar_env() descarta
    # cualquier cosa fuera de esa whitelist, asi que abrir el modelo no abre
    # la escritura del .env.
    model_config = {"extra": "allow"}

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
    # Todo lo que entra aca es plata o un porcentaje de costo: nada puede ser
    # negativo. Sin estos limites, un error de tipeo del usuario (-50 en vez de
    # 50) devolvia HTTP 200 con "precio: -90.0" y un semaforo en rojo, o sea un
    # numero imposible presentado como un resultado valido. Eso choca de frente
    # con la regla del proyecto: si el dato no sirve, se avisa, no se inventa un
    # resultado. Con ge=0 la API contesta 422 diciendo cual campo esta mal.
    #
    # El limite va ACA (frontera de la API) y no en agents/pricing.py a
    # proposito: la formula de pricing no se toca. landed_cost() sigue siendo
    # la misma; lo unico que cambia es que ya no se la llama con basura.
    costo: float = Field(0.0, ge=0)
    flete: float = Field(0.0, ge=0)
    arancel_pct: float = Field(0.0, ge=0)
    prep: float = Field(0.0, ge=0)
    fba_fee: float | None = Field(None, ge=0)
    # El codigo ya ignora una competencia <= 0 (ver pricing.evaluar), asi que
    # ge=0 no cambia ningun comportamiento valido: solo rechaza el disparate.
    precio_competencia: float | None = Field(None, ge=0)
    # Margen objetivo en PORCENTAJE (config.TARGET_MARGIN = 25.0, no 0.25).
    # Un margen >= 100% es imposible por definicion -- el margen es una parte
    # del precio -- y hace que precio_objetivo() no pueda converger.
    margen_obj: float | None = Field(None, ge=0, lt=100)


class CajaIn(BaseModel):
    # Mismo criterio que PricingIn: los imposibles se rechazan en la frontera,
    # el motor (agents/capital_planner.py) NO se toca.
    #
    # QUE PASABA: sell_through=-1 devolvia HTTP 200 con "vendidas": -1488896
    # -- un millon y medio de unidades NEGATIVAS -- porque
    #   vendidas = min(int(round(disponible * sell_through)), disponible, techo)
    # y el min() se queda con ese negativo gigante. techo_demanda=-50 daba
    # "vendidas": -50. Numeros imposibles presentados como una proyeccion real,
    # que es justo lo que el techo de demanda existe para evitar.
    budget: float = Field(..., ge=0)
    landed: float = Field(..., ge=0)
    precio: float = Field(..., ge=0)
    # net_unit SIN limite inferior a proposito: un neto negativo es un caso
    # legitimo a modelar (vender a perdida para liquidar stock), no un error.
    net_unit: float
    # Fracciones, no porcentajes (default 0.5 = 50%, 0.05 = 5%): el motor hace
    # `disponible * sell_through` y `1 - devoluciones`.
    sell_through: float = Field(0.5, ge=0, le=1)
    devoluciones: float = Field(0.05, ge=0, le=1)
    lead_time_meses: int = Field(2, ge=0)
    payout_delay_meses: int = Field(1, ge=0)
    techo_demanda: int = Field(290, ge=0)
    # meses=100000 generaba 100.000 filas en una sola request (memoria y CPU
    # por una entrada sin sentido). 120 = 10 años, de sobra para una
    # proyeccion de caja; abajo de 1 no hay nada que proyectar.
    meses: int = Field(12, ge=1, le=120)


class EscenarioInversorIn(BaseModel):
    # capital_propio negativo daba "unidades_mes": -455 y "facturacion":
    # -10909; techo=-1 daba "facturacion": -24. Facturacion negativa no existe.
    capital_propio: float = Field(..., ge=0)
    n_productos: int = Field(1, ge=1)
    techo: int = Field(290, ge=0)
    precio: float = Field(24.0, ge=0)
    net_unit: float = 6.9          # puede ser negativo (ver CajaIn)
    landed: float = Field(5.5, ge=0)
    capital_inversor: float = Field(0.0, ge=0)
    # Comision del inversor sobre la facturacion que financia su capital: una
    # parte de la facturacion, nunca mas del 100% ni negativa.
    pct_facturacion: float = Field(10.0, ge=0, le=100)
    pipeline_meses: int = Field(4, ge=1)


class RetornoInversorIn(BaseModel):
    ticket: float = Field(1000.0, ge=0)
    pct_facturacion: float = Field(10.0, ge=0, le=100)
    techo: int = Field(290, ge=0)
    precio: float = Field(24.0, ge=0)
    landed: float = Field(5.5, ge=0)
    meses: int = Field(24, ge=1, le=120)
    productos_financia: float = Field(1.0, ge=0)
    pipeline_meses: int = Field(4, ge=1)
    devoluciones: float = Field(0.05, ge=0, le=1)
    mes_arranque: int = Field(2, ge=1)


class InteresCompuestoIn(BaseModel):
    # Este era el peor de la familia: no devolvia un numero raro, CRASHEABA.
    # anios=10000 hacia desbordar el capital a inf, y FastAPI moria al
    # serializar con "ValueError: Out of range float values are not JSON
    # compliant" -> HTTP 500 con stack trace. De paso generaba 120.000 filas.
    # tasa_anual_pct=1e12 producia el mismo inf ya con 50 años.
    #
    # Los topes se eligieron VERIFICANDO que el peor caso permitido siga
    # dando un float finito: aporte 1e9 + 1e9/mes al 1000% durante 50 años
    # da 6.48e61, que serializa bien.
    aporte_inicial: float = Field(..., ge=0)
    aporte_periodico: float = Field(0.0, ge=0)
    # Una tasa negativa es un escenario legitimo (un mal año); no se puede
    # perder mas del 100% del capital en un periodo. El techo de 1000% anual
    # (10x por año) ya es absurdo de sobra para una proyeccion real.
    tasa_anual_pct: float = Field(60.0, ge=-100, le=1000)
    anios: int = Field(5, ge=1, le=50)
    techo_capital: float = Field(0.0, ge=0)
    frecuencia: str = "mensual"


class PlanPortafolioIn(BaseModel):
    # objetivo_mensual=-3000 devolvia 200 con "alcanzado": True -- decia que
    # un objetivo de sueldo NEGATIVO estaba cumplido.
    objetivo_mensual: float = Field(..., ge=0)
    capital_propio: float = Field(..., ge=0)
    techo: int = Field(290, ge=0)
    precio: float = Field(24.0, ge=0)
    net_unit: float = 6.9          # puede ser negativo (ver CajaIn)
    usar_inversores: bool = False
    pct_comision: float = Field(5.0, ge=0, le=100)


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
    # El unico de la familia que ESCRIBE EN LA BASE: unidades=-500 creaba una
    # fila real con ingreso -12000 y mandaba un mail diciendo "Vendiste -500
    # unidades de ...". Eso no es una respuesta rara que se descarta: queda
    # guardado y ensucia la analitica de ventas para siempre.
    #
    # No hay concepto de devolucion/reembolso en agents/analytics.py (solo
    # `ingreso = unidades * precio`), asi que una venta negativa no es una
    # funcion no documentada -- es entrada sin validar.
    asin: str
    unidades: int = Field(..., ge=1)      # una venta de 0 unidades no es una venta
    precio: float = Field(..., ge=0)      # 0 = muestra/regalo, es real
    # neto_unitario SIN limite: vender a perdida es un caso legitimo.
    neto_unitario: float
    pais: str = "US"
    segmento: str = "general"
    product_id: int | None = None


class StockIn(BaseModel):
    stock: int
    lead_time_dias: int | None = None


class PoaIn(BaseModel):
    motivo: str = ""
    tipo: str = "otro"
    idioma: str = "es"


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


def _proveedores_ia():
    """Los proveedores de IA tal como los necesita el panel: ficha + si ya
    tiene clave cargada + que modelo esta usando hoy."""
    return [{"codigo": p["codigo"], "nombre": p["nombre"],
             "clave_env": p["clave_env"], "modelo_env": p["modelo_env"],
             "tiene_clave": bool(config.clave_ia(p["codigo"])),
             "modelo": config.modelo_ia(p["codigo"])}
            for p in config.PROVEEDORES_IA]


@router.get("/config")
def config_get():
    estado = config.estado_config()
    # El modelo elegido NO es un secreto (es "gpt-4o-mini", no una clave) y el
    # panel lo necesita en claro para que el selector arranque donde debe. Va
    # el modelo EFECTIVO (el default cuando el usuario nunca eligio uno), que
    # es el que se usa de verdad al preguntar — no el "" del .env vacio.
    modelos_env = {p["modelo_env"]: config.modelo_ia(p["codigo"])
                   for p in config.PROVEEDORES_IA}
    claves = {k: (config.mask(config.env(k)) if k in config.CLAVES_SECRETAS
                  else modelos_env.get(k, config.env(k)))
              for k in config.CLAVES_GUARDABLES}
    return {**estado, "claves": claves, "ia_provider": config.IA_PROVIDER,
            "proveedores_ia": _proveedores_ia(),
            "modelos_ia": modelos_ia.disponibles(),
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


@router.post("/config/modelos")
def config_modelos_actualizar():
    """Boton "Actualizar modelos": le pregunta a cada proveedor con clave
    cargada que modelos ofrece HOY, con la clave del propio usuario. Los que
    no tienen clave se saltan (no hay a quien preguntarle)."""
    return modelos_ia.actualizar()


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


@router.post("/mercado/vendedores-csv")
async def subir_vendedores_csv(file: UploadFile):
    """Vendedores principales desde un export de PRODUCTOS que ya pagas.

    Acepta Helium 10 Xray/Black Box y Jungle Scout Product Database. Resuelve el
    hueco que el BSR pegado a mano no cubre: DESCUBRIR que ASINs compiten en el
    nicho, sin ninguna API. Si el export trae ventas propias se usan esas
    (calibradas); si solo trae BSR, se convierte con la curva."""
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "productos.csv")
    if not nombre.lower().endswith(".csv"):
        return {"ok": False, "productos": [], "ventas_estim_total": 0,
                "ventas_estim_lider": 0,
                "mensaje": "Solo se aceptan archivos .csv exportados de Helium 10 "
                           "(Xray/Black Box) o de Jungle Scout."}
    os.makedirs(config.CEREBRO_CSV_DIR, exist_ok=True)
    destino = os.path.join(config.CEREBRO_CSV_DIR, nombre)
    with open(destino, "wb") as f:
        f.write(await file.read())
    return helium_productos.vendedores_desde_csv(destino)


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


@router.get("/jungle/keywords-asin")
def jungle_keywords_asin(asin: str, max_n: int = 20):
    """Keywords por las que indexa un ASIN (Keywords by ASIN) via Jungle Scout."""
    return jungle_scout.keywords_por_asin(asin, max_n=max_n)


@router.get("/jungle/ventas-historicas")
def jungle_ventas_historicas(asin: str, dias: int = 30):
    """Ventas y precio diarios de un ASIN (Sales Estimates con rango) via Jungle Scout."""
    return jungle_scout.ventas_historicas_asin(asin, dias=dias)


@router.get("/jungle/volumen-historico")
def jungle_volumen_historico(keyword: str, meses: int = 12):
    """Volumen de busqueda semanal historico + estacionalidad (mejor mes) via Jungle Scout."""
    return jungle_scout.volumen_historico(keyword, meses=meses)


@router.get("/jungle/sov")
def jungle_sov(keyword: str):
    """Share of Voice de una keyword (marcas que dominan la pagina) via Jungle Scout."""
    return jungle_scout.share_of_voice(keyword)


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


@router.post("/mercado/vendedores")
def mercado_vendedores(body: dict = Body(default=None)):
    """Vendedores principales de un nicho SIN ninguna API paga.

    El cliente manda {"texto": "<un competidor por linea, con ASIN y BSR>"} y
    devuelve cada uno con sus ventas/mes estimadas por la curva del BSR, su
    cuota entre los pegados y el ingreso/mes estimado. Las lineas sin BSR se
    listan sin numero: no se inventa nada."""
    return data_mercado.vendedores_principales((body or {}).get("texto"))


@router.post("/mercado/bsr")
def mercado_bsr(body: dict = Body(default=None)):
    """Convierte un BSR publico de Amazon en ventas/mes estimadas (gratis)."""
    datos = body or {}
    return data_bsr.estimar(datos.get("bsr"), datos.get("categoria"))


@router.get("/exito")
def exito_get(keyword: str, precio: float | None = None,
              margen_pct: float | None = None, demo: bool = False,
              con_narrativa: bool = False):
    comp = None
    if demo:
        r = data_mercado.productos_estrella(keyword, 10, 50, demo=True)
        comp = data_mercado.resumen_competencia(r["productos"])
    elif config.KEEPA_API_KEY or (config.JUNGLE_SCOUT_API_KEY and config.JUNGLE_SCOUT_KEY_NAME):
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


@router.post("/productos/{pid}/estimar-ventas")
def productos_estimar_ventas(pid: int, body: dict = Body(default=None)):
    """Estima las ventas/mes de mercado del producto y las guarda en su ficha.

    Fuentes, en orden: Jungle Scout, Keepa, y -- GRATIS, sin ninguna API -- el
    BSR publico de la pagina de Amazon que mande el cliente en el body
    ({"bsr": "#1,234 in Home & Kitchen"} o {"bsr": 1234, "categoria": "..."}).
    Sin ASIN, sin clave y sin BSR: avisa y no inventa un numero."""
    datos = body or {}
    return productos.estimar_ventas(pid, bsr=datos.get("bsr"),
                                    categoria=datos.get("categoria"))


@router.post("/ventas")
def ventas_registrar(v: VentaIn):
    from agents import analytics
    return analytics.registrar_venta(v.asin, v.unidades, v.precio,
                                     v.neto_unitario, pais=v.pais,
                                     segmento=v.segmento,
                                     product_id=v.product_id)


@router.get("/inventario/panel")
def inventario_panel():
    """Pronostico de reabastecimiento del portafolio (restock estilo Sellerboard):
    cuando quiebra el stock, cuando pedir y cuanto reponer, con velocidad real."""
    return inventario.panel()


@router.post("/inventario/stock/{pid}")
def inventario_set_stock(pid: int, s: StockIn):
    """Carga/actualiza el stock actual (unidades) y el lead time (dias) de un producto."""
    return inventario.set_stock(pid, s.stock, lead_time_dias=s.lead_time_dias)


@router.get("/poa/tipos")
def poa_tipos():
    """Tipos de motivo de suspension para el generador de Plan de Accion."""
    return {"tipos": agente_poa.TIPOS}


@router.post("/poa")
def poa_generar(p: PoaIn):
    """Genera un borrador de Plan de Accion (POA) para una suspension de Amazon.
    Con clave de IA lo redacta Claude; sin clave, plantilla deterministica util."""
    return agente_poa.generar(p.motivo, tipo=p.tipo, idioma=p.idioma)


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
