#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
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
from typing import Annotated

_AQUI = os.path.dirname(os.path.abspath(__file__))
if _AQUI not in sys.path:
    sys.path.insert(0, _AQUI)

from fastapi import APIRouter, Body, Query, Response, UploadFile
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

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
class _Entrada(BaseModel):
    """Base de los modelos con campos numericos que alimentan los motores de
    calculo (pricing, caja, inversores, ventas...).

    allow_inf_nan=False: sin esto, mandar "Infinity"/"-Infinity"/"NaN" en un
    campo float PASA la validacion ge=0 (inf >= 0 es True) y despues desborda
    el motor -> el resultado es inf -> FastAPI muere al serializarlo a JSON
    ("Out of range float values are not JSON compliant") -> HTTP 500. Peor:
    en /api/ventas (el unico que ESCRIBE en la base) la fila con precio=inf se
    PERSISTIA antes de fallar la serializacion, y a partir de ahi /dashboard
    quedaba roto con 500 permanente hasta limpiar la fila a mano. Con esto,
    inf/nan se rechazan en el parseo -> 422 con el campo señalado, igual que
    cualquier otro valor invalido. El motor nunca ve un no-finito."""
    model_config = ConfigDict(allow_inf_nan=False)


# Cotas SUPERIORES de dominio. allow_inf_nan corta inf/nan, pero un input
# FINITO extremo (precio=1e308, capital=1e308) sigue desbordando el motor a inf
# al multiplicarse -> 500 al serializar (y en /api/ventas, fila inf PERSISTIDA
# -> dashboard roto). Estos techos son absurdamente amplios para FBA (un
# operador real no maneja mil millones de dolares ni diez millones de unidades
# por mes), asi que no rechazan ningun valor legitimo: solo cierran el
# desborde. Con precio<=1e9 y unidades<=1e7, el peor producto es 1e16, lejos
# del limite de float (1.8e308).
MAX_USD = 1e9            # cualquier campo en dolares (capital, precio, costo, ticket, aporte)
MAX_UNID = 10_000_000    # unidades/mes (techo de demanda, unidades de una venta)
MAX_PROD = 1000          # cantidad de productos en un portafolio/escenario


def _no_denormal(v: float) -> float:
    """El landed cost es un DIVISOR: `int(budget // landed)` en caja y
    `total_cap / (landed * pipeline)` en inversores. Un landed positivo pero
    absurdamente chico (1e-300) hace desbordar la division a inf ->
    int(inf) lanza OverflowError -> 500. landed=0 sigue siendo valido (el
    motor lo trata como "sin costo": 0 unidades, no divide); un costo real de
    sourcing es de centavos como minimo. Este validador solo rechaza la franja
    imposible 0 < landed < 1e-6, no toca ningun valor legitimo."""
    if 0 < v < 1e-6:
        raise ValueError("costo por unidad demasiado chico: usá 0 o un número realista")
    return v


# Un costo por unidad (landed): 0 o un valor realista, nunca un denormal que
# desborde la division. Se usa via Annotated para no repetir el validador.
Landed = Annotated[float, AfterValidator(_no_denormal)]


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


class RecomendadorIn(_Entrada):
    # A diferencia de PricingIn/CajaIn (que limitan plata), esto limita TRABAJO:
    # _pasada_amplia hace una request HTTP de autocompletado de Amazon POR
    # CADA seed, con un sleep entre cada una -- y el endpoint es sincrono,
    # asi que unas pocas requests con seeds/max_seeds grandes agotan el
    # threadpool de Starlette y cuelgan el servidor entero para el usuario
    # real. shortlist ademas gasta tokens PAGOS de Keepa/Jungle Scout por
    # candidato si estan conectados: sin techo, una sola request (local, LAN,
    # o disparada por una pagina de terceros si el CORS estuviera abierto)
    # puede drenar en minutos la cuota mensual que el usuario paga de su
    # bolsillo. Los topes (20) son generosos frente a los defaults (8/12/10):
    # no cambian ningun uso normal, solo cortan el caso sin sentido.
    precio_min: float = Field(10.0, le=MAX_USD)
    precio_max: float = Field(50.0, le=MAX_USD)
    marketplace: str = "US"
    seeds: list[str] | None = Field(None, max_length=20)
    max_seeds: int = Field(8, ge=1, le=20)
    shortlist: int = Field(12, ge=1, le=20)
    top_n: int = Field(10, ge=1, le=20)
    usar_keepa: bool = True
    demo: bool = False


