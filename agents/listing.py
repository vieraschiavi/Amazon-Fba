#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/listing.py — Generador de listing Amazon (titulo, bullets, descripcion, banner).

Reconstruido desde DOCUMENTACION.md: generar(producto, mercado) -> dict con
`titulo`, `bullets` (5), `descripcion`, `banner_brief`. Usa las keywords reales de
Cerebro como insumo (el listing es para el comprador de Amazon US -> copy en INGLES).

Dos caminos (igual que el diseño documentado del sistema):
  - Con ANTHROPIC_API_KEY + SDK anthropic instalado -> redacta con Claude (Sonnet).
  - Sin clave / sin SDK / si falla -> modo offline DETERMINISTICO (no rompe el pipeline).
    El offline NO es un placeholder: arma un listing usable con las keywords de Cerebro.

Standalone:
    python agents/listing.py --demo
    python agents/listing.py --csv export.csv --producto "bamboo kitchen utensils"
Importable:
    from agents.listing import generar
"""

import argparse
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from data.cerebro import cerebro_con_estado, keywords_para_listing  # noqa: E402

MODEL_SONNET = os.environ.get("MODEL_SONNET", "claude-sonnet-4-6")


# --------------------------------------------------------------------------- #
# Camino LLM (opcional). Nunca rompe: si algo falla, cae a offline.
# --------------------------------------------------------------------------- #
def _generar_con_claude(producto: str, kw: dict, mercado: str):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic  # SDK opcional
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You are an Amazon listing copywriter. Marketplace: " + mercado + ".\n"
            "Product/niche: " + producto + "\n"
            "Use these researched keywords (from Helium 10 Cerebro):\n"
            "  Title keywords: " + ", ".join(kw["titulo"]) + "\n"
            "  Opportunity keywords (bullets): " + ", ".join(kw["bullets"]) + "\n"
            "  Backend keywords: " + ", ".join(kw["backend"]) + "\n"
            "Return ONLY valid JSON, no preamble, with keys: "
            'titulo (string, <=200 chars), bullets (array of exactly 5 strings), '
            "descripcion (string), banner_brief (string). Copy in English."
        )
        msg = client.messages.create(
            model=MODEL_SONNET, max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        texto = texto.strip().strip("`")
        if texto.startswith("json"):
            texto = texto[4:].strip()
        data = json.loads(texto)
        if all(k in data for k in ("titulo", "bullets", "descripcion", "banner_brief")):
            data["_motor"] = "IA avanzada"
            return data
    except Exception:
        return None
    return None


# --------------------------------------------------------------------------- #
# Camino OFFLINE deterministico (default, siempre funciona)
# --------------------------------------------------------------------------- #
def _cap(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def _titulo_offline(producto: str, kw: dict) -> str:
    base = kw["titulo"][:3] if kw["titulo"] else [producto]
    # quita prefijo [DEMO] para el copy final
    base = [b.replace("[DEMO] ", "").strip() for b in base]
    titulo = " - ".join(dict.fromkeys([b.title() for b in base]))
    extras = "Eco-Friendly, Heat Resistant, Non-Scratch, Dishwasher Safe Kitchen Set"
    return _cap(f"{titulo} | {extras}", 200)


def _bullets_offline(kw: dict) -> list:
    opp = [k.replace("[DEMO] ", "").strip() for k in kw["bullets"]] or \
          [k.replace("[DEMO] ", "").strip() for k in kw["titulo"]]
    def pick(i, default=""):
        return opp[i] if i < len(opp) else default
    return [
        f"PREMIUM ECO MATERIAL — Made from sustainable bamboo and food-grade silicone; "
        f"a true {pick(0,'eco friendly kitchen set')} that is BPA-free and built to last.",
        f"COMPLETE SET FOR EVERY MEAL — Covers what shoppers search for: "
        f"{pick(1,'cooking utensils')} for everyday cooking, baking and serving.",
        "HEAT RESISTANT & NON-SCRATCH — Safe up to 446°F; won't scratch your non-stick "
        "pots and pans, unlike cheap metal sets.",
        f"EASY TO CLEAN & STORE — Dishwasher safe and includes a holder; "
        f"ideal as {pick(2,'kitchen gadgets')} that keep your counter tidy.",
        "PERFECT GIFT — Comes in a sturdy box, an ideal housewarming, wedding or "
        "holiday gift for home cooks who care about sustainability.",
    ]


def _descripcion_offline(producto: str, kw: dict) -> str:
    p = producto.replace("[DEMO] ", "").strip()
    extra = ", ".join(k.replace("[DEMO] ", "").strip() for k in kw["bullets"][:4])
    return (
        f"Upgrade your kitchen with this complete {p} set. Designed for cooks who want "
        f"durable, eco-friendly tools that look good and perform every day. Crafted from "
        f"sustainable bamboo and heat-resistant, food-grade silicone, the set is "
        f"non-scratch, BPA-free and dishwasher safe. Whether you are searching for "
        f"{extra}, this set has you covered. Backed by a satisfaction guarantee — "
        f"if you are not happy, we make it right."
    )


def _banner_offline(producto: str, kw: dict) -> str:
    p = producto.replace("[DEMO] ", "").strip()
    return (
        f"Hero banner for '{p}'. Lifestyle shot: the full set in a bright, modern kitchen, "
        f"bamboo + sage-green silicone on a wooden counter. Overlay 3 badges: "
        f"'Eco Bamboo', 'Heat Resistant 446°F', 'Non-Scratch'. Clean sans-serif type, "
        f"natural light, neutral palette. Emphasize the differentiator from reviews: "
        f"durability and no melting/scratching vs cheap competitors."
    )


def generar(producto, mercado: str = "US", csv_path: str = None, demo: bool = False,
            keywords: list = None) -> dict:
    """
    producto: str (nicho/keyword) o dict con clave 'nicho'/'nombre'.
    keywords: lista opcional de data.cerebro.Keyword ya investigadas (p.ej. del
    motor propio embebido); si se pasa, no consulta Cerebro.
    Devuelve {titulo, bullets[5], descripcion, banner_brief, _motor, _fuente_kw}.
    """
    if isinstance(producto, dict):
        nombre = producto.get("nicho") or producto.get("nombre") or ""
    else:
        nombre = str(producto)

    if keywords:
        kws, estado = keywords, {"fuente": "motor_propio"}
    else:
        kws, estado = cerebro_con_estado(categoria=nombre, csv_path=csv_path, demo=demo)
    kw = keywords_para_listing(kws)

    # 1) intento con Claude; 2) si no, offline deterministico
    data = _generar_con_claude(nombre, kw, mercado) if kws else None
    if data is None:
        data = {
            "titulo": _titulo_offline(nombre, kw),
            "bullets": _bullets_offline(kw),
            "descripcion": _descripcion_offline(nombre, kw),
            "banner_brief": _banner_offline(nombre, kw),
            "_motor": "offline-deterministico",
        }
    data["_fuente_kw"] = estado["fuente"]
    data["_keywords"] = kw
    return data


def _texto(producto, d: dict) -> str:
    out = ["=" * 64, f"LISTING — {producto}   (motor: {d['_motor']}, kw: {d['_fuente_kw']})",
           "=" * 64, "TITULO:", "  " + d["titulo"], "", "BULLETS:"]
    for i, b in enumerate(d["bullets"], 1):
        out.append(f"  {i}. {b}")
    out += ["", "DESCRIPCION:", "  " + d["descripcion"], "",
            "BANNER BRIEF:", "  " + d["banner_brief"], "=" * 64]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generador de listing Amazon (FBA).")
    ap.add_argument("--producto", default="bamboo kitchen utensils")
    ap.add_argument("--mercado", default="US")
    ap.add_argument("--csv", help="Export CSV de Cerebro.")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    d = generar(args.producto, args.mercado, csv_path=args.csv, demo=args.demo)
    print(json.dumps(d, ensure_ascii=False, indent=2) if args.json else _texto(args.producto, d))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
