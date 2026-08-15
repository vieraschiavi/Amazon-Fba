#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
core/notify.py — Alertas por email. Sin SMTP_USER/PASS -> DRY-RUN (registra, no envia).
Toda alerta queda en la tabla alerts_outbox. ALERT_TO cae al propio SMTP_USER del
usuario si no se configura uno aparte (ver config.py); nunca a un email fijo.
"""
import os
import smtplib
import sys
from email.mime.text import MIMEText

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import config            # noqa: E402
from core import db      # noqa: E402


def alertar(asunto: str, cuerpo: str, para: str = None) -> dict:
    """Envia (o simula) una alerta y la registra en alerts_outbox."""
    para = para or config.ALERT_TO
    enviado = False
    error = None
    if config.SMTP_USER and config.SMTP_PASS:
        try:
            msg = MIMEText(cuerpo, "plain", "utf-8")
            msg["Subject"] = asunto
            msg["From"] = config.SMTP_USER
            msg["To"] = para
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
                s.starttls()
                s.login(config.SMTP_USER, config.SMTP_PASS)
                s.sendmail(config.SMTP_USER, [para], msg.as_string())
            enviado = True
        except Exception as e:           # nunca rompe el pipeline por un mail
            error = str(e)
    try:
        db.insert("alerts_outbox", para=para, asunto=asunto, cuerpo=cuerpo,
                  enviado=1 if enviado else 0)
    except Exception:
        pass
    return {"enviado": enviado, "dry_run": not (config.SMTP_USER and config.SMTP_PASS),
            "para": para, "error": error}


if __name__ == "__main__":
    db.init()
    r = alertar("[FBA] Prueba", "Cuerpo de prueba.")
    print("Resultado:", r)
    print("Outbox:", db.rows("SELECT asunto,enviado FROM alerts_outbox ORDER BY id DESC LIMIT 3"))