class PricingIn(_Entrada):
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
    costo: float = Field(0.0, ge=0, le=MAX_USD)
    flete: float = Field(0.0, ge=0, le=MAX_USD)
    arancel_pct: float = Field(0.0, ge=0, le=MAX_USD)
    prep: float = Field(0.0, ge=0, le=MAX_USD)
    fba_fee: float | None = Field(None, ge=0, le=MAX_USD)
    # El codigo ya ignora una competencia <= 0 (ver pricing.evaluar), asi que
    # ge=0 no cambia ningun comportamiento valido: solo rechaza el disparate.
    precio_competencia: float | None = Field(None, ge=0, le=MAX_USD)
    # Margen objetivo en PORCENTAJE (config.TARGET_MARGIN = 25.0, no 0.25).
    # Un margen >= 100% es imposible por definicion -- el margen es una parte
    # del precio -- y hace que precio_objetivo() no pueda converger.
    margen_obj: float | None = Field(None, ge=0, lt=100)


class CajaIn(_Entrada):
    # Mismo criterio que PricingIn: los imposibles se rechazan en la frontera,
    # el motor (agents/capital_planner.py) NO se toca.
    #
    # QUE PASABA: sell_through=-1 devolvia HTTP 200 con "vendidas": -1488896
    # -- un millon y medio de unidades NEGATIVAS -- porque
    #   vendidas = min(int(round(disponible * sell_through)), disponible, techo)
    # y el min() se queda con ese negativo gigante. techo_demanda=-50 daba
    # "vendidas": -50. Numeros imposibles presentados como una proyeccion real,
    # que es justo lo que el techo de demanda existe para evitar.
    budget: float = Field(..., ge=0, le=MAX_USD)
    landed: Landed = Field(..., ge=0, le=MAX_USD)
    precio: float = Field(..., ge=0, le=MAX_USD)
    # net_unit SIN limite inferior a proposito: un neto negativo es un caso
    # legitimo a modelar (vender a perdida para liquidar stock), no un error.
    net_unit: float = Field(..., ge=-MAX_USD, le=MAX_USD)
    # Fracciones, no porcentajes (default 0.5 = 50%, 0.05 = 5%): el motor hace
    # `disponible * sell_through` y `1 - devoluciones`.
    sell_through: float = Field(0.5, ge=0, le=1)
    devoluciones: float = Field(0.05, ge=0, le=1)
    lead_time_meses: int = Field(2, ge=0)
    payout_delay_meses: int = Field(1, ge=0)
    techo_demanda: int = Field(290, ge=0, le=MAX_UNID)
    # meses=100000 generaba 100.000 filas en una sola request (memoria y CPU
    # por una entrada sin sentido). 120 = 10 años, de sobra para una
    # proyeccion de caja; abajo de 1 no hay nada que proyectar.
    meses: int = Field(12, ge=1, le=120)


class EscenarioInversorIn(_Entrada):
    # capital_propio negativo daba "unidades_mes": -455 y "facturacion":
    # -10909; techo=-1 daba "facturacion": -24. Facturacion negativa no existe.
    capital_propio: float = Field(..., ge=0, le=MAX_USD)
    n_productos: int = Field(1, ge=1, le=MAX_PROD)
    techo: int = Field(290, ge=0, le=MAX_UNID)
    precio: float = Field(24.0, ge=0, le=MAX_USD)
    net_unit: float = Field(6.9, ge=-MAX_USD, le=MAX_USD)  # puede ser negativo (ver CajaIn)
    landed: Landed = Field(5.5, ge=0, le=MAX_USD)
    capital_inversor: float = Field(0.0, ge=0, le=MAX_USD)
    # Comision del inversor sobre la facturacion que financia su capital: una
    # parte de la facturacion, nunca mas del 100% ni negativa.
    pct_facturacion: float = Field(10.0, ge=0, le=100)
    pipeline_meses: int = Field(4, ge=1)


class RetornoInversorIn(_Entrada):
    ticket: float = Field(1000.0, ge=0, le=MAX_USD)
    pct_facturacion: float = Field(10.0, ge=0, le=100)
    techo: int = Field(290, ge=0, le=MAX_UNID)
    precio: float = Field(24.0, ge=0, le=MAX_USD)
    landed: Landed = Field(5.5, ge=0, le=MAX_USD)
    meses: int = Field(24, ge=1, le=120)
    productos_financia: float = Field(1.0, ge=0, le=MAX_PROD)
    pipeline_meses: int = Field(4, ge=1)
    devoluciones: float = Field(0.05, ge=0, le=1)
    mes_arranque: int = Field(2, ge=1)


