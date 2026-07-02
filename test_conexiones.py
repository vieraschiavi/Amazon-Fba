#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_conexiones.py — Verifica las conexiones del README y reporta verde/rojo.
Chequea: (1) Keepa, (2) Anthropic/Claude, (3) SMTP/Gmail, (4) CSV de Cerebro.
Validaciones reales (Keepa /token, Anthropic /models, SMTP login) sin gastar de mas.
Las funciones check_* devuelven filas {estado,nombre,detalle} reutilizables por el dashboard.

Uso:
    python test_conexiones.py                 (chequea todo)
    python test_conexiones.py --asin B0...     (ademas trae 1 producto real de Keepa, gasta 1 token)
    python test_conexiones.py --init-env       (crea .env desde .env.example si no existe)
"""
import argparse
import glob
import json
import os
import smtplib
import sys
import urllib.error
import urllib.request

_AQUI = os.path.dirname(os.path.abspath(__file__))
if _AQUI not in sys.path:
    sys.path.insert(0, _AQUI)
import config              # noqa: E402
from data import keepa     # noqa: E402

OK, FALLA, AVISO = "ok", "falla", "aviso"
_SIMBOLO = {OK: "[ OK ]", FALLA: "[FALLA]", AVISO: "[AVISO]"}


def check_keepa(asin=None):
    filas = []
    if not config.KEEPA_API_KEY:
        return [{"estado": FALLA, "nombre": "Keepa",
                 "detalle": "falta KEEPA_API_KEY (suscripcion 19 EUR/mes; key en keepa.com -> API)"}]
    tk = keepa.tokens_left()
    if not tk["ok"]:
        return [{"estado": FALLA, "nombre": "Keepa", "detalle": tk["mensaje"]}]
    filas.append({"estado": OK, "nombre": "Keepa",
                  "detalle": f"clave valida. tokens: {tk['tokens_left']} "
                             f"(recarga ~{tk['refill_in_min']} min)"})
    if asin:
        pr = keepa.producto(asin)
        if pr.get("ok"):
            filas.append({"estado": OK, "nombre": "Keepa producto",
                          "detalle": f"{asin}: ${pr['precio']} | BSR {pr['bsr']} | "
                                     f"~{pr['ventas_estim']} u/mes (estimado)"})
        else:
            filas.append({"estado": AVISO, "nombre": "Keepa producto",
                          "detalle": pr.get("mensaje", "sin datos")})
    return filas


def check_anthropic():
    if not config.ANTHROPIC_API_KEY:
        return [{"estado": AVISO, "nombre": "Anthropic",
                 "detalle": "sin clave -> listing en modo offline (no es error)"}]
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": config.ANTHROPIC_API_KEY,
                     "anthropic-version": "2023-06-01", "User-Agent": "fba-system/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [{"estado": OK, "nombre": "Anthropic",
                 "detalle": f"clave valida. modelos visibles: {len(data.get('data', []))}"}]
    except urllib.error.HTTPError as e:
        return [{"estado": FALLA, "nombre": "Anthropic", "detalle": f"clave rechazada (HTTP {e.code})"}]
    except Exception as e:
        return [{"estado": FALLA, "nombre": "Anthropic", "detalle": f"error de red: {e}"}]


def check_smtp():
    if not (config.SMTP_USER and config.SMTP_PASS):
        return [{"estado": AVISO, "nombre": "SMTP/Gmail",
                 "detalle": f"sin SMTP_USER/PASS -> alertas en dry-run. Destino: {config.ALERT_TO}"}]
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
            s.starttls()
            s.login(config.SMTP_USER, config.SMTP_PASS)
        return [{"estado": OK, "nombre": "SMTP/Gmail",
                 "detalle": f"login OK como {config.SMTP_USER} -> alertas reales a {config.ALERT_TO}"}]
    except smtplib.SMTPAuthenticationError:
        return [{"estado": FALLA, "nombre": "SMTP/Gmail",
                 "detalle": "rechazado. Gmail requiere App Password (no la clave normal)"}]
    except Exception as e:
        return [{"estado": FALLA, "nombre": "SMTP/Gmail", "detalle": f"error: {e}"}]


def check_cerebro():
    d = config.CEREBRO_CSV_DIR
    csvs = sorted(glob.glob(os.path.join(d, "*.csv")))
    if not csvs:
        return [{"estado": AVISO, "nombre": "Cerebro CSV",
                 "detalle": f"sin .csv en {d}. Exporta de Cerebro (Export Data) y dejalo ahi"}]
    try:
        from data.cerebro import parse_cerebro_csv
        kws = parse_cerebro_csv(csvs[-1])
        return [{"estado": OK, "nombre": "Cerebro CSV",
                 "detalle": f"{os.path.basename(csvs[-1])}: {len(kws)} keywords leidas"}]
    except Exception as e:
        return [{"estado": FALLA, "nombre": "Cerebro CSV",
                 "detalle": f"no se pudo leer {os.path.basename(csvs[-1])}: {e}"}]


def verificar_todo(asin=None):
    filas = []
    filas += check_keepa(asin)
    filas += check_anthropic()
    filas += check_smtp()
    filas += check_cerebro()
    return filas


def init_env():
    dst = os.path.join(_AQUI, ".env")
    src = os.path.join(_AQUI, ".env.example")
    if os.path.exists(dst):
        print(f"Ya existe {dst} (no lo piso).")
        return
    if os.path.exists(src):
        with open(src) as a, open(dst, "w") as b:
            b.write(a.read())
        print(f"Cree {dst} desde .env.example. Abrilo y pega tus claves.")
    else:
        print("No encontre .env.example.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verifica conexiones del README.")
    ap.add_argument("--asin", default=None, help="ASIN real para probar Keepa (gasta 1 token)")
    ap.add_argument("--init-env", action="store_true")
    args = ap.parse_args(argv)
    if args.init_env:
        init_env()
        return 0
    print("=" * 60 + "\nVERIFICADOR DE CONEXIONES — sistema FBA\n" + "=" * 60)
    for f in verificar_todo(args.asin):
        print(f"  {_SIMBOLO[f['estado']]}  {f['nombre']:<16} {f['detalle']}")
    print("=" * 60)
    print("Anthropic/SMTP/Cerebro en aviso no son errores: el sistema funciona igual.\n"
          "Keepa es el unico que necesita suscripcion paga para datos programaticos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
