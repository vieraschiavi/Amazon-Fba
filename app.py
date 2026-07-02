#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — API FastAPI (puente con n8n) del sistema FBA.
Endpoints: /health, /webhook/message, /webhook/sale, /run/research, /dashboard.
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

from fastapi import FastAPI
from pydantic import BaseModel

import config
from core import db
from agents.market_intel import market_intel
from agents.listing import generar as generar_listing
from agents.pricing import evaluar as evaluar_precio
from agents import analytics
from agents import customer_bot

db.init()
app = FastAPI(title="FBA API", version="1.0")


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
