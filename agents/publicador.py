#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/publicador.py — Paquete de publicacion end-to-end de MV FBA IA.

Arma TODO lo necesario para publicar un producto en Amazon de forma atractiva y
profesional, con los motores ya validados del sistema (nada se inventa):

  - Listing completo: titulo + 5 bullets + descripcion + backend keywords
    (agents/listing: Claude si hay clave, offline deterministico si no).
  - Brief de fotos: las 7 tomas estandar que Amazon espera (guion para el
    fotografo o para vos con el celular; Amazon exige fotos REALES del producto).
  - Precio y unit economics: agents/pricing (landed, margen, ROI, semaforo).
  - Cantidades: orden de prueba (validacion) y primera compra al techo
    (misma logica de pipeline que el portafolio).
  - Proveedores serios: checklist de verificacion (Trade Assurance, anios,
    certificaciones) + plantilla RFQ profesional en ingles lista para Alibaba.
  - Checklist Seller Central: pasos exactos para publicar; el listing se puede
    cargar a mano (gratis) o via la API oficial SP-API de Amazon (GRATIS para
    sellers registrados; no es una API de terceros paga).

Salidas: dict estructurado (panel / API / n8n) y HTML imprimible descargable.
"""
import argparse
import html as _html
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import config                                    # noqa: E402
from agents.listing import generar as generar_listing   # noqa: E402
from agents.pricing import evaluar as evaluar_precio    # noqa: E402

PIPELINE_MESES = 4      # mismo supuesto que agents/productos

FOTOS = [
    ("Principal (obligatoria)", "Producto solo sobre fondo BLANCO puro (Amazon lo "
     "exige), ocupando ~85% del cuadro, minimo 1600px para zoom. Sin logos ni texto."),
    ("Angulos", "3/4 frontal y vista trasera. Muestra materiales y terminaciones."),
    ("Escala", "El producto en una mano o junto a un objeto cotidiano: el comprador "
     "tiene que entender el tamano real sin leer medidas."),
    ("En uso (lifestyle)", "Una persona usandolo en el ambiente real (cocina "
     "luminosa y moderna si es hogar). Es la foto que mas vende."),
    ("Beneficios con texto", "Infografia: 3-4 iconos con los beneficios clave "
     "(eco, resistente al calor, apto lavavajillas...)."),
    ("Detalle / calidad", "Macro de la textura o el detalle que diferencia de la "
     "competencia barata."),
    ("Contenido del paquete", "Todo lo que llega en la caja, prolijo y contado "
     "(ideal si es un set)."),
]

CHECKLIST_PROVEEDOR = [
    "Trade Assurance activo en Alibaba (pago protegido contra specs).",
    "3+ anios operando y perfil 'Verified Supplier'.",
    "Responde en <24h y contesta preguntas tecnicas con precision.",
    "Certificaciones del producto (FDA para contacto con alimentos, CPSIA "
    "si es para chicos) verificadas ANTES de pagar.",
    "Acepta muestra previa (paga la muestra, no la saltees).",
    "Cotiza FOB con incoterm claro y tiempos de produccion por escrito.",
    "Referencias: pedile fotos de ordenes reales despachadas a US.",
]

CHECKLIST_SELLER = [
    "Cuenta Professional en Seller Central (USD 39.99/mes) verificada.",
    "Marca: registra tu marca (Brand Registry) o publica generico con UPC/GTIN "
    "comprado en GS1 (no compres codigos truchos).",
    "Catalogo -> 'Add a Product' -> 'I'm adding a product not sold on Amazon'.",
    "Pega titulo, bullets y descripcion del paquete (abajo). Backend keywords en "
    "'Search Terms' (max 250 bytes).",
    "Sube las 7 fotos del brief (principal fondo blanco obligatorio).",
    "Precio del paquete + shipping template FBA.",
    "Envia inventario: 'Send to Amazon' con la cantidad de la orden de prueba.",
    "Activa una campana PPC automatica chica (ACoS objetivo del pricing) al "
    "recibir stock.",
    "AUTOMATIZACION OPCIONAL: la SP-API oficial de Amazon (gratis para sellers) "
    "permite crear/actualizar listings, precios y stock por codigo; requiere "
    "registrar una app en Seller Central -> Develop Apps.",
]


def _rfq(nombre, unidades):
    return (
        f"Subject: RFQ — {nombre} ({unidades} units, USA market)\n\n"
        "Hi, I'm sourcing for my Amazon FBA brand in the US market.\n\n"
        f"Product: {nombre}\n"
        f"Quantity: {unidades} units (trial order; monthly reorders if quality "
        "is consistent)\n"
        "Please quote:\n"
        "  1. Unit price EXW and FOB (nearest port), with your MOQ tiers\n"
        "  2. Production lead time for this quantity\n"
        "  3. Sample cost + DHL/FedEx express shipping to USA\n"
        "  4. Certifications you hold for this product (FDA food-contact, etc.) — "
        "please attach the certificates\n"
        "  5. Customization: logo engraving/printing and custom packaging cost\n\n"
        "We pay via Trade Assurance only. Looking for a long-term supplier, not "
        "the cheapest one-off.\n\nThanks!"
    )


def paquete(nombre, costo=0.0, flete=0.0, arancel_pct=0.0, prep=0.0, fba_fee=None,
            precio_competencia=None, techo_demanda=290, keywords=None,
            csv_path=None, demo=False):
    """Arma el paquete completo de publicacion. Nunca lanza; siempre devuelve dict."""
    nombre = (nombre or "").strip()
    if not nombre:
        return {"ok": False, "mensaje": "El producto necesita un nombre."}
    fba_fee = config.FBA_FEE_DEFAULT if fba_fee is None else fba_fee

    li = generar_listing(nombre, config.MARKETPLACE, csv_path=csv_path, demo=demo,
                         keywords=keywords)
    m = evaluar_precio({"costo": costo, "flete": flete, "arancel_pct": arancel_pct,
                        "prep": prep}, fba_fee=fba_fee,
                       precio_competencia=precio_competencia)

    landed = m["landed"]
    orden_prueba = max(1, int(round(1500 / landed))) if landed > 0 else 0
    primera_compra = int(techo_demanda * PIPELINE_MESES) if techo_demanda else 0
    return {
        "ok": True, "producto": nombre, "marketplace": config.MARKETPLACE,
        "listing": {
            "titulo": li["titulo"], "bullets": li["bullets"],
            "descripcion": li["descripcion"],
            "backend_keywords": ", ".join(li.get("_keywords", {}).get("backend", [])),
            "banner_brief": li["banner_brief"], "motor": li["_motor"],
            "fuente_keywords": li["_fuente_kw"],
        },
        "fotos": [{"toma": t, "guion": g} for t, g in FOTOS],
        "pricing": m,
        "cantidades": {
            "orden_prueba": orden_prueba,
            "orden_prueba_usd": round(orden_prueba * landed, 2),
            "criterio_prueba": "USD ~1.500 de landed para validar antes de escalar",
            "primera_compra_techo": primera_compra,
            "primera_compra_usd": round(primera_compra * landed, 2),
            "criterio_compra": f"~{PIPELINE_MESES} meses de stock al techo de demanda "
                               f"({techo_demanda} u/mes), recien despues de validar",
        },
        "proveedor": {"checklist": CHECKLIST_PROVEEDOR,
                      "rfq": _rfq(nombre, orden_prueba)},
        "checklist_seller_central": CHECKLIST_SELLER,
        "nota_honesta": ("Las fotos deben ser REALES de tu producto (Amazon lo "
                         "exige y el comprador lo nota). La orden de prueba va "
                         "antes que cualquier escala: ningun score reemplaza "
                         "vender de verdad la primera tanda."),
    }


def html_paquete(p):
    """HTML imprimible del paquete (misma estetica navy que el pitch)."""
    if not p.get("ok"):
        return f"<p>{_html.escape(p.get('mensaje', 'Paquete invalido'))}</p>"
    e = _html.escape
    li = p["listing"]
    bullets = "".join(f"<li>{e(b)}</li>" for b in li["bullets"])
    fotos = "".join(f"<tr><td><b>{e(f['toma'])}</b></td><td>{e(f['guion'])}</td></tr>"
                    for f in p["fotos"])
    prov = "".join(f"<li>{e(c)}</li>" for c in p["proveedor"]["checklist"])
    seller = "".join(f"<li>{e(c)}</li>" for c in p["checklist_seller_central"])
    m, q = p["pricing"], p["cantidades"]
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paquete de publicacion — {e(p['producto'])} — MV FBA IA</title>
<style>
 body{{font-family:'Segoe UI',Inter,system-ui,sans-serif;color:#0f172a;background:#f1f5f9;margin:0;padding:24px}}
 .wrap{{max-width:860px;margin:0 auto}}
 .hero{{background:linear-gradient(135deg,#1e3a8a,#152a63);color:#fff;border-radius:16px;padding:24px 28px}}
 .hero h1{{margin:0;font-size:24px}} .hero .g{{color:#8bc34a}}
 .hero p{{color:#c7d2fe;margin:6px 0 0;font-size:13.5px}}
 .card{{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:18px 22px;margin-top:14px}}
 h2{{font-size:16px;margin:0 0 10px;color:#1e3a8a;border-left:4px solid #8bc34a;padding-left:10px}}
 table{{width:100%;border-collapse:collapse;font-size:13.5px}}
 td{{padding:7px 9px;border-bottom:1px solid #e2e8f0;vertical-align:top}}
 ul,ol{{margin:6px 0;padding-left:20px;line-height:1.65;font-size:13.5px}}
 .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}}
 .kpi{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);border-radius:10px;padding:9px 11px}}
 .kpi b{{display:block;font-size:18px;color:#8bc34a}} .kpi span{{font-size:11px;color:#c7d2fe}}
 pre{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px;font-size:12.5px;white-space:pre-wrap}}
 .aviso{{background:#fffbeb;border:1px solid #f59e0b;border-radius:12px;padding:12px 14px;font-size:13px}}
 @media print{{body{{background:#fff}}}}
</style></head><body><div class="wrap">
<div class="hero"><h1>MV FBA <span class="g">IA</span> — Paquete de publicacion</h1>
<p>{e(p['producto'])} · mercado {e(p['marketplace'])} · listing: {e(li['motor'])} · keywords: {e(li['fuente_keywords'])}</p>
<div class="kpis">
 <div class="kpi"><b>USD {m['precio']:.2f}</b><span>precio sugerido ({e(m['estrategia'])})</span></div>
 <div class="kpi"><b>{m['margen_pct']:.1f}%</b><span>margen ({e(m['semaforo'])})</span></div>
 <div class="kpi"><b>{q['orden_prueba']} u</b><span>orden de prueba (USD {q['orden_prueba_usd']:,.0f})</span></div>
 <div class="kpi"><b>{q['primera_compra_techo']} u</b><span>1ra compra al techo (USD {q['primera_compra_usd']:,.0f})</span></div>
</div></div>
<div class="card"><h2>1. Titulo</h2><p>{e(li['titulo'])}</p>
<h2>2. Bullets</h2><ul>{bullets}</ul>
<h2>3. Descripcion</h2><p>{e(li['descripcion'])}</p>
<h2>4. Backend keywords (Search Terms)</h2><pre>{e(li['backend_keywords'])}</pre></div>
<div class="card"><h2>5. Brief de fotos (7 tomas)</h2><table>{fotos}</table>
<p style="font-size:12.5px;color:#64748b">Banner/A+: {e(li['banner_brief'])}</p></div>
<div class="card"><h2>6. Unit economics</h2><table>
<tr><td>Landed cost</td><td>USD {m['landed']:.2f}</td></tr>
<tr><td>Precio sugerido</td><td>USD {m['precio']:.2f} — {e(m['estrategia'])}</td></tr>
<tr><td>Neto / unidad</td><td>USD {m['neto']:.2f}</td></tr>
<tr><td>Margen / ROI</td><td>{m['margen_pct']:.1f}% / {m['roi_pct']:.1f}% [{e(m['semaforo'].upper())}]</td></tr>
<tr><td>Break-even</td><td>USD {m['break_even']:.2f}</td></tr></table></div>
<div class="card"><h2>7. Proveedor serio — checklist</h2><ul>{prov}</ul>
<h2>8. RFQ listo para Alibaba (ingles)</h2><pre>{e(p['proveedor']['rfq'])}</pre></div>
<div class="card"><h2>9. Publicar en Seller Central — paso a paso</h2><ol>{seller}</ol></div>
<div class="card"><div class="aviso"><b>Nota honesta:</b> {e(p['nota_honesta'])}</div></div>
<p style="color:#64748b;font-size:12px;text-align:center;margin:16px 0 4px">
Generado por MV FBA IA — mismos motores de pricing y listing que el panel.</p>
</div></body></html>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Paquete de publicacion end-to-end.")
    ap.add_argument("--nombre", default="bamboo kitchen utensils set")
    ap.add_argument("--costo", type=float, default=2.1)
    ap.add_argument("--flete", type=float, default=0.8)
    ap.add_argument("--arancel", type=float, default=6.0)
    ap.add_argument("--prep", type=float, default=0.5)
    ap.add_argument("--competencia", type=float, default=19.99)
    ap.add_argument("--techo", type=int, default=290)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--html", metavar="RUTA", help="Escribe el paquete como HTML.")
    args = ap.parse_args(argv)
    p = paquete(args.nombre, costo=args.costo, flete=args.flete,
                arancel_pct=args.arancel, prep=args.prep,
                precio_competencia=args.competencia, techo_demanda=args.techo,
                demo=args.demo)
    if args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(html_paquete(p))
        print(f"Paquete escrito en {args.html}")
    else:
        print(json.dumps(p, ensure_ascii=False, indent=2))
    return 0 if p.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