class InteresCompuestoIn(_Entrada):
    # Este era el peor de la familia: no devolvia un numero raro, CRASHEABA.
    # anios=10000 hacia desbordar el capital a inf, y FastAPI moria al
    # serializar con "ValueError: Out of range float values are not JSON
    # compliant" -> HTTP 500 con stack trace. De paso generaba 120.000 filas.
    # tasa_anual_pct=1e12 producia el mismo inf ya con 50 años.
    #
    # Los topes se eligieron VERIFICANDO que el peor caso permitido siga
    # dando un float finito: aporte 1e9 + 1e9/mes al 1000% durante 50 años
    # da 6.48e61, que serializa bien.
    aporte_inicial: float = Field(..., ge=0, le=MAX_USD)
    aporte_periodico: float = Field(0.0, ge=0, le=MAX_USD)
    # Una tasa negativa es un escenario legitimo (un mal año); no se puede
    # perder mas del 100% del capital en un periodo. El techo de 1000% anual
    # (10x por año) ya es absurdo de sobra para una proyeccion real.
    tasa_anual_pct: float = Field(60.0, ge=-100, le=1000)
    anios: int = Field(5, ge=1, le=50)
    techo_capital: float = Field(0.0, ge=0, le=MAX_USD)
    frecuencia: str = "mensual"


class PlanPortafolioIn(_Entrada):
    # objetivo_mensual=-3000 devolvia 200 con "alcanzado": True -- decia que
    # un objetivo de sueldo NEGATIVO estaba cumplido.
    objetivo_mensual: float = Field(..., ge=0, le=MAX_USD)
    capital_propio: float = Field(..., ge=0, le=MAX_USD)
    techo: int = Field(290, ge=0, le=MAX_UNID)
    precio: float = Field(24.0, ge=0, le=MAX_USD)
    net_unit: float = Field(6.9, ge=-MAX_USD, le=MAX_USD)  # puede ser negativo (ver CajaIn)
    usar_inversores: bool = False
    pct_comision: float = Field(5.0, ge=0, le=100)


class ChatIn(BaseModel):
    pregunta: str
    historial: list[dict] | None = None
    idioma: str = "es"


class ProductoUpdateIn(_Entrada):
    # Los mismos ge=0 que PricingIn: este es el OTRO camino que alimenta el
    # motor de pricing (editar un producto guardado), y sin los limites
    # aceptaba costo=-999 -> el analisis mostraba landed=-1057 y precio=-2107,
    # un precio negativo presentado como resultado valido. La validacion tiene
    # que ser la misma en los dos caminos que llegan al mismo motor.
    nombre: str | None = None
    asin: str | None = None
    costo: float | None = Field(None, ge=0, le=MAX_USD)
    flete: float | None = Field(None, ge=0, le=MAX_USD)
    arancel_pct: float | None = Field(None, ge=0, le=MAX_USD)
    prep: float | None = Field(None, ge=0, le=MAX_USD)
    fba_fee: float | None = Field(None, ge=0, le=MAX_USD)
    precio_competencia: float | None = Field(None, ge=0, le=MAX_USD)
    techo_demanda: int | None = Field(None, ge=0, le=MAX_UNID)
    notas: str | None = None
    activo: int | None = None


class PublicarIn(_Entrada):
    nombre: str
    costo: float = Field(0.0, ge=0, le=MAX_USD)
    flete: float = Field(0.0, ge=0, le=MAX_USD)
    arancel_pct: float = Field(0.0, ge=0, le=MAX_USD)
    prep: float = Field(0.0, ge=0, le=MAX_USD)
    fba_fee: float | None = Field(None, ge=0, le=MAX_USD)
    precio_competencia: float | None = Field(None, ge=0, le=MAX_USD)
    techo_demanda: int = Field(290, ge=0, le=MAX_UNID)
    usar_motor_propio: bool = True
    demo: bool = False


class KitCreativoIn(BaseModel):
    titulo: str
    bullets: list[str] = []


