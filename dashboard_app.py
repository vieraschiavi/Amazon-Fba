#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard_app.py — Panel FBA (Streamlit 1.45.1), cockpit BI navy/verde.
Pipeline: Cerebro -> market_intel -> listing -> pricing -> caja -> ventas/analitica.
Sin datos inventados en produccion; Modo DEMO claramente etiquetado.
Correr: streamlit run dashboard_app.py
"""
import os
import sys

import pandas as pd
import streamlit as st

_AQUI = os.path.dirname(os.path.abspath(__file__))
if _AQUI not in sys.path:
    sys.path.insert(0, _AQUI)

import config
import styles as ui
from core import db
from agents.market_intel import market_intel
from agents.listing import generar as generar_listing
from agents.pricing import evaluar as evaluar_precio
from agents.capital_planner import proyeccion_realista
from agents import analytics
from agents import productos
from agents import asistente
from agents import glosario
from data import keepa

db.init()

st.set_page_config(page_title="MV Amazon FBA IA", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(ui.CSS, unsafe_allow_html=True)


def _cols_html(items):
    """Renderiza una fila de tarjetas HTML en columnas iguales."""
    cols = st.columns(len(items))
    for c, html in zip(cols, items):
        c.markdown(html, unsafe_allow_html=True)


# --- Sidebar ---
with st.sidebar:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px'>{ui.logo(30, on_dark=False)}"
        f"<div style='font-weight:800;color:{ui.NAVY};font-size:17px;line-height:1.1'>"
        f"{ui.BRAND_PREFIX} <span style='color:{ui.GREEN}'>{ui.BRAND_ACCENT}</span></div></div>",
        unsafe_allow_html=True)
    st.caption(ui.TAGLINE)
    st.divider()
    demo = st.toggle("Modo DEMO", value=True,
                     help="Datos [DEMO] ilustrativos. Apagar para usar CSV real de Cerebro.")
    cfg = config.estado_config()
    st.markdown(ui.seccion("Conexiones"), unsafe_allow_html=True)
    st.markdown(
        ui.badge("Claude" if config.ANTHROPIC_API_KEY else "Listing offline",
                 "verde" if config.ANTHROPIC_API_KEY else "navy") +
        " " + ui.badge("Keepa" if config.KEEPA_API_KEY else "Keepa sin clave",
                       "verde" if config.KEEPA_API_KEY else "amarillo"),
        unsafe_allow_html=True)
    st.markdown(
        ui.badge("Email real" if (config.SMTP_USER and config.SMTP_PASS) else "Email dry-run",
                 "verde" if (config.SMTP_USER and config.SMTP_PASS) else "amarillo"),
        unsafe_allow_html=True)
    st.caption(f"Alertas a {config.ALERT_TO}")
    if demo:
        st.warning("MODO DEMO activo: datos ilustrativos, no reales.")

# --- Brand header ---
st.markdown(ui.header(
    subtitulo="Investigacion, pricing, portafolio y caja para Amazon FBA — mercado US",
    chips=[("DEMO" if demo else "Produccion", not demo),
           ("Keepa", bool(config.KEEPA_API_KEY)),
           ("Claude", bool(config.ANTHROPIC_API_KEY)),
           ("Email", bool(config.SMTP_USER and config.SMTP_PASS))]),
    unsafe_allow_html=True)

tabs = st.tabs(["  Investigacion  ", "  Pricing  ", "  Portafolio  ", "  Caja  ",
                "  Ventas  ", "  Inversores  ", "  Plan  ", "  Alertas  ", "  Config  ",
                "  Asistente IA  ", "  Ayuda  "])

# ============================ 1) INVESTIGACION ============================ #
with tabs[0]:
    st.markdown(ui.seccion("Investigacion de nicho",
                           "Cerebro -> score de nicho -> veredicto -> listing"),
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    keyword = c1.text_input("Nicho / keyword principal", value="bamboo kitchen utensils")
    correr = c2.button("Investigar", type="primary", use_container_width=True)
    up = st.file_uploader("O subi un export CSV de Helium 10 Cerebro", type=["csv"])
    csv_path = None
    if up is not None:
        os.makedirs(config.CEREBRO_CSV_DIR, exist_ok=True)
        csv_path = os.path.join(config.CEREBRO_CSV_DIR, up.name)
        with open(csv_path, "wb") as f:
            f.write(up.getbuffer())
        st.success(f"CSV recibido: {up.name}")

    if correr or up is not None:
        mi = market_intel(keyword, config.MARKETPLACE, csv_path=csv_path, demo=demo)
        if not mi["ok"]:
            st.info(mi["comentario"])
        else:
            tono = {"VERDE": "verde", "AMARILLO": "amarillo", "ROJO": "rojo"}.get(
                mi["veredicto"], "navy")
            _cols_html([
                ui.kpi("Demanda / mes", ui.fmt_int(mi["demanda_mensual"]), "unidades estimadas"),
                ui.kpi("Competidores", ui.fmt_int(mi["competidores"]), "menos es mejor"),
                ui.kpi("Oportunidad", f"{mi['oportunidad_valor']}/100", "hueco de valor"),
                ui.kpi("Score nicho", f"{mi['score_nicho']}/100", "ganabilidad", hero=True),
            ])
            st.markdown(ui.badge(f"Veredicto: {mi['veredicto']}", tono), unsafe_allow_html=True)
            st.caption(mi["comentario"])
            st.divider()
            st.markdown(ui.seccion("Listing sugerido", "Copy en ingles (mercado US)"),
                        unsafe_allow_html=True)
            li = generar_listing(keyword, config.MARKETPLACE, csv_path=csv_path, demo=demo)
            st.text_input("Titulo", value=li["titulo"], key="li_tit")
            for i, b in enumerate(li["bullets"], 1):
                st.markdown(f"**{i}.** {b}")
            st.text_area("Descripcion", value=li["descripcion"], height=120, key="li_desc")
            st.caption(f"Banner brief: {li['banner_brief']}  ·  Motor: {li['_motor']}")
    else:
        st.caption("Escribi un nicho y toca Investigar (o subi un CSV de Cerebro).")

# ============================ 2) PRICING ============================ #
with tabs[1]:
    st.markdown(ui.seccion("Pricing", "Costo desembarcado -> precio -> margen -> ROI"),
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    costo = c1.number_input("Costo unitario (USD)", value=2.10, min_value=0.0, step=0.10)
    flete = c2.number_input("Flete unitario (USD)", value=0.80, min_value=0.0, step=0.10)
    arancel = c3.number_input("Arancel (%)", value=6.0, min_value=0.0, step=0.5)
    c4, c5, c6 = st.columns(3)
    prep = c4.number_input("Prep (USD)", value=0.50, min_value=0.0, step=0.10)
    fba = c5.number_input("FBA fee (USD)", value=config.FBA_FEE_DEFAULT, min_value=0.0, step=0.10)
    comp = c6.number_input("Precio competencia (USD, 0=sin)", value=19.99, min_value=0.0, step=0.50)
    prod = {"costo": costo, "flete": flete, "arancel_pct": arancel, "prep": prep}
    m = evaluar_precio(prod, fba_fee=fba, precio_competencia=(comp if comp > 0 else None))
    tono = {"verde": "good", "amarillo": "warn", "rojo": "bad"}[m["semaforo"]]
    _cols_html([
        ui.kpi("Landed cost", ui.fmt_money(m["landed"]), "costo desembarcado"),
        ui.kpi("Precio sugerido", ui.fmt_money(m["precio"]), m["estrategia"], hero=True),
        ui.kpi("Margen", ui.fmt_pct(m["margen_pct"]), "neto / precio", tone=tono),
        ui.kpi("ROI", ui.fmt_pct(m["roi_pct"]), "neto / landed"),
    ])
    st.markdown(
        ui.badge(f"Semaforo: {m['semaforo'].upper()}", m["semaforo"]) +
        f"&nbsp;&nbsp;<span style='color:#475569;font-size:13px'>Break-even "
        f"{ui.usd(m['break_even'])} · Neto/unidad {ui.usd(m['neto'])}</span>",
        unsafe_allow_html=True)
    st.divider()
    with st.expander("Guardar este producto en el portafolio"):
        g1, g2, g3 = st.columns(3)
        g_nombre = g1.text_input("Nombre del producto", key="pr_g_nombre",
                                 placeholder="Bamboo utensil set 12pc")
        g_asin = g2.text_input("ASIN (si ya existe)", key="pr_g_asin")
        g_techo = g3.number_input("Techo de demanda (u/mes)", value=290, min_value=0,
                                  step=10, key="pr_g_techo")
        if st.button("Guardar en portafolio", type="primary", key="pr_g_btn"):
            r = productos.guardar(g_nombre, asin=g_asin, costo=costo, flete=flete,
                                  arancel_pct=arancel, prep=prep, fba_fee=fba,
                                  precio_competencia=(comp if comp > 0 else None),
                                  techo_demanda=int(g_techo))
            if r["ok"]:
                st.success(r["mensaje"] + " Velo en la pestana Portafolio.")
            else:
                st.error(r["mensaje"])

# ============================ 3) PORTAFOLIO ============================ #
with tabs[2]:
    st.markdown(ui.seccion("Portafolio de productos",
                           "El negocio producto a producto: proyectado vs real"),
                unsafe_allow_html=True)

    with st.expander("Agregar producto al portafolio"):
        with st.form("alta_producto"):
            a1, a2, a3 = st.columns(3)
            n_nombre = a1.text_input("Nombre *", key="pf_a_nombre")
            n_asin = a2.text_input("ASIN", key="pf_a_asin")
            n_techo = a3.number_input("Techo demanda (u/mes)", value=290, min_value=0,
                                      step=10, key="pf_a_techo")
            a4, a5, a6, a7 = st.columns(4)
            n_costo = a4.number_input("Costo (USD)", value=2.10, min_value=0.0,
                                      step=0.10, key="pf_a_costo")
            n_flete = a5.number_input("Flete (USD)", value=0.80, min_value=0.0,
                                      step=0.10, key="pf_a_flete")
            n_aran = a6.number_input("Arancel (%)", value=6.0, min_value=0.0,
                                     step=0.5, key="pf_a_aran")
            n_prep = a7.number_input("Prep (USD)", value=0.50, min_value=0.0,
                                     step=0.10, key="pf_a_prep")
            a8, a9 = st.columns(2)
            n_fba = a8.number_input("FBA fee (USD)", value=config.FBA_FEE_DEFAULT,
                                    min_value=0.0, step=0.10, key="pf_a_fba")
            n_comp = a9.number_input("Precio competencia (USD, 0=sin)", value=0.0,
                                     min_value=0.0, step=0.50, key="pf_a_comp")
            alta_ok = st.form_submit_button("Agregar al portafolio", type="primary")
        if alta_ok:
            r_alta = productos.guardar(n_nombre, asin=n_asin, costo=n_costo,
                                       flete=n_flete, arancel_pct=n_aran, prep=n_prep,
                                       fba_fee=n_fba,
                                       precio_competencia=(n_comp if n_comp > 0 else None),
                                       techo_demanda=int(n_techo))
            (st.success if r_alta["ok"] else st.error)(r_alta["mensaje"])

    rp = productos.resumen_portafolio()
    if rp["n_productos"] == 0:
        st.info("Portafolio vacio. Calcula un producto en Pricing y toca "
                "'Guardar en portafolio', o cargalo con el formulario de arriba.")
    else:
        sem = rp["semaforos"]
        _cols_html([
            ui.kpi("Productos activos", str(rp["n_productos"]),
                   f"{sem['verde']} verde / {sem['amarillo']} amarillo / {sem['rojo']} rojo"),
            ui.kpi("Sueldo meseta proyectado", ui.fmt_money(rp["sueldo_meseta_proyectado"]),
                   "suma de techo x neto (con devoluciones)", hero=True),
            ui.kpi("Capital en pipeline", ui.fmt_money(rp["capital_pipeline_total"]),
                   "~4 meses de stock por producto"),
            ui.kpi("Ventas reales", ui.fmt_money(rp["ingreso_real"]),
                   f"neto {ui.usd(rp['neto_real'])}",
                   tone=("good" if rp["neto_real"] > 0 else "navy")),
        ])
        dfp = pd.DataFrame(rp["productos"])[[
            "id", "nombre", "asin", "landed", "precio", "neto", "margen", "roi",
            "semaforo", "techo_demanda", "capital_pipeline",
            "sueldo_meseta_teorico", "ventas_ingreso", "ventas_unidades"]]
        dfp.columns = ["ID", "Producto", "ASIN", "Landed", "Precio", "Neto/u",
                       "Margen %", "ROI %", "Semaforo", "Techo u/mes",
                       "Capital pipeline", "Sueldo meseta", "Ventas USD", "Unid."]
        st.dataframe(dfp, use_container_width=True, hide_index=True)
        st.download_button("Exportar portafolio (CSV)",
                           data=dfp.to_csv(index=False).encode("utf-8"),
                           file_name="portafolio_fba.csv", mime="text/csv")

        st.divider()
        st.markdown(ui.seccion("Analisis financiero por producto",
                               "Unit economics + proyeccion de caja + ventas reales"),
                    unsafe_allow_html=True)
        opciones = {f"#{p['id']} — {p['nombre']}": p["id"] for p in rp["productos"]}
        sel = st.selectbox("Producto", list(opciones.keys()), key="pf_sel")
        an = productos.analisis(opciones[sel])
        if an["ok"]:
            ue, vr = an["unit_economics"], an["ventas_reales"]
            tono_p = {"verde": "good", "amarillo": "warn", "rojo": "bad"}[ue["semaforo"]]
            _cols_html([
                ui.kpi("Precio", ui.fmt_money(ue["precio"]), ue["estrategia"]),
                ui.kpi("Margen", ui.fmt_pct(ue["margen_pct"]), "neto / precio", tone=tono_p),
                ui.kpi("ROI", ui.fmt_pct(ue["roi_pct"]), "neto / landed"),
                ui.kpi("Capital pipeline", ui.fmt_money(an["capital_pipeline"]),
                       "para sostener el techo"),
            ])
            if an["proyeccion"]:
                res_p = an["proyeccion"]["resumen"]
                _cols_html([
                    ui.kpi("Sueldo en meseta", ui.fmt_money(res_p["sueldo_meseta"]),
                           "proyectado 12 meses", hero=True),
                    ui.kpi("Caja minima", ui.fmt_money(res_p["caja_minima"]),
                           "colchon del producto",
                           tone=("bad" if res_p["caja_minima"] < 0 else "good")),
                    ui.kpi("Primer cobro", f"mes {res_p['mes_primer_cobro']}",
                           "lead time + DD+7"),
                    ui.kpi("Ventas reales", ui.fmt_money(vr["ingreso"]),
                           f"{ui.fmt_int(vr['unidades'])} unidades en "
                           f"{ui.fmt_int(vr['ordenes'])} ordenes",
                           tone=("good" if vr["ingreso"] > 0 else "navy")),
                ])
                dfa = pd.DataFrame(an["proyeccion"]["filas"])
                st.line_chart(dfa.set_index("mes")[["caja", "sueldo"]], height=220,
                              color=["#1e3a8a", "#8bc34a"])
            if vr["ordenes"]:
                st.markdown(ui.seccion("Ultimas ventas del producto"),
                            unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(vr["ultimas"]), use_container_width=True,
                             hide_index=True)
            else:
                st.caption("Sin ventas registradas para este ASIN todavia "
                           "(registralas en Ventas o via API /webhook/sale).")
            if st.button("Quitar del portafolio (baja logica)", key="pf_del"):
                productos.desactivar(opciones[sel])
                st.rerun()

# ============================ 4) CAJA ============================ #
with tabs[3]:
    st.markdown(ui.seccion("Proyeccion realista de caja",
                           "Con lead time, DD+7, devoluciones y techo de demanda"),
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    budget = c1.number_input("Capital (USD)", value=8000, min_value=0, step=500)
    landed_in = c2.number_input("Landed/unidad (USD)", value=5.50, min_value=0.0, step=0.10)
    precio_in = c3.number_input("Precio venta (USD)", value=24.0, min_value=0.0, step=0.50)
    c4, c5, c6 = st.columns(3)
    net_in = c4.number_input("Neto/unidad (USD)", value=6.90, min_value=0.0, step=0.10)
    techo = c5.number_input("Techo demanda (unid/mes)", value=290, min_value=0, step=10)
    meses = c6.number_input("Meses", value=12, min_value=1, step=1)
    r = proyeccion_realista(budget, landed_in, precio_in, net_in,
                            techo_demanda=int(techo), meses=int(meses))
    res = r["resumen"]
    caja_tone = "bad" if res["caja_minima"] < 0 else ("warn" if res["caja_minima"] < budget * 0.05 else "good")
    _cols_html([
        ui.kpi("Sueldo en meseta", ui.fmt_money(res["sueldo_meseta"]),
               "neto sostenido por mes", hero=True),
        ui.kpi("Caja minima", ui.fmt_money(res["caja_minima"]), "colchon de efectivo", tone=caja_tone),
        ui.kpi("Primer cobro", f"mes {res['mes_primer_cobro']}", "lead time + DD+7"),
        ui.kpi("Capital invertido", ui.fmt_money(res["inversion"]),
               f"{ui.fmt_int(res['unidades_compra'])} unidades"),
    ])
    if res["caja_minima"] < 0:
        st.error(res["alerta"] + ". Bajá el techo, subí el capital o achicá la primera compra.")
    elif res["caja_minima"] < budget * 0.05:
        st.warning("Caja minima muy ajustada: estas fronteando casi todo el capital en stock.")
    df = pd.DataFrame(r["filas"])
    st.markdown(ui.seccion("Evolucion mensual"), unsafe_allow_html=True)
    st.line_chart(df.set_index("mes")[["caja", "sueldo"]], height=240,
                  color=["#1e3a8a", "#8bc34a"])
    st.dataframe(df[["mes", "vendidas", "cobrado", "sueldo", "caja", "capital_atado"]],
                 use_container_width=True, hide_index=True)

# ============================ 5) VENTAS ============================ #
with tabs[4]:
    st.markdown(ui.seccion("Ventas y KPIs", "Registra una venta y segui el mix"),
                unsafe_allow_html=True)
    with st.form("venta"):
        c1, c2, c3 = st.columns(3)
        asin = c1.text_input("ASIN", value="B0DEMO123")
        unid = c2.number_input("Unidades", value=5, min_value=0, step=1)
        pventa = c3.number_input("Precio (USD)", value=24.0, min_value=0.0, step=0.5)
        c4, c5, c6 = st.columns(3)
        netou = c4.number_input("Neto/unidad (USD)", value=6.9, min_value=0.0, step=0.1)
        pais = c5.text_input("Pais", value="US")
        seg = c6.text_input("Segmento", value="hogar")
        ok = st.form_submit_button("Registrar venta", type="primary")
    if ok:
        rv = analytics.registrar_venta(asin, int(unid), pventa, netou, pais=pais,
                                       segmento=seg, alertar=True)
        st.success(f"Venta registrada. Facturacion {ui.usd(rv['ingreso'])} · "
                   f"Neto {ui.usd(rv['neto'])} (alerta -> {config.ALERT_TO})")
    k = analytics.kpis()
    _cols_html([
        ui.kpi("Facturacion", ui.fmt_money(k["facturacion"]), "acumulada", hero=True),
        ui.kpi("Neto", ui.fmt_money(k["neto"]), "despues de costos"),
        ui.kpi("Margen global", ui.fmt_pct(k["margen_global_pct"]), "neto / facturacion",
               tone=("good" if k["margen_global_pct"] >= 25 else "warn" if k["margen_global_pct"] >= 12 else "bad")),
        ui.kpi("Ordenes", ui.fmt_int(k["ordenes"]), f"{ui.fmt_int(k['unidades'])} unidades"),
    ])
    if k["por_producto"]:
        st.markdown(ui.seccion("Mix por producto"), unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame(k["por_producto"]).set_index("k")["ingreso"], height=220,
                     color="#1e3a8a")
        cca, ccb = st.columns(2)
        if k["por_pais"]:
            cca.markdown(ui.seccion("Por pais"), unsafe_allow_html=True)
            cca.dataframe(pd.DataFrame(k["por_pais"]), use_container_width=True, hide_index=True)
        if k["por_segmento"]:
            ccb.markdown(ui.seccion("Por segmento"), unsafe_allow_html=True)
            ccb.dataframe(pd.DataFrame(k["por_segmento"]), use_container_width=True, hide_index=True)
    else:
        st.caption("Aun no hay ventas registradas.")

# ============================ 6) INVERSORES ============================ #
with tabs[5]:
    from agents.capital_planner import escenario_inversor
    st.markdown(ui.seccion("Escenario con inversor",
                "Comision = % variable de facturacion sobre la parte que financia su capital"),
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    cap_propio = c1.number_input("Capital propio (USD)", value=10000, min_value=0, step=500, key="iv_cap")
    cap_inv = c2.number_input("Capital del inversor (USD)", value=1000, min_value=0, step=250, key="iv_capinv")
    pct = c3.slider("Comision inversor (% de facturacion)", 3, 15, 10, key="iv_pct")
    c4, c5, c6, c7 = st.columns(4)
    techo_i = c4.number_input("Techo/producto (u/mes)", value=290, min_value=0, step=10, key="iv_techo")
    precio_i = c5.number_input("Precio (USD)", value=24.0, min_value=0.0, step=0.5, key="iv_precio")
    net_i = c6.number_input("Neto/unidad (USD)", value=6.9, min_value=0.0, step=0.1, key="iv_net")
    landed_i = c7.number_input("Landed/unidad (USD)", value=5.5, min_value=0.0, step=0.1, key="iv_landed")

    def _col_prod(n):
        e = escenario_inversor(cap_propio, n, int(techo_i), precio_i, net_i, landed_i,
                               capital_inversor=cap_inv, pct_facturacion=pct)
        if e["delta"] > 5:
            tono, verd = "verde", f"El inversor te SUMA USD {e['delta']:,}/mes"
        elif e["delta"] < -5:
            tono, verd = "rojo", f"El inversor te RESTA USD {abs(e['delta']):,}/mes"
        else:
            tono, verd = "amarillo", "El inversor te deja casi igual"
        cuello = ("techo de demanda (te sobra capital)" if e["cuello"] == "demanda"
                  else "capital (podes colocar mas plata)")
        dsig = ("+" if e["delta"] >= 0 else "-") + "$" + f"{abs(e['delta']):,.0f}"
        html = (ui.kpi(f"Tu sueldo ({n} prod)", ui.fmt_money(e["sueldo_martin"]),
                       "neto mensual en meseta", hero=True)
                + ui.kpi("Comision inversor", ui.fmt_money(e["comision_inversor"]),
                         f"{e['retorno_inversor_mes_pct']}%/mes sobre su capital", tone="warn")
                + ui.kpi("Vs. sin inversor", dsig, "cuanto te cambia",
                         tone=("good" if e["delta"] >= 0 else "bad"))
                + ui.kpi("Cuello de botella", e["cuello"].upper(), cuello))
        return html, verd, tono

    cc1, cc2 = st.columns(2)
    for col, n in ((cc1, 1), (cc2, 2)):
        html, verd, tono = _col_prod(n)
        col.markdown(ui.seccion(f"{n} producto" + ("s" if n > 1 else "")),
                     unsafe_allow_html=True)
        col.markdown(html, unsafe_allow_html=True)
        col.markdown(ui.badge(verd, tono), unsafe_allow_html=True)

    st.divider()
    st.caption("Clave honesta: el inversor solo te SUMA cuando el cuello es CAPITAL "
               "(no te alcanza para llenar los techos de demanda). Si el cuello es DEMANDA, "
               "su plata no agrega ventas: comparte tu techo y te cobra comision, entonces "
               "te RESTA. Por eso su capital tiene sentido para financiar el 2do producto, "
               "no el 1ro que ya bancas solo. Mantene la comision en un digito.")

    st.divider()
    st.markdown(ui.seccion("Trayectoria del inversor (pitch honesto)",
                "Comision reinvertida con techo de demanda: crece, satura y se aplana"),
                unsafe_allow_html=True)
    t1, t2, t3 = st.columns(3)
    ticket = t1.number_input("Ticket del inversor (USD)", value=1000, min_value=0, step=250, key="tr_ticket")
    horizonte = t2.number_input("Horizonte (meses)", value=24, min_value=1, step=6, key="tr_meses")
    prods_fin = t3.selectbox("Productos que financia su capital", [1, 2], key="tr_prods",
                             help="2 = cuando el producto 1 satura, su capital entra al producto 2 "
                                  "(techo nuevo). Es el unico camino real de crecimiento post-saturacion.")
    from agents.portafolio import retorno_inversor
    tr = retorno_inversor(ticket, float(pct), int(techo_i), precio_i, landed_i,
                          meses=int(horizonte), productos_financia=float(prods_fin))
    rt = tr["resumen"]
    _cols_html([
        ui.kpi("Comision inicial", ui.fmt_money(rt["comision_inicial"]) ,
               "primer mes con ventas", tone="navy"),
        ui.kpi("Comision en meseta", ui.fmt_money(rt["comision_meseta"]),
               "tope por techo de demanda", hero=True),
        ui.kpi("Satura en", f"mes {rt['mes_saturacion']}" if rt["mes_saturacion"] else "no satura",
               f"capital productivo max {ui.usd(rt['capital_max_productivo'])}",
               tone=("warn" if rt["mes_saturacion"] else "navy")),
        ui.kpi("Capital acumulado", ui.fmt_money(rt["capital_final"]),
               f"x{rt['multiplicador']} | ocioso {ui.usd(rt['capital_ocioso_final'])}",
               tone=("good" if rt["capital_ocioso_final"] == 0 else "warn")),
    ])
    dtr = pd.DataFrame(tr["filas"])
    g1, g2 = st.columns(2)
    g1.markdown(ui.seccion("Capital del inversor"), unsafe_allow_html=True)
    g1.line_chart(dtr.set_index("mes")[["capital", "productivo"]], height=220,
                  color=["#1e3a8a", "#8bc34a"])
    g2.markdown(ui.seccion("Comision mensual"), unsafe_allow_html=True)
    g2.line_chart(dtr.set_index("mes")[["comision_mes"]], height=220, color=["#d4af37"])
    st.caption("La curva se aplana cuando su lote satura el techo: de ahi en mas la comision "
               "reinvertida queda ociosa salvo que financie un producto NUEVO. Cualquier pitch "
               "que muestre crecimiento exponencial sin tope esta mintiendo.")
    import generar_pitch
    st.download_button("Descargar pitch HTML (mismos numeros)",
                       data=generar_pitch.html_pitch(ticket=ticket, pct=float(pct),
                                                     techo=int(techo_i), precio=precio_i,
                                                     landed=landed_i, meses=int(horizonte),
                                                     productos_financia=float(prods_fin)),
                       file_name="pitch_inversor_fba.html", mime="text/html")

# ============================ 7) PLAN ============================ #
with tabs[6]:
    from agents.portafolio import interes_compuesto, recomendar_portafolio

    st.markdown(ui.seccion("Recomendacion de portafolio",
                "Cuantos productos, con que capital y en que mes llegas a tu objetivo"),
                unsafe_allow_html=True)
    p1, p2, p3 = st.columns(3)
    objetivo = p1.number_input("Objetivo de ingreso (USD/mes)", value=2500, min_value=0, step=100, key="pf_obj")
    cap_pf = p2.number_input("Capital propio (USD)", value=10000, min_value=0, step=500, key="pf_cap")
    usar_inv = p3.toggle("Usar inversores para acelerar", value=False, key="pf_inv")
    p4, p5, p6, p7 = st.columns(4)
    techo_pf = p4.number_input("Techo/producto (u/mes)", value=290, min_value=0, step=10, key="pf_techo")
    precio_pf = p5.number_input("Precio (USD)", value=24.0, min_value=0.0, step=0.5, key="pf_precio")
    net_pf = p6.number_input("Neto/unidad (USD)", value=6.9, min_value=0.0, step=0.1, key="pf_net")
    pct_pf = p7.slider("Comision inversores (% fact.)", 3, 15, 5, key="pf_pct",
                       disabled=not usar_inv)

    rp = recomendar_portafolio(objetivo, cap_pf, techo=int(techo_pf), precio=precio_pf,
                               net_unit=net_pf, usar_inversores=usar_inv,
                               pct_comision=float(pct_pf))
    if not rp["ok"]:
        st.error(rp["mensaje"])
    else:
        _cols_html([
            ui.kpi("Productos necesarios", str(rp["n_productos"]),
                   f"{ui.usd(rp['sueldo_por_producto'])}/mes c/u en meseta", hero=True),
            ui.kpi("Llegas al objetivo", f"mes {rp['mes_objetivo']}" if rp["alcanzado"]
                   else "NO en 6 productos",
                   "secuencial, validando c/u",
                   tone=("good" if rp["alcanzado"] else "bad")),
            ui.kpi("Capital propio usado", ui.fmt_money(rp["capital_propio_usado"]),
                   f"{ui.usd(rp['capital_por_producto'])} por producto"),
            ui.kpi("Capital de inversores", ui.fmt_money(rp["capital_inversores"]),
                   "solo si acelera", tone=("warn" if rp["capital_inversores"] > 0 else "navy")),
        ])
        st.markdown(ui.seccion("Plan producto a producto"), unsafe_allow_html=True)
        dfp = pd.DataFrame(rp["plan"])
        dfp.columns = ["Producto", "Fuente", "Capital", "Capital inversor",
                       "Sueldo que aporta", "Mes meseta", "Ingreso acumulado"]
        st.dataframe(dfp, use_container_width=True, hide_index=True)
        st.caption(rp["advertencia"])

    st.divider()
    st.markdown(ui.seccion("Calculadora de reinversion compuesta",
                "Aportando X por mes o anio a tasa Y durante Z anios, cuanto tenes"),
                unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    ap_ini = q1.number_input("Aporte inicial (USD)", value=10000, min_value=0, step=500, key="ic_ini")
    ap_per = q2.number_input("Aporte periodico (USD)", value=500, min_value=0, step=100, key="ic_per")
    frec = q3.selectbox("Frecuencia del aporte", ["mensual", "anual"], key="ic_frec")
    q4, q5, q6 = st.columns(3)
    tasa = q4.number_input("Tasa efectiva anual (%)", value=12.0, min_value=0.0, step=0.5, key="ic_tasa")
    anios = q5.number_input("Anios", value=10, min_value=1, step=1, key="ic_anios")
    techo_cap = q6.number_input("Techo de capital productivo (USD, 0=sin techo)",
                                value=0, min_value=0, step=1000, key="ic_techo",
                                help="En FBA el capital solo rinde mientras la demanda lo absorbe; "
                                     "el excedente queda ocioso. 0 = tasa fija clasica.")
    ic = interes_compuesto(ap_ini, ap_per, tasa, int(anios), frec, techo_capital=techo_cap)
    ric = ic["resumen"]
    _cols_html([
        ui.kpi("Capital final", ui.fmt_money(ric["capital_final"]),
               f"en {int(anios)} anios", hero=True),
        ui.kpi("Total aportado", ui.fmt_money(ric["total_aportado"]), "tu plata puesta"),
        ui.kpi("Ganancia generada", ui.fmt_money(ric["ganancia"]),
               f"x{ric['multiplicador']} sobre lo aportado",
               tone=("good" if ric["ganancia"] > 0 else "navy")),
        ui.kpi("Capital ocioso al final", ui.fmt_money(ric["capital_ocioso_final"]),
               "no rinde por el techo",
               tone=("warn" if ric["capital_ocioso_final"] > 0 else "navy")),
    ])
    dfc = pd.DataFrame(ic["filas"])
    if not dfc.empty:
        st.line_chart(dfc.set_index("mes")[["capital", "aportado"]], height=240,
                      color=["#1e3a8a", "#8bc34a"])
        df_an = dfc[dfc["mes"] % 12 == 0][["anio", "capital", "aportado", "ocioso"]]
        st.dataframe(df_an, use_container_width=True, hide_index=True)
    st.caption("Honesto: la tasa fija compuesta es matematica de folleto. En FBA el rendimiento "
               "es alto sobre el capital desplegado, pero el techo de demanda corta la "
               "capitalizacion: mas plata no rinde si el nicho no la absorbe. Usa el techo "
               "para ver tu curva real; la exponencial pura solo aplica a instrumentos "
               "financieros sin tope de colocacion.")

# ============================ 8) ALERTAS ============================ #
with tabs[7]:
    st.markdown(ui.seccion("Alertas", "Sin SMTP, quedan en dry-run (registradas, no enviadas)"),
                unsafe_allow_html=True)
    outbox = db.rows("SELECT fecha,asunto,para,enviado FROM alerts_outbox ORDER BY id DESC LIMIT 50")
    if outbox:
        df = pd.DataFrame(outbox)
        df["estado"] = df["enviado"].map({1: "ENVIADO", 0: "dry-run"})
        st.dataframe(df[["fecha", "asunto", "para", "estado"]],
                     use_container_width=True, hide_index=True)
    else:
        st.caption("Sin alertas todavia.")

# ============================ 9) CONFIG ============================ #
with tabs[8]:
    st.markdown(ui.seccion("Configuracion y conexiones",
                           "Estado actual y verificacion en vivo"), unsafe_allow_html=True)
    st.json(config.estado_config())
    st.markdown(ui.seccion("Probar conexiones"), unsafe_allow_html=True)
    asin_test = st.text_input("ASIN para probar Keepa (opcional, gasta 1 token)", value="")
    if st.button("Probar conexiones", type="primary"):
        import test_conexiones as tc
        for f in tc.verificar_todo(asin_test.strip() or None):
            if f["estado"] == tc.OK:
                st.success(f"{f['nombre']}: {f['detalle']}")
            elif f["estado"] == tc.FALLA:
                st.error(f"{f['nombre']}: {f['detalle']}")
            else:
                st.warning(f"{f['nombre']}: {f['detalle']}")
    st.markdown(ui.seccion("Claves de API",
                           "Se guardan cifradas por tu sistema de archivos en .env "
                           "(fuera de git); aca nunca se muestran completas"),
                unsafe_allow_html=True)
    st.caption("Estado actual — "
               f"KEEPA_API_KEY: {config.mask(config.KEEPA_API_KEY)} · "
               f"ANTHROPIC_API_KEY: {config.mask(config.ANTHROPIC_API_KEY)} · "
               f"SMTP_USER: {config.mask(config.SMTP_USER)} · "
               f"SMTP_PASS: {config.mask(config.SMTP_PASS)}")
    with st.form("form_claves"):
        k1, k2 = st.columns(2)
        in_keepa = k1.text_input("KEEPA_API_KEY", type="password",
                                 help="keepa.com -> Keepa API -> Private API access key")
        in_anth = k2.text_input("ANTHROPIC_API_KEY", type="password",
                                help="console.anthropic.com -> API Keys")
        k3, k4, k5 = st.columns(3)
        in_su = k3.text_input("SMTP_USER (Gmail)", key="cf_smtp_user")
        in_sp = k4.text_input("SMTP_PASS (App Password)", type="password",
                              key="cf_smtp_pass")
        in_to = k5.text_input("ALERT_TO (destino de alertas)", value=config.ALERT_TO,
                              key="cf_alert_to")
        guardar_claves = st.form_submit_button("Guardar claves", type="primary")
    if guardar_claves:
        r_env = config.guardar_env(KEEPA_API_KEY=in_keepa, ANTHROPIC_API_KEY=in_anth,
                                   SMTP_USER=in_su, SMTP_PASS=in_sp,
                                   ALERT_TO=(in_to if in_to != config.ALERT_TO else ""))
        if r_env["ok"]:
            import importlib
            importlib.reload(config)
            st.success(r_env["mensaje"] + " (" + ", ".join(r_env["guardadas"]) + "). "
                       "Solo se sobreescriben los campos que completaste.")
        else:
            st.info(r_env["mensaje"] + " Completa al menos un campo.")
    st.caption(f"Archivo: {config.ENV_PATH} — esta en .gitignore y nunca se sube al "
               "repositorio. Tambien podes editarlo a mano (plantilla: .env.example).")
    st.caption("Helium 10 no tiene API en Platinum: keywords por CSV de Cerebro. "
               "Keepa es la fuente programatica de precio + BSR.")

# ============================ 10) ASISTENTE IA ============================ #
with tabs[9]:
    st.markdown(ui.seccion("Asistente IA (Claude)",
                           "Pregunta sobre tus metricas, tu portafolio o la estrategia FBA"),
                unsafe_allow_html=True)
    est = asistente.estado()
    st.markdown(ui.badge("Claude conectado" if est["ok"] else "Modo offline (glosario)",
                         "verde" if est["ok"] else "amarillo"), unsafe_allow_html=True)
    st.caption(est["mensaje"])

    if "chat_hist" not in st.session_state:
        st.session_state.chat_hist = []

    ej1, ej2, ej3 = st.columns(3)
    sugerencias = ["Como venia mi negocio segun mis ventas?",
                   "Que producto de mi portafolio conviene escalar?",
                   "Que es el techo de demanda y por que importa?"]
    disparo = None
    for col, txt in zip((ej1, ej2, ej3), sugerencias):
        if col.button(txt, use_container_width=True, key="sug_" + txt[:10]):
            disparo = txt

    for m in st.session_state.chat_hist:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    pregunta = st.chat_input("Escribi tu pregunta sobre el negocio...")
    pregunta = pregunta or disparo
    if pregunta:
        st.session_state.chat_hist.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                r = asistente.responder(pregunta, st.session_state.chat_hist[:-1])
            st.markdown(r["texto"])
        st.session_state.chat_hist.append({"role": "assistant", "content": r["texto"]})

    if st.session_state.chat_hist:
        if st.button("Limpiar conversacion", key="chat_clear"):
            st.session_state.chat_hist = []
            st.rerun()
    st.caption("El asistente usa tus datos reales (ventas, portafolio) como contexto y "
               "respeta los principios honestos del sistema. No es consejo financiero "
               "garantizado: el retorno FBA es variable.")

# ============================ 11) AYUDA ============================ #
with tabs[10]:
    st.markdown(ui.seccion("Ayuda y glosario",
                           "Los conceptos de FBA y finanzas que usa el sistema, en criollo"),
                unsafe_allow_html=True)

    st.markdown(ui.seccion("Como empezar (3 pasos)"), unsafe_allow_html=True)
    st.markdown(
        "1. **Investiga** un nicho (o subi un CSV de Cerebro) y mira el score y el veredicto.\n"
        "2. **Calcula el pricing** con tus costos reales y **guarda el producto** en el portafolio.\n"
        "3. **Segui el negocio**: registra ventas, revisa el analisis por producto y "
        "proyecta la caja. Conecta tus claves en **Config** para datos reales y el asistente IA.")
    st.info("Modo DEMO (toggle del sidebar) muestra datos ilustrativos para ver el "
            "flujo sin gastar nada. Apagalo para produccion: el sistema no inventa datos.")

    st.divider()
    q = st.text_input("Buscar un termino", placeholder="ej: ROI, techo, BSR, landed...")
    if q.strip():
        hits = glosario.buscar(q)
        if hits:
            for termino, definicion, cat in hits:
                st.markdown(f"**{termino}** · _{cat}_  \n{definicion}")
        else:
            st.caption("Sin coincidencias. Proba con otra palabra.")
    else:
        for cat, items in glosario.por_categoria().items():
            with st.expander(f"{cat}  ({len(items)} terminos)"):
                for termino, definicion in items:
                    st.markdown(f"**{termino}** — {definicion}")

    st.divider()
    st.markdown(ui.seccion("Verdades que el sistema respeta"), unsafe_allow_html=True)
    st.markdown(
        "- **Helium 10 no tiene API en Platinum**: keywords por CSV de Cerebro; Keepa es la "
        "alternativa programatica (precio + BSR).\n"
        "- **El bot no auto-responde texto libre** (lo prohibe Amazon): solo FAQs de la "
        "whitelist; el resto queda para tu aprobacion.\n"
        "- **La proyeccion de caja tiene techo de demanda**: sin el, el sueldo 'explota' y "
        "miente. Con techo, se estabiliza en meseta (~techo x neto).\n"
        "- **El score mide ganabilidad, no margen.** Nada reemplaza la orden de prueba "
        "(USD 1.000-2.000) antes de escalar.")
