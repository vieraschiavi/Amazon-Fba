#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
app.py — API FastAPI de MV FBA IA (puente con n8n).
Endpoints: /health, /webhook/message, /webhook/sale, /run/research, /dashboard,
/portfolio, /portfolio/producto, /portfolio/producto/{id}.
Correr: uvicorn app:app --host 0.0.0.0 --port 8000   (o API.bat)
"""
import os
import sys

# UTF-8 en consola Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_AQUI = os.path.dirname(os.path.abspath(__file__))
if _AQUI not in sys.path:
    sys.path.insert(0, _AQUI)

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from core import db
from agents.market_intel import market_intel
from agents.listing import generar as generar_listing
from agents.pricing import evaluar as evaluar_precio
from agents import analytics
from agents import customer_bot
from agents import productos
from agents import asistente
from agents import publicador
from agents import exito
from agents import ganancias
from agents import dedicacion
from agents import creativos
from data import mercado
from data import motor_propio

db.init()
app = FastAPI(title="MV FBA IA — API", version="2.0")

# CORS abierto: la API corre en localhost y la consumen n8n y la app movil
# (mobile/), que sirve desde otro origen (otro puerto o el navegador del
# celular). No hay cookies/sesion de por medio (sin auth), asi que abrir el
# origen no expone datos de otros usuarios.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class MsgIn(BaseModel):
    cliente: str
    texto: str


class SaleIn(BaseModel):
    asin: str
    unidades: int
    precio: float
    neto_unitario: float
    pais: str = "US"
    segmento: str = "general"
    product_id: int | None = None


class ResearchIn(BaseModel):
    categoria: str
    demo: bool = False


class AsistenteIn(BaseModel):
    pregunta: str
    historial: list[dict] | None = None


class GananciasIn(BaseModel):
    inversion: float | None = None
    unidades: int | None = None
    costo: float = 2.10
    flete: float = 0.80
    arancel_pct: float = 6.0
    prep: float = 0.50
    fba_fee: float | None = None
    precio: float | None = None
    precio_competencia: float | None = None
    techo_demanda: int = 290


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


class ProductoIn(BaseModel):
    nombre: str
    asin: str = ""
    costo: float = 0.0
    flete: float = 0.0
    arancel_pct: float = 0.0
    prep: float = 0.0
    fba_fee: float | None = None
    precio_competencia: float | None = None
    techo_demanda: int = 290
    notas: str = ""


@app.get("/health")
def health():
    return {"ok": True, "config": config.estado_config()}


@app.post("/webhook/message")
def webhook_message(m: MsgIn):
    return customer_bot.procesar(m.cliente, m.texto)


@app.post("/webhook/sale")
def webhook_sale(s: SaleIn):
    return analytics.registrar_venta(s.asin, s.unidades, s.precio, s.neto_unitario,
                                     pais=s.pais, segmento=s.segmento,
                                     product_id=s.product_id)


@app.post("/run/research")
def run_research(r: ResearchIn):
    mi = market_intel(r.categoria, config.MARKETPLACE, demo=r.demo)
    out = {"nicho": mi}
    if mi["ok"]:
        out["listing"] = generar_listing(r.categoria, config.MARKETPLACE, demo=r.demo)
        out["pricing"] = evaluar_precio({"costo": 2.1, "flete": 0.8, "arancel_pct": 6,
                                         "prep": 0.5})
    return out


@app.get("/dashboard")
def dashboard():
    return analytics.kpis()


@app.post("/assistant")
def assistant(a: AsistenteIn):
    return asistente.responder(a.pregunta, a.historial)


@app.get("/motor/keywords")
def motor_keywords(seed: str, demo: bool = False):
    return motor_propio.investigar(seed, demo=demo)


@app.get("/mercado/estrellas")
def mercado_estrellas(keyword: str, precio_min: float = 10.0,
                      precio_max: float = 50.0, demo: bool = False):
    r = mercado.productos_estrella(keyword, precio_min, precio_max, demo=demo)
    r["competencia"] = mercado.resumen_competencia(r["productos"])
    r["proveedores"] = mercado.links_proveedores(keyword)
    return r


@app.post("/ganancias")
def ganancias_sim(g: GananciasIn):
    return ganancias.simular(inversion=g.inversion, unidades=g.unidades,
                             costo=g.costo, flete=g.flete,
                             arancel_pct=g.arancel_pct, prep=g.prep,
                             fba_fee=g.fba_fee, precio=g.precio,
                             precio_competencia=g.precio_competencia,
                             techo_demanda=g.techo_demanda)


@app.get("/dedicacion")
def dedicacion_estimar(productos: int = 1, lanzando: bool = False):
    return dedicacion.estimar(n_productos_operacion=productos,
                              lanzando_producto=lanzando)


@app.get("/creativos/banner")
def creativos_banner(titulo: str, badges: str = ""):
    lista = [b.strip() for b in badges.split(",") if b.strip()][:3]
    png = creativos.generar_banner(titulo, badges=lista)
    return Response(content=png, media_type="image/png")


@app.get("/creativos/infografia")
def creativos_infografia(bullets: str):
    lista = [b.strip() for b in bullets.split("|") if b.strip()]
    png = creativos.generar_infografia(lista)
    return Response(content=png, media_type="image/png")


@app.get("/exito")
def exito_eval(keyword: str, precio: float | None = None,
               margen_pct: float | None = None, demo: bool = False):
    comp = None
    if demo:
        r = mercado.productos_estrella(keyword, 10, 50, demo=True)
        comp = mercado.resumen_competencia(r["productos"])
    elif config.KEEPA_API_KEY:
        r = mercado.productos_estrella(keyword, 10, 50)
        if r["ok"]:
            comp = mercado.resumen_competencia(r["productos"])
    return exito.evaluar(keyword, competencia=comp, precio_objetivo=precio,
                         margen_pct=margen_pct)


@app.post("/publicar")
def publicar(p: PublicarIn):
    kws = None
    if p.usar_motor_propio:
        res = motor_propio.investigar(p.nombre, demo=p.demo)
        if res["ok"]:
            kws = motor_propio.keywords_cerebro(res)
    return publicador.paquete(p.nombre, costo=p.costo, flete=p.flete,
                              arancel_pct=p.arancel_pct, prep=p.prep,
                              fba_fee=p.fba_fee,
                              precio_competencia=p.precio_competencia,
                              techo_demanda=p.techo_demanda, keywords=kws,
                              demo=p.demo)


@app.get("/portfolio")
def portfolio():
    return productos.resumen_portafolio()


@app.post("/portfolio/producto")
def portfolio_alta(p: ProductoIn):
    return productos.guardar(p.nombre, asin=p.asin, costo=p.costo, flete=p.flete,
                             arancel_pct=p.arancel_pct, prep=p.prep,
                             fba_fee=p.fba_fee,
                             precio_competencia=p.precio_competencia,
                             techo_demanda=p.techo_demanda, notas=p.notas)


@app.get("/portfolio/producto/{pid}")
def portfolio_analisis(pid: int):
    return productos.analisis(pid)


# ---------- Rutas /api/* del panel SaaS (frontend React) ---------- #
# Los endpoints de arriba quedan CONGELADOS como contrato para n8n/mobile;
# todo lo nuevo del SPA vive bajo /api (ver api_rutas.py).
import api_rutas  # noqa: E402

app.include_router(api_rutas.router)

# Si el frontend compilado existe (frontend/dist, generado por `npm run build`
# o incluido por el instalador de Windows), se sirve como el panel web en la
# raiz. Montado AL FINAL para que nunca tape /api ni los endpoints legacy.
_FRONT_DIST = os.path.join(_AQUI, "frontend", "dist")
if os.path.isdir(_FRONT_DIST):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_FRONT_DIST, html=True), name="spa")