class VentaIn(_Entrada):
    # El unico de la familia que ESCRIBE EN LA BASE: unidades=-500 creaba una
    # fila real con ingreso -12000 y mandaba un mail diciendo "Vendiste -500
    # unidades de ...". Eso no es una respuesta rara que se descarta: queda
    # guardado y ensucia la analitica de ventas para siempre.
    #
    # No hay concepto de devolucion/reembolso en agents/analytics.py (solo
    # `ingreso = unidades * precio`), asi que una venta negativa no es una
    # funcion no documentada -- es entrada sin validar.
    asin: str
    unidades: int = Field(..., ge=1, le=MAX_UNID)  # una venta de 0 unidades no es una venta
    precio: float = Field(..., ge=0, le=MAX_USD)  # 0 = muestra/regalo, es real
    # neto_unitario SIN limite INFERIOR (vender a perdida es legitimo); el
    # techo evita que unidades*neto desborde y se guarde inf en la base.
    neto_unitario: float = Field(..., ge=-MAX_USD, le=MAX_USD)
    pais: str = "US"
    segmento: str = "general"
    product_id: int | None = None


class StockIn(_Entrada):
    # Stock y lead time NEGATIVOS no existen fisicamente; sin ge=0 se
    # persistian igual (stock=-999, lead_time=-50) y despues la proyeccion de
    # caja/inventario los tomaba como validos.
    stock: int = Field(..., ge=0)
    lead_time_dias: int | None = Field(None, ge=0)


class PoaIn(BaseModel):
    motivo: str = ""
    tipo: str = "otro"
    idioma: str = "es"


class BsrIn(_Entrada):
    # Antes era Body(dict) sin tipar: mandar bsr como lista/objeto/bool
    # llegaba crudo a data_bsr.estimar() -> parsear_bloque() hacia
    # operaciones de string sobre un tipo inesperado -> HTTP 500. Tipado como
    # str|float, un tipo que no sea eso da 422. El frontend manda un string
    # (el bloque de texto pegado de Amazon); un BSR numerico suelto tambien
    # sirve (estimar() acepta int/float).
    bsr: str | float | None = None
    categoria: str | None = None


class VendedoresTextoIn(_Entrada):
    # Igual que BsrIn: era Body(dict) sin tipar y un texto no-string reventaba
    # vendedores_principales(). El frontend manda {"texto": "<un competidor
    # por linea>"}.
    texto: str = ""


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
CSV_MAX_BYTES = 20 * 1024 * 1024   # 20 MB: de sobra para un export de keywords/productos


class ArchivoDemasiadoGrande(Exception):
    pass


async def _leer_csv_limitado(file):
    """Lee un UploadFile en chunks, cortando ANTES de volcar mas de
    CSV_MAX_BYTES a memoria/disco.

    POR QUE EXISTE: file.read() sin tope no tenia ningun limite de tamaño --
    un archivo gigante (repetido) podia llenar el disco del usuario. Content-
    Length no es confiable (lo pone el cliente), asi que se corta leyendo de
    a partes reales, no confiando en un header."""
    partes, total = [], 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > CSV_MAX_BYTES:
            raise ArchivoDemasiadoGrande()
        partes.append(chunk)
    return b"".join(partes)


def _csv_seguro(csv_path):
    """Reduce cualquier `csv_path` que llegue del cliente a un NOMBRE de
    archivo dentro de CEREBRO_CSV_DIR -- nunca una ruta.

    POR QUE EXISTE: InvestigacionIn.csv_path viaja del cliente sin ninguna
    validacion hasta cerebro_con_estado() -> open(). El upload legitimo
    (POST /archivos/cerebro, ariba) ya sanea el NOMBRE con este mismo regex,
    asi que el csv_path que manda el panel para un archivo que el subio
    siempre queda igual con esto. Lo que se cierra es el otro camino: alguien
    mandando "../../../../etc/passwd" o una ruta absoluta a cualquier archivo
    del disco y leyendo su contenido a traves del mensaje de error (las
    columnas que no matchean se devuelven en la respuesta)."""
    if not csv_path:
        return None
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(csv_path))
    return os.path.join(config.CEREBRO_CSV_DIR, nombre) if nombre else None


