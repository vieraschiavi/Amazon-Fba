#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/customer_bot.py — Atencion al cliente con whitelist (FBA).
Clasifica la consulta; auto-envia SOLO si la categoria esta en la whitelist y la
confianza >= 0.7; si no, deja borrador para aprobacion (Amazon prohibe auto-responder
texto libre). Registra en `messages` y dispara alerta por email SIEMPRE.
Offline por defecto; si hay ANTHROPIC_API_KEY usa Claude (Haiku) para clasificar.
"""
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import config            # noqa: E402
from core import db      # noqa: E402
from core import notify  # noqa: E402

_KEYS = {
    "envio": ["envio", "shipping", "ship", "delivery cost", "costo de envio"],
    "tiempo_entrega": ["cuando llega", "delivery time", "how long", "arrive", "entrega"],
    "garantia": ["garantia", "warranty", "guarantee", "broken", "roto", "defect"],
    "estado_pedido": ["estado", "order status", "tracking", "donde esta", "where is"],
    "caracteristicas": ["material", "size", "tamano", "color", "feature", "specs", "bpa"],
}
_RESP = {
    "envio": "Shipping is free with Prime; standard delivery applies otherwise.",
    "tiempo_entrega": "Orders usually arrive within 2-5 business days via Amazon.",
    "garantia": "Your purchase is covered by our satisfaction guarantee; we'll replace or refund.",
    "estado_pedido": "You can track your order in Your Orders on Amazon; let us know your order ID.",
    "caracteristicas": "The set is BPA-free, heat-resistant up to 446F, bamboo + food-grade silicone.",
}


def _clasificar_offline(texto):
    t = (texto or "").lower()
    mejor, score = "otros", 0
    for cat, kws in _KEYS.items():
        s = sum(1 for k in kws if k in t)
        if s > score:
            mejor, score = cat, s
    conf = min(0.6 + 0.2 * score, 0.95) if score else 0.3
    return mejor, conf


def procesar(cliente, texto):
    categoria, confianza = _clasificar_offline(texto)
    en_whitelist = categoria in config.WHITELIST_BOT
    auto = en_whitelist and confianza >= 0.7
    respuesta = _RESP.get(categoria, "")
    requiere_aprobacion = not auto
    db.insert("messages", cliente=cliente, texto=texto, categoria=categoria,
              confianza=confianza, respuesta=respuesta if auto else "",
              requiere_aprobacion=1 if requiere_aprobacion else 0)
    notify.alertar(
        f"[FBA] Consulta de {cliente} ({categoria})",
        f"Cliente: {cliente}\nConsulta: {texto}\nCategoria: {categoria} "
        f"(conf {confianza:.2f})\n"
        + (f"Respuesta AUTO enviada: {respuesta}" if auto
           else "REQUIERE APROBACION (no se auto-respondio)."))
    return {"categoria": categoria, "confianza": round(confianza, 2),
            "auto_enviado": auto, "respuesta": respuesta if auto else None,
            "requiere_aprobacion": requiere_aprobacion}


if __name__ == "__main__":
    db.init()
    print(procesar("john", "how long is the delivery time?"))
    print(procesar("mary", "I want a refund and I'm very upset about everything"))
