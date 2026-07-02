#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_pitch.py — Genera pitch_inversor_fba.html desde el MISMO motor que el panel
(agents/portafolio.retorno_inversor), para que el pitch y el dashboard cuenten
exactamente la misma historia: comision reinvertida CON techo de demanda.

Uso:  python generar_pitch.py           (escribe pitch_inversor_fba.html)
      python generar_pitch.py --pct 10 --ticket 1000 --meses 24
"""
import argparse
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
if _AQUI not in sys.path:
    sys.path.insert(0, _AQUI)
from agents.portafolio import retorno_inversor  # noqa: E402

NAVY, NAVY2, GOLD = "#1e3a8a", "#152a63", "#d4af37"


def _svg_curva(filas, w=680, h=180):
    """Curva de comision mensual como SVG inline (sin dependencias)."""
    vals = [f["comision_mes"] for f in filas]
    if not vals or max(vals) <= 0:
        return ""
    mx = max(vals) * 1.15
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = 40 + i * (w - 60) / max(1, n - 1)
        y = h - 25 - (v / mx) * (h - 45)
        pts.append(f"{x:.1f},{y:.1f}")
    # linea de meseta teorica
    meseta = vals[-1]
    ym = h - 25 - (meseta / mx) * (h - 45)
    return f"""<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto">
      <line x1="40" y1="{h-25}" x2="{w-20}" y2="{h-25}" stroke="#cbd5e1" stroke-width="1"/>
      <line x1="40" y1="{ym:.1f}" x2="{w-20}" y2="{ym:.1f}" stroke="{GOLD}"
            stroke-width="1" stroke-dasharray="5,4" opacity=".7"/>
      <text x="{w-24}" y="{ym-6:.1f}" text-anchor="end" font-size="11"
            fill="{GOLD}" font-weight="700">meseta USD {meseta:,.0f}/mes</text>
      <polyline points="{' '.join(pts)}" fill="none" stroke="{NAVY}" stroke-width="2.5"/>
      <text x="40" y="{h-8}" font-size="11" fill="#64748b">mes 1</text>
      <text x="{w-20}" y="{h-8}" text-anchor="end" font-size="11" fill="#64748b">mes {n}</text>
    </svg>"""


def html_pitch(ticket=1000, pct=10.0, techo=290, precio=24.0, landed=5.5,
               meses=24, productos_financia=1.0):
    r = retorno_inversor(ticket, pct, techo, precio, landed, meses=meses,
                         productos_financia=productos_financia)
    fs, res = r["filas"], r["resumen"]
    hitos = [f for f in fs if f["mes"] in (2, 4, 6, 9, 12, 15, 18, 21, meses)]
    filas_html = "".join(
        f"<tr><td>Mes {f['mes']}</td><td>USD {f['comision_mes']:,.0f}</td>"
        f"<td>USD {f['capital']:,.0f}</td>"
        f"<td>{'USD %s ocioso' % format(f['ocioso'], ',.0f') if f['ocioso'] > 0 else 'productivo'}</td></tr>"
        for f in hitos)
    sat = (f"Su capital satura el techo en el <b>mes {res['mes_saturacion']}</b>; "
           f"desde ahi la comision se estabiliza en USD {res['comision_meseta']:,.0f}/mes."
           if res["mes_saturacion"] else
           "En este horizonte su capital no llega a saturar el techo.")
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Propuesta de inversion — FBA Operations</title>
<style>
 body{{font-family:'Segoe UI',Inter,system-ui,sans-serif;color:#0f172a;background:#f1f5f9;
      margin:0;padding:24px}}
 .wrap{{max-width:820px;margin:0 auto}}
 .hero{{background:linear-gradient(135deg,{NAVY},{NAVY2});color:#fff;border-radius:16px;
       padding:28px 30px;box-shadow:0 18px 40px -18px rgba(30,58,138,.6)}}
 .hero h1{{margin:0;font-size:26px}} .hero .g{{color:{GOLD};font-weight:800}}
 .hero p{{color:#c7d2fe;margin:6px 0 0;font-size:14px}}
 .card{{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px 22px;
       margin-top:16px;box-shadow:0 10px 26px -20px rgba(15,23,42,.35)}}
 h2{{font-size:17px;margin:0 0 10px;color:{NAVY};border-left:4px solid {GOLD};padding-left:10px}}
 table{{width:100%;border-collapse:collapse;font-size:14px}}
 th{{background:{NAVY};color:#fff;padding:8px 10px;text-align:left;font-weight:600}}
 td{{padding:8px 10px;border-bottom:1px solid #e2e8f0;font-variant-numeric:tabular-nums}}
 tr:nth-child(even) td{{background:#f8fafc}}
 ul{{margin:8px 0;padding-left:20px;line-height:1.7;font-size:14px}}
 .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}}
 .kpi{{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.18);
      border-radius:10px;padding:10px 12px}}
 .kpi b{{display:block;font-size:19px;color:{GOLD}}} .kpi span{{font-size:11px;color:#c7d2fe}}
 .aviso{{background:#fffbeb;border:1px solid #f59e0b;border-radius:12px;padding:14px 16px;
        font-size:13.5px;line-height:1.6}}
 .aviso b{{color:#92400e}}
 .pie{{color:#64748b;font-size:12px;text-align:center;margin:18px 0 4px}}
 @media print{{body{{background:#fff}} .card{{box-shadow:none}}}}
</style></head><body><div class="wrap">
 <div class="hero">
  <h1>FBA <span class="g">Operations</span> — Propuesta de inversion</h1>
  <p>Negocio Amazon FBA (mercado US, cocina eco). Ticket unico, retorno variable
     sobre facturacion del lote que financia su capital.</p>
  <div class="kpis">
   <div class="kpi"><b>USD {ticket:,.0f}</b><span>ticket unico (no mensual)</span></div>
   <div class="kpi"><b>{pct:.0f}%</b><span>de la facturacion de SU lote</span></div>
   <div class="kpi"><b>USD {res['comision_meseta']:,.0f}/mes</b><span>comision en meseta</span></div>
   <div class="kpi"><b>USD {res['capital_final']:,.0f}</b><span>capital al mes {meses}</span></div>
  </div>
 </div>

 <div class="card"><h2>Como funciona</h2><ul>
  <li>Su aporte de <b>USD {ticket:,.0f}</b> financia unidades de un lote concreto (trazable).</li>
  <li>Cobra <b>{pct:.0f}% de la facturacion bruta</b> de ese lote, verificable con el
      reporte mensual de ventas de Amazon.</li>
  <li>La comision se <b>reinvierte automaticamente</b>: compra mas unidades y su
      capital compone mes a mes.</li>
  <li>Salida sin penalidad desde el <b>mes 6</b>. Cupo de esta ronda: <b>3 inversores</b>.</li>
 </ul></div>

 <div class="card"><h2>Trayectoria proyectada (con techo de demanda)</h2>
  {_svg_curva(fs)}
  <table><tr><th>Periodo</th><th>Comision mensual</th><th>Capital acumulado</th><th>Estado del capital</th></tr>
  {filas_html}</table>
 </div>

 <div class="card"><div class="aviso"><b>Aviso honesto (leer antes de invertir):</b>
  este negocio tiene <b>techo de demanda</b>: un producto vende como maximo ~{techo} unidades/mes.
  {sat} El crecimiento posterior <b>no es exponencial</b>: solo continua si el capital
  financia un producto NUEVO (techo nuevo), lo que requiere validacion previa con una
  orden de prueba. Toda proyeccion esta sujeta al resultado real de esa validacion;
  el retorno es variable y no esta garantizado.</div></div>

 <div class="card"><h2>Garantias y transparencia</h2><ul>
  <li>Compra al proveedor via <b>Trade Assurance de Alibaba</b> (pago protegido por specs).</li>
  <li><b>Contrato privado</b> firmado entre las partes.</li>
  <li><b>Reporte mensual</b> de ventas exportado de Amazon Seller Central.</li>
  <li>Certificacion FDA del producto verificada antes de pagar al proveedor.</li>
 </ul></div>
 <div class="pie">Generado por FBA Operations — mismos numeros y mismo motor que el panel de control.</div>
</div></body></html>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Genera el pitch HTML honesto.")
    ap.add_argument("--ticket", type=float, default=1000)
    ap.add_argument("--pct", type=float, default=10.0)
    ap.add_argument("--techo", type=int, default=290)
    ap.add_argument("--precio", type=float, default=24.0)
    ap.add_argument("--landed", type=float, default=5.5)
    ap.add_argument("--meses", type=int, default=24)
    ap.add_argument("--productos", type=float, default=1.0)
    ap.add_argument("--out", default=os.path.join(_AQUI, "pitch_inversor_fba.html"))
    a = ap.parse_args(argv)
    html = html_pitch(a.ticket, a.pct, a.techo, a.precio, a.landed, a.meses, a.productos)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Pitch escrito en {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