@router.post("/archivos/cerebro")
async def subir_cerebro(file: UploadFile):
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "cerebro.csv")
    if not nombre.lower().endswith(".csv"):
        return {"ok": False, "mensaje": "Solo se aceptan archivos .csv de Cerebro."}
    try:
        contenido = await _leer_csv_limitado(file)
    except ArchivoDemasiadoGrande:
        return {"ok": False, "mensaje": f"El archivo supera el máximo de "
                                        f"{CSV_MAX_BYTES // 1024 // 1024} MB."}
    os.makedirs(config.CEREBRO_CSV_DIR, exist_ok=True)
    destino = os.path.join(config.CEREBRO_CSV_DIR, nombre)
    with open(destino, "wb") as f:
        f.write(contenido)
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
    try:
        contenido = await _leer_csv_limitado(file)
    except ArchivoDemasiadoGrande:
        return {"ok": False, "productos": [], "ventas_estim_total": 0,
                "ventas_estim_lider": 0,
                "mensaje": f"El archivo supera el máximo de "
                          f"{CSV_MAX_BYTES // 1024 // 1024} MB."}
    os.makedirs(config.CEREBRO_CSV_DIR, exist_ok=True)
    destino = os.path.join(config.CEREBRO_CSV_DIR, nombre)
    with open(destino, "wb") as f:
        f.write(contenido)
    return helium_productos.vendedores_desde_csv(destino)


@router.post("/investigacion")
def investigacion(i: InvestigacionIn):
    ruta = _csv_seguro(i.csv_path)
    mi = market_intel(i.keyword, i.marketplace, csv_path=ruta, demo=i.demo)
    out = {"nicho": mi}
    if mi["ok"] and i.con_listing:
        out["listing"] = generar_listing(i.keyword, i.marketplace,
                                         csv_path=ruta, demo=i.demo)
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
def mercado_vendedores(body: VendedoresTextoIn):
    """Vendedores principales de un nicho SIN ninguna API paga.

    El cliente manda {"texto": "<un competidor por linea, con ASIN y BSR>"} y
    devuelve cada uno con sus ventas/mes estimadas por la curva del BSR, su
    cuota entre los pegados y el ingreso/mes estimado. Las lineas sin BSR se
    listan sin numero: no se inventa nada."""
    return data_mercado.vendedores_principales(body.texto)


@router.post("/mercado/bsr")
def mercado_bsr(body: BsrIn):
    """Convierte un BSR publico de Amazon en ventas/mes estimadas (gratis)."""
    return data_bsr.estimar(body.bsr, body.categoria)


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
def pricing_acos(
        # Query float sin cotas aceptaba "Infinity"/"nan" -> inf en la
        # respuesta -> 500 al serializar. Las cotas finitas (absurdamente
        # anchas para un porcentaje real) rechazan inf con 422; nan falla la
        # comparacion ge/le y tambien da 422.
        margen_actual_pct: float = Query(..., ge=-1e6, le=1e6),
        margen_minimo_pct: float = Query(..., ge=-1e6, le=1e6),
        acos_supuesto_pct: float | None = Query(None, ge=0, le=1e6)):
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
def plan_pitch(
        # Cotas finitas: sin ellas, ?ticket=Infinity embebia "$inf" en el HTML
        # del pitch, y ?meses=1000000 generaba una sola respuesta de ~11 MB
        # (una fila por mes). meses topado en 120 = 10 años, igual que
        # CajaIn/RetornoInversorIn; el resto ge=0 con techo amplio.
        ticket: float = Query(1000, ge=0, le=1e9),
        pct: float = Query(10.0, ge=0, le=100),
        techo: int = Query(290, ge=0, le=1_000_000),
        precio: float = Query(24.0, ge=0, le=1e9),
        landed: float = Query(5.5, ge=0, le=1e9),
        meses: int = Query(24, ge=1, le=120),
        productos_financia: float = Query(1.0, ge=0, le=1e6)):
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
def productos_estimar_ventas(pid: int, body: BsrIn | None = None):
    """Estima las ventas/mes de mercado del producto y las guarda en su ficha.

    Fuentes, en orden: Jungle Scout, Keepa, y -- GRATIS, sin ninguna API -- el
    BSR publico de la pagina de Amazon que mande el cliente en el body
    ({"bsr": "#1,234 in Home & Kitchen"} o {"bsr": 1234, "categoria": "..."}).
    El body es OPCIONAL: sin el, usa las APIs (Jungle Scout/Keepa) por ASIN.
    Sin ASIN, sin clave y sin BSR: avisa y no inventa un numero. Sigue tipado
    (BsrIn) para que un bsr que no sea str/float de 422, no 500."""
    return productos.estimar_ventas(pid, bsr=body.bsr if body else None,
                                    categoria=body.categoria if body else None)


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
