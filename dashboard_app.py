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
import urllib.parse
import webbrowser

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
from agents import publicador
from agents import exito
from agents import ganancias
from agents import dedicacion
from agents import creativos
from data import keepa
from data import mercado
from data import motor_propio

db.init()

st.set_page_config(page_title="MV Amazon FBA IA", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(ui.CSS, unsafe_allow_html=True)


def _cols_html(items):
    """Renderiza una fila de tarjetas HTML en columnas iguales."""
    cols = st.columns(len(items))
    for c, html in zip(cols, items):
        c.markdown(html, unsafe_allow_html=True)


# Los graficos nativos de Streamlit usan altair; en Python 3.14 con versiones
# viejas de altair/typing_extensions eso puede reventar al renderizar. Estos
# wrappers intentan el grafico y, si falla, muestran la tabla en vez de romper
# TODO el programa. Asi la app nunca se cae por un problema de dependencias.
def _line_chart(data, **kw):
    try:
        st.line_chart(data, **kw)
    except Exception:
        st.dataframe(data, use_container_width=True)
        st.caption("Grafico no disponible en este equipo (dependencia de charts); "
                   "muestro la tabla. Se corrige con: pip install -U typing_extensions altair")


def _bar_chart(data, **kw):
    try:
        st.bar_chart(data, **kw)
    except Exception:
        st.dataframe(data, use_container_width=True)
        st.caption("Grafico no disponible en este equipo (dependencia de charts); "
                   "muestro la tabla. Se corrige con: pip install -U typing_extensions altair")


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

tabs = st.tabs(["  Investigacion  ", "  Mercado  ", "  Pricing  ", "  Portafolio  ",
                "  Publicar  ", "  Caja  ", "  Ventas  ", "  Inversores  ", "  Plan  ",
                "  Alertas  ", "  Config  ", "  Asistente IA  ", "  Ayuda  "])

# ==================== PRODUCTO ACTIVO (compartido entre pestañas) ==================== #
# Elegís un producto del portafolio UNA vez y sus datos (costo, flete, precio, neto,
# ASIN, techo...) se replican como valores por defecto en Pricing, Caja y Ventas, en
# vez de cargarlos a mano en cada pestaña. Soporta multiples productos: cambiás el
# seleccionado y todo se actualiza.
try:
    _cartera = productos.listar()
except Exception:
    _cartera = []
_opc_activo = {"— Manual (sin producto) —": None}
for _p in _cartera:
    _opc_activo[f"{_p['nombre']} · {(_p.get('asin') or 's/ASIN')}"] = _p
st.sidebar.markdown("### 🎯 Producto activo")
_sel_activo = st.sidebar.selectbox(
    "Sus datos se replican en Pricing, Caja y Ventas",
    list(_opc_activo.keys()), key="sb_prod_activo")
ACTIVO = _opc_activo.get(_sel_activo) or {}
if ACTIVO:
    st.sidebar.caption(
        f"Costo {ui.usd(ACTIVO.get('costo'))} · Precio {ui.usd(ACTIVO.get('precio'))} · "
        f"Neto/u {ui.usd(ACTIVO.get('neto'))} · Techo {ACTIVO.get('techo_demanda') or '—'} u/mes")
    st.sidebar.caption("Los campos de las pestañas vienen precargados; podés ajustarlos igual.")
else:
    st.sidebar.caption("Cargá productos en **Portafolio** para elegirlos acá y no "
                       "reescribir sus datos en cada pestaña.")


def A(campo, defecto):
    """Valor del producto activo para 'campo', o el 'defecto' si no hay activo/valor."""
    v = ACTIVO.get(campo)
    return v if v not in (None, "") else defecto

# ============================ 1) INVESTIGACION ============================ #
with tabs[0]:
    st.markdown(ui.seccion("Investigacion de nicho",
                           "Motor propio gratis o CSV de Cerebro -> score -> listing"),
                unsafe_allow_html=True)
    fuente_kw = st.radio("Fuente de keywords",
                         ["Motor propio (gratis, autocompletado Amazon)",
                          "CSV de Helium 10 Cerebro"],
                         horizontal=True, key="inv_fuente",
                         help="El motor propio descubre keywords y nichos reales sin "
                              "pagar APIs; el CSV de Cerebro suma volumenes de busqueda.")
    usa_motor = fuente_kw.startswith("Motor propio")
    # Idioma/marketplace: el buscador trae las keywords localizadas por API (no a
    # mano). Con clave de Claude, ademas traduce el seed al idioma del pais.
    _mkts = motor_propio.MARKETPLACES
    _mk_labels = {f"{cod} — {d['nombre']}": cod for cod, d in _mkts.items()}
    ci1, ci2 = st.columns([2, 1])
    _mk_sel = ci1.selectbox("Idioma / Marketplace (keywords localizadas por API)",
                            list(_mk_labels.keys()),
                            index=list(_mk_labels.values()).index(
                                st.session_state.get("inv_mkt", "US")),
                            key="inv_mkt_label")
    mkt_cod = _mk_labels[_mk_sel]
    st.session_state["inv_mkt"] = mkt_cod
    traducir_seed = ci2.checkbox("Traducir el seed al idioma del país", value=False,
                                 key="inv_trad",
                                 help="Con clave de Claude traduce tu keyword al idioma "
                                      "del marketplace antes de buscar.")
    c1, c2 = st.columns([3, 1])
    keyword = c1.text_input("Nicho / keyword principal", value="bamboo kitchen utensils")
    correr = c2.button("Investigar", type="primary", use_container_width=True)
    csv_path = None
    if not usa_motor:
        up = st.file_uploader("Subi un export CSV de Helium 10 Cerebro", type=["csv"])
        if up is not None:
            os.makedirs(config.CEREBRO_CSV_DIR, exist_ok=True)
            csv_path = os.path.join(config.CEREBRO_CSV_DIR, up.name)
            with open(csv_path, "wb") as f:
                f.write(up.getbuffer())
            st.success(f"CSV recibido: {up.name}")
    else:
        up = None

    if usa_motor and correr:
        seed_busqueda = keyword
        if traducir_seed and not demo:
            from agents import traductor
            tr = traductor.traducir(keyword, _mkts[mkt_cod]["idioma"])
            seed_busqueda = tr["texto"]
            (st.success if tr["fuente"].startswith("Claude") else st.info)(tr["mensaje"])
        with st.spinner(f"Consultando el autocompletado de Amazon {mkt_cod} (gratis)..."):
            res_m = motor_propio.investigar(seed_busqueda, demo=demo, marketplace=mkt_cod)
        if not res_m["ok"]:
            st.info(res_m["mensaje"])
        else:
            top_kw = res_m["keywords"]
            _cols_html([
                ui.kpi("Keywords reales", ui.fmt_int(len(top_kw)),
                       f"{res_m['requests']} consultas gratis", hero=True),
                ui.kpi("Nichos candidatos", ui.fmt_int(len(res_m["nichos"])),
                       "por modificador long-tail"),
                ui.kpi("Interes maximo", f"{top_kw[0]['interes']}/100" if top_kw else "0",
                       "proxy de autocompletado"),
                ui.kpi("Costo", "$0", "sin APIs pagas", tone="good"),
            ])
            st.warning(res_m["nota_honesta"])
            cA, cB = st.columns(2)
            cA.markdown(ui.seccion("Top keywords (interes real de Amazon)"),
                        unsafe_allow_html=True)
            dfk = pd.DataFrame(top_kw[:20])[["keyword", "interes", "mejor_rank",
                                             "apariciones"]]
            dfk.columns = ["Keyword", "Interes /100", "Mejor rank", "Apariciones"]
            cA.dataframe(dfk, use_container_width=True, hide_index=True)
            cB.markdown(ui.seccion("Nichos candidatos"), unsafe_allow_html=True)
            dfn = pd.DataFrame([{"Nicho": n["nicho"], "Keywords": len(n["keywords"]),
                                 "Interes max": n["interes_max"]}
                                for n in res_m["nichos"][:12]])
            cB.dataframe(dfn, use_container_width=True, hide_index=True)
            st.divider()
            st.markdown(ui.seccion("Listing sugerido con estas keywords",
                                   "Copy en ingles (mercado US)"), unsafe_allow_html=True)
            li = generar_listing(keyword, config.MARKETPLACE,
                                 keywords=motor_propio.keywords_cerebro(res_m))
            st.text_input("Titulo", value=li["titulo"], key="mo_li_tit")
            for i, b in enumerate(li["bullets"], 1):
                st.markdown(f"**{i}.** {b}")
            st.text_area("Descripcion", value=li["descripcion"], height=120,
                         key="mo_li_desc")
            st.caption(f"Motor: {li['_motor']} · Para score de nicho con demanda "
                       "numerica, usa CSV de Cerebro o conecta Keepa.")
    elif usa_motor:
        st.caption("Escribi un seed (ej: 'bamboo kitchen') y toca Investigar. "
                   "El motor consulta el autocompletado publico de Amazon: keywords "
                   "y nichos reales, gratis.")

    if (not usa_motor) and (correr or up is not None):
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
    elif not usa_motor:
        st.caption("Escribi un nicho y toca Investigar (o subi un CSV de Cerebro).")

# ============================ 2) MERCADO ============================ #
with tabs[1]:
    st.markdown(ui.seccion("Explorador de mercado",
                           "Productos estrella por rango de precios, competidores, "
                           "reseñas, proveedores y probabilidad de exito"),
                unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns([3, 1, 1, 1])
    mk_kw = m1.text_input("Producto / keyword", value="bamboo kitchen utensils",
                          key="mk_kw")
    mk_min = m2.number_input("Precio min (USD)", value=10.0, min_value=0.0,
                             step=1.0, key="mk_min")
    mk_max = m3.number_input("Precio max (USD)", value=50.0, min_value=1.0,
                             step=1.0, key="mk_max")
    mk_go = m4.button("Explorar", type="primary", use_container_width=True,
                      key="mk_go")
    if mk_go:
        with st.spinner("Buscando productos estrella..."):
            st.session_state["mk_res"] = mercado.productos_estrella(
                mk_kw, mk_min, mk_max, demo=demo)
            st.session_state["mk_kw_hecho"] = mk_kw
    res_mk = st.session_state.get("mk_res")
    if res_mk:
        comp = mercado.resumen_competencia(res_mk["productos"])
        if not res_mk["ok"]:
            st.warning(res_mk["mensaje"])
            st.markdown(ui.seccion("Mira los competidores a mano (links directos)"),
                        unsafe_allow_html=True)
            for l in res_mk["links_amazon"]:
                st.markdown(f"- [{l['nombre']}]({l['url']})")
        else:
            st.caption(f"Fuente: {res_mk['fuente']} · {res_mk['mensaje']}" +
                       (f" · costo ~{res_mk['costo_tokens']} tokens Keepa"
                        if res_mk["costo_tokens"] else ""))
            if comp.get("ok"):
                _cols_html([
                    ui.kpi("Competidores", ui.fmt_int(comp["n_competidores"]),
                           f"precios USD {comp['precio_min']:.0f}-{comp['precio_max']:.0f}"),
                    ui.kpi("Ventas estimadas", ui.fmt_int(comp["ventas_estim_total"]) + "/mes",
                           "suma de lideres (curva BSR)", hero=True),
                    ui.kpi("Calidad promedio", f"{comp['rating_promedio']}/5"
                           if comp["rating_promedio"] else "s/d",
                           "rating de la competencia",
                           tone=("warn" if (comp["rating_promedio"] or 5) < 4.3 else "navy")),
                    ui.kpi("Reseñas (mediana)", ui.fmt_int(comp["resenas_mediana"]),
                           "barrera de entrada",
                           tone=("bad" if comp["resenas_mediana"] > 1000 else
                                 "good" if comp["resenas_mediana"] < 300 else "warn")),
                ])
            dfe = pd.DataFrame([{
                "Producto": p["titulo"][:60], "ASIN": p["asin"],
                "Precio": p["precio"], "BSR": p["bsr"],
                "Ventas/mes (est.)": p["ventas_estim"], "Rating": p["rating"],
                "Reseñas": p["resenas"], "Link": p["link"],
                "Reseñas (link)": p["link_resenas"],
            } for p in res_mk["productos"]])
            st.dataframe(dfe, use_container_width=True, hide_index=True,
                         column_config={
                             "Link": st.column_config.LinkColumn("Producto ->"),
                             "Reseñas (link)": st.column_config.LinkColumn("Reseñas ->"),
                         })
            st.caption("Calidad de producto: abri las reseñas de 1-3 estrellas del "
                       "lider (link) y pegalas en el Asistente IA: te resume que "
                       "arreglar para diferenciarte. El sistema no scrapea reseñas "
                       "(lo prohiben los terminos de Amazon).")

        st.divider()
        st.markdown(ui.seccion("Proveedores mejor rankeados",
                               "Links directos filtrados para contactar en serio"),
                    unsafe_allow_html=True)
        for pv in mercado.links_proveedores(st.session_state.get("mk_kw_hecho", mk_kw)):
            st.markdown(f"**{pv['prioridad']}. [{pv['plataforma']}]({pv['url']})** — "
                        f"{pv['nota']}")
        st.caption("Checklist de verificacion + RFQ profesional en ingles: pestana "
                   "Publicar, seccion Proveedor.")

        st.divider()
        st.markdown(ui.seccion("Asesor de probabilidad de exito",
                               "Formula auditable + analisis razonado (Claude si hay clave)"),
                    unsafe_allow_html=True)
        e1, e2, e3 = st.columns(3)
        ex_precio = e1.number_input("Tu precio objetivo (USD)", value=24.0,
                                    min_value=0.0, step=0.5, key="ex_precio")
        ex_margen = e2.number_input("Margen calculado % (0 = sin pricing)", value=0.0,
                                    min_value=0.0, step=0.5, key="ex_margen")
        ex_go = e3.button("Evaluar exito", type="primary", use_container_width=True,
                          key="ex_go")
        if ex_go:
            ev = exito.evaluar(st.session_state.get("mk_kw_hecho", mk_kw),
                               competencia=(comp if comp.get("ok") else None),
                               precio_objetivo=ex_precio,
                               margen_pct=(ex_margen if ex_margen > 0 else None))
            tono_ev = {"VERDE": "verde", "AMARILLO": "amarillo", "ROJO": "rojo"}[ev["veredicto"]]
            _cols_html([
                ui.kpi("Probabilidad de exito", f"{ev['probabilidad']}/100",
                       ev["veredicto"], hero=True),
            ] + [ui.kpi(k.replace("_", " ").title(), f"{v['valor']:.2f}",
                        f"peso {exito.PESOS[k]:.0%}",
                        tone=("good" if v["valor"] >= 0.6 else
                              "bad" if v["valor"] < 0.35 else "warn"))
                 for k, v in list(ev["factores"].items())[:3]])
            st.markdown(ui.badge(f"{ev['veredicto']}: {ev['comentario']}", tono_ev),
                        unsafe_allow_html=True)
            for k, v in ev["factores"].items():
                st.markdown(f"- **{k}** (peso {exito.PESOS[k]:.0%}, valor "
                            f"{v['valor']:.2f}): {v['detalle']}")
            if ev["datos_faltantes"]:
                st.info("Datos que mejorarian la estimacion: " +
                        ", ".join(ev["datos_faltantes"]))
            st.markdown(ui.seccion("Recomendaciones"), unsafe_allow_html=True)
            for rc in ev["recomendaciones"]:
                st.markdown(f"- {rc}")
            with st.spinner("Analisis razonado..."):
                nar = exito.narrativa(ev, comp if comp.get("ok") else None)
            if nar["modo"] == "online":
                st.markdown(ui.seccion("Analisis del asesor (Claude)"),
                            unsafe_allow_html=True)
                st.markdown(nar["texto"])
            st.warning(ev["caveat"])

        st.divider()
        st.markdown(ui.seccion("¿Cuanto podrias ganar?",
                               "Invertis X plata (o compras X unidades): desglose "
                               "de costos y ganancia neta para vos"),
                    unsafe_allow_html=True)
        g1, g2, g3 = st.columns(3)
        modo_g = g1.radio("Simular por", ["Inversion (USD)", "Cantidad (unidades)"],
                          horizontal=True, key="ga_modo")
        ga_inv = g2.number_input("Inversion (USD)", value=3000.0, min_value=0.0,
                                 step=250.0, key="ga_inv",
                                 disabled=not modo_g.startswith("Inversion"))
        ga_uni = g3.number_input("Unidades a comprar", value=500, min_value=0,
                                 step=50, key="ga_uni",
                                 disabled=modo_g.startswith("Inversion"))
        g4, g5, g6, g7 = st.columns(4)
        ga_costo = g4.number_input("Costo unitario (USD)", value=2.10, min_value=0.0,
                                   step=0.10, key="ga_costo")
        ga_flete = g5.number_input("Flete unitario (USD)", value=0.80, min_value=0.0,
                                   step=0.10, key="ga_flete")
        ga_aran = g6.number_input("Arancel (%)", value=6.0, min_value=0.0,
                                  step=0.5, key="ga_aran")
        ga_prep = g7.number_input("Prep (USD)", value=0.50, min_value=0.0,
                                  step=0.10, key="ga_prep")
        g8, g9, g10 = st.columns(3)
        ga_fba = g8.number_input("FBA fee (USD)", value=config.FBA_FEE_DEFAULT,
                                 min_value=0.0, step=0.10, key="ga_fba")
        ga_precio = g9.number_input("Precio de venta (USD, 0 = sugerido)",
                                    value=float(st.session_state.get("ex_precio", 24.0)),
                                    min_value=0.0, step=0.50, key="ga_precio")
        ga_techo = g10.number_input("Techo demanda (u/mes)", value=290, min_value=1,
                                    step=10, key="ga_techo")
        if st.button("Calcular ganancia potencial", type="primary", key="ga_btn"):
            sim = ganancias.simular(
                inversion=(ga_inv if modo_g.startswith("Inversion") else None),
                unidades=(int(ga_uni) if not modo_g.startswith("Inversion") else None),
                costo=ga_costo, flete=ga_flete, arancel_pct=ga_aran, prep=ga_prep,
                fba_fee=ga_fba, precio=(ga_precio if ga_precio > 0 else None),
                techo_demanda=int(ga_techo))
            if not sim["ok"]:
                st.error(sim["mensaje"])
            else:
                st.session_state["ga_sim"] = sim
        sim = st.session_state.get("ga_sim")
        if sim and sim.get("ok"):
            ue_g, lo_g, re_g = sim["unit_economics"], sim["lote"], sim["reciclado"]
            gan_tone = "good" if lo_g["ganancia_neta"] > 0 else "bad"
            _cols_html([
                ui.kpi("Ganancia neta del lote", ui.fmt_money(lo_g["ganancia_neta"]),
                       f"{sim['entrada']} -> {ui.fmt_int(lo_g['unidades_compradas'])} u",
                       hero=(lo_g["ganancia_neta"] > 0), tone=gan_tone),
                ui.kpi("ROI de tu inversion", ui.fmt_pct(lo_g["roi_inversion_pct"]),
                       f"sobre USD {lo_g['inversion_usada']:,.0f}", tone=gan_tone),
                ui.kpi("Ganancia por unidad", ui.fmt_money(lo_g["ganancia_por_unidad"]),
                       f"precio USD {ue_g['precio_venta']:.2f}"
                       + (" (sugerido)" if ue_g["precio_es_sugerido"] else ""),
                       tone={"verde": "good", "amarillo": "warn",
                             "rojo": "bad"}[ue_g["semaforo"]]),
                ui.kpi("Tiempo de venta", f"~{lo_g['meses_para_venderlo']} meses",
                       f"USD {lo_g['ganancia_por_mes_promedio']:,.0f}/mes al techo"
                       if lo_g["ganancia_por_mes_promedio"] else ""),
            ])
            cg1, cg2 = st.columns(2)
            cg1.markdown(ui.seccion("Desglose: a donde va cada dolar"),
                         unsafe_allow_html=True)
            etiquetas = {"producto": "Producto (fabrica)", "flete": "Flete",
                         "arancel": "Arancel", "prep": "Prep",
                         "comision_amazon_referral": "Comision Amazon (referral)",
                         "fba_fee": "FBA fee (logistica)",
                         "publicidad_acos": "Publicidad (ACoS)"}
            df_c = pd.DataFrame(
                [{"Concepto": "Ingreso bruto (post devoluciones)",
                  "USD": lo_g["ingreso_bruto"]}] +
                [{"Concepto": f"- {etiquetas[k]}", "USD": -v}
                 for k, v in lo_g["costos"].items()] +
                [{"Concepto": "= GANANCIA NETA PARA VOS", "USD": lo_g["ganancia_neta"]}])
            cg1.dataframe(df_c, use_container_width=True, hide_index=True,
                          column_config={"USD": st.column_config.NumberColumn(
                              format="$%.2f")})
            cg2.markdown(ui.seccion("Escenario sostenido: reciclando capital 12 meses",
                                    "El landed repone stock, el neto se retira"),
                         unsafe_allow_html=True)
            cg2.markdown(
                ui.kpi("Sueldo en meseta", ui.fmt_money(re_g["sueldo_meseta_mensual"]),
                       "por mes, sostenido", hero=True) +
                ui.kpi("Ganancia acumulada 12m", ui.fmt_money(re_g["ganancia_12m_estimada"]),
                       f"primer cobro mes {re_g['mes_primer_cobro']}",
                       tone="good" if re_g["ganancia_12m_estimada"] > 0 else "bad"),
                unsafe_allow_html=True)
            df_g = pd.DataFrame(re_g["filas"])
            cg2.line_chart(df_g.set_index("mes")[["sueldo", "caja"]], height=200,
                           color=["#8bc34a", "#1e3a8a"])
            st.warning(sim["caveat"])
    else:
        st.caption("Escribi un producto y un rango de precios, y toca Explorar: "
                   "productos estrella con ventas/reseñas/calidad (Keepa o demo), "
                   "proveedores verificados con link directo, probabilidad de exito "
                   "y cuanto podrias ganar con tu inversion.")

# ============================ 3) PRICING ============================ #
with tabs[2]:
    st.markdown(ui.seccion("Pricing", "Costo desembarcado -> precio -> margen -> ROI"),
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    costo = c1.number_input("Costo unitario (USD)", value=float(A("costo", 2.10)), min_value=0.0, step=0.10)
    flete = c2.number_input("Flete unitario (USD)", value=float(A("flete", 0.80)), min_value=0.0, step=0.10)
    arancel = c3.number_input("Arancel (%)", value=float(A("arancel_pct", 6.0)), min_value=0.0, step=0.5)
    c4, c5, c6 = st.columns(3)
    prep = c4.number_input("Prep (USD)", value=float(A("prep", 0.50)), min_value=0.0, step=0.10)
    fba = c5.number_input("FBA fee (USD)", value=float(A("fba_fee", config.FBA_FEE_DEFAULT)), min_value=0.0, step=0.10)
    comp = c6.number_input("Precio competencia (USD, 0=sin)", value=float(A("precio_competencia", 19.99) or 0.0), min_value=0.0, step=0.50)
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

# ============================ 4) PORTAFOLIO ============================ #
with tabs[3]:
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
                _line_chart(dfa.set_index("mes")[["caja", "sueldo"]], height=220,
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

# ============================ 5) PUBLICAR ============================ #
with tabs[4]:
    st.markdown(ui.seccion("Publicar en Amazon — paquete completo",
                           "Listing + fotos + precio + cantidades + proveedor + "
                           "checklist Seller Central, en un solo documento"),
                unsafe_allow_html=True)
    prods_pub = productos.listar(solo_activos=True)
    opciones_pub = {"(cargar a mano)": None}
    opciones_pub.update({f"#{p['id']} — {p['nombre']}": p for p in prods_pub})
    sel_pub = st.selectbox("Producto del portafolio (o carga manual)",
                           list(opciones_pub.keys()), key="pub_sel")
    base = opciones_pub[sel_pub]
    b1, b2, b3, b4 = st.columns(4)
    p_nombre = b1.text_input("Nombre *", value=(base or {}).get("nombre", ""),
                             key="pub_nombre")
    p_costo = b2.number_input("Costo (USD)", value=float((base or {}).get("costo") or 2.10),
                              min_value=0.0, step=0.10, key="pub_costo")
    p_flete = b3.number_input("Flete (USD)", value=float((base or {}).get("flete") or 0.80),
                              min_value=0.0, step=0.10, key="pub_flete")
    p_aran = b4.number_input("Arancel (%)", value=float((base or {}).get("arancel_pct") or 6.0),
                             min_value=0.0, step=0.5, key="pub_aran")
    b5, b6, b7, b8 = st.columns(4)
    p_prep = b5.number_input("Prep (USD)", value=float((base or {}).get("prep") or 0.50),
                             min_value=0.0, step=0.10, key="pub_prep")
    p_fba = b6.number_input("FBA fee (USD)",
                            value=float((base or {}).get("fba_fee") or config.FBA_FEE_DEFAULT),
                            min_value=0.0, step=0.10, key="pub_fba")
    p_comp = b7.number_input("Precio competencia (0=sin)", value=19.99, min_value=0.0,
                             step=0.50, key="pub_comp")
    p_techo = b8.number_input("Techo demanda (u/mes)",
                              value=int((base or {}).get("techo_demanda") or 290),
                              min_value=0, step=10, key="pub_techo")
    fuente_pub = st.radio("Keywords para el listing",
                          ["Motor propio (gratis)", "CSV Cerebro / DEMO"],
                          horizontal=True, key="pub_fuente")
    if st.button("Armar paquete de publicacion", type="primary", key="pub_btn"):
        kws_pub = None
        if fuente_pub.startswith("Motor propio") and p_nombre.strip():
            with st.spinner("Investigando keywords con el motor propio..."):
                res_pub = motor_propio.investigar(p_nombre, demo=demo)
            if res_pub["ok"]:
                kws_pub = motor_propio.keywords_cerebro(res_pub)
        with st.spinner("Armando el paquete..."):
            paq = publicador.paquete(
                p_nombre, costo=p_costo, flete=p_flete, arancel_pct=p_aran,
                prep=p_prep, fba_fee=p_fba,
                precio_competencia=(p_comp if p_comp > 0 else None),
                techo_demanda=int(p_techo), keywords=kws_pub, demo=demo)
        if not paq["ok"]:
            st.error(paq["mensaje"])
        else:
            st.session_state["paq_pub"] = paq
    paq = st.session_state.get("paq_pub")
    if paq and paq.get("ok"):
        mq, qq = paq["pricing"], paq["cantidades"]
        _cols_html([
            ui.kpi("Precio sugerido", ui.fmt_money(mq["precio"]), mq["estrategia"],
                   hero=True),
            ui.kpi("Margen", ui.fmt_pct(mq["margen_pct"]), "neto / precio",
                   tone={"verde": "good", "amarillo": "warn", "rojo": "bad"}[mq["semaforo"]]),
            ui.kpi("Orden de prueba", f"{qq['orden_prueba']} u",
                   f"USD {qq['orden_prueba_usd']:,.0f} — validar primero"),
            ui.kpi("1ra compra al techo", f"{qq['primera_compra_techo']} u",
                   f"USD {qq['primera_compra_usd']:,.0f} — tras validar"),
        ])
        t_list, t_fotos, t_img, t_prov, t_pasos = st.tabs(
            ["Listing", "Fotos (7 tomas)", "Imagenes (banner + infografia)",
             "Proveedor + RFQ", "Publicar paso a paso"])
        with t_list:
            st.text_input("Titulo", value=paq["listing"]["titulo"], key="pub_li_tit")
            for i, b in enumerate(paq["listing"]["bullets"], 1):
                st.markdown(f"**{i}.** {b}")
            st.text_area("Descripcion", value=paq["listing"]["descripcion"],
                         height=110, key="pub_li_desc")
            st.text_area("Backend keywords (Search Terms)",
                         value=paq["listing"]["backend_keywords"], height=70,
                         key="pub_li_bk")
            st.caption(f"Motor: {paq['listing']['motor']} · Keywords: "
                       f"{paq['listing']['fuente_keywords']}")
        with t_fotos:
            for f in paq["fotos"]:
                st.markdown(f"**{f['toma']}** — {f['guion']}")
            st.caption("Banner/A+: " + paq["listing"]["banner_brief"])
        with t_img:
            st.caption("Generadas localmente (sin costo ni API paga) con la paleta "
                       "de marca. Usalas como imagen secundaria/A+ o de referencia "
                       "de estilo — NO reemplazan la foto principal real que exige Amazon.")
            kit = creativos.kit_creativo(paq["listing"]["titulo"], paq["listing"]["bullets"])
            ci1, ci2 = st.columns(2)
            ci1.image(kit["banner_png"], caption="Banner hero (A+ / redes)",
                      use_container_width=True)
            ci1.download_button("Descargar banner (PNG)", data=kit["banner_png"],
                                file_name="banner_hero.png", mime="image/png",
                                key="dl_banner")
            ci2.image(kit["infografia_png"], caption="Infografia de beneficios",
                      use_container_width=True)
            ci2.download_button("Descargar infografia (PNG)", data=kit["infografia_png"],
                                file_name="infografia_beneficios.png", mime="image/png",
                                key="dl_info")
            st.caption(kit["nota"])
        with t_prov:
            for c in paq["proveedor"]["checklist"]:
                st.markdown(f"- {c}")
            st.text_area("RFQ listo para Alibaba (ingles)",
                         value=paq["proveedor"]["rfq"], height=260, key="pub_rfq")
        with t_pasos:
            for i, c in enumerate(paq["checklist_seller_central"], 1):
                st.markdown(f"**{i}.** {c}")
        st.warning(paq["nota_honesta"])
        st.download_button(
            "Descargar paquete completo (HTML imprimible)",
            data=publicador.html_paquete(paq),
            file_name=f"paquete_publicacion_{paq['producto'][:30].replace(' ', '_')}.html",
            mime="text/html", key="pub_dl")
    else:
        st.caption("Elegi un producto del portafolio (o carga los datos) y toca "
                   "'Armar paquete': sale todo listo para publicar, con fotos, "
                   "precio, cantidades y proveedor.")

# ============================ 6) CAJA ============================ #
with tabs[5]:
    st.markdown(ui.seccion("Proyeccion realista de caja",
                           "Con lead time, DD+7, devoluciones y techo de demanda"),
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    budget = c1.number_input("Capital (USD)", value=8000, min_value=0, step=500)
    landed_in = c2.number_input("Landed/unidad (USD)", value=float(A("landed", 5.50)), min_value=0.0, step=0.10)
    precio_in = c3.number_input("Precio venta (USD)", value=float(A("precio", 24.0)), min_value=0.0, step=0.50)
    c4, c5, c6 = st.columns(3)
    net_in = c4.number_input("Neto/unidad (USD)", value=float(A("neto", 6.90)), min_value=0.0, step=0.10)
    techo = c5.number_input("Techo demanda (unid/mes)", value=int(A("techo_demanda", 290)), min_value=0, step=10)
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
    _line_chart(df.set_index("mes")[["caja", "sueldo"]], height=240,
                  color=["#1e3a8a", "#8bc34a"])
    st.dataframe(df[["mes", "vendidas", "cobrado", "sueldo", "caja", "capital_atado"]],
                 use_container_width=True, hide_index=True)

# ============================ 7) VENTAS ============================ #
with tabs[6]:
    st.markdown(ui.seccion("Ventas y KPIs", "Registra una venta y segui el mix"),
                unsafe_allow_html=True)
    if ACTIVO:
        st.caption(f"Producto activo: **{ACTIVO.get('nombre')}** — precio y neto/unidad "
                   "vienen precargados. Cambialo en la barra lateral.")
    with st.form("venta"):
        c1, c2, c3 = st.columns(3)
        asin = c1.text_input("ASIN", value=str(A("asin", "B0DEMO123")))
        unid = c2.number_input("Unidades", value=5, min_value=0, step=1)
        pventa = c3.number_input("Precio (USD)", value=float(A("precio", 24.0)), min_value=0.0, step=0.5)
        c4, c5, c6 = st.columns(3)
        netou = c4.number_input("Neto/unidad (USD)", value=float(A("neto", 6.9)), min_value=0.0, step=0.1)
        pais = c5.text_input("Pais", value="US")
        seg = c6.text_input("Segmento", value="hogar")
        ok = st.form_submit_button("Registrar venta", type="primary")
    if ok:
        rv = analytics.registrar_venta(asin, int(unid), pventa, netou, pais=pais,
                                       segmento=seg, product_id=ACTIVO.get("id"),
                                       alertar=True)
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
        _bar_chart(pd.DataFrame(k["por_producto"]).set_index("k")["ingreso"], height=220,
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

# ============================ 8) INVERSORES ============================ #
with tabs[7]:
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

# ============================ 9) PLAN ============================ #
with tabs[8]:
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
    st.markdown(ui.seccion("¿Cuantas horas por semana necesito REALMENTE?",
                           "Desglosado por tarea; distingue lo que el sistema ya automatiza"),
                unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    ded_prod = d1.number_input("Productos ya en meseta (operacion)", value=1,
                               min_value=0, step=1, key="ded_prod")
    ded_lanz = d2.toggle("Estoy lanzando/validando un producto nuevo ahora", value=True,
                        key="ded_lanz")
    ded = dedicacion.estimar(n_productos_operacion=ded_prod, lanzando_producto=ded_lanz)
    _cols_html([
        ui.kpi("Horas por semana", f"{ded['horas_semana_min']:.0f}-{ded['horas_semana_max']:.0f}",
               "lanzamiento + operacion" if ded_lanz else "solo operacion", hero=True),
    ])
    df_ded = pd.DataFrame(ded["desglose"])
    df_ded.columns = ["Tarea", "Hs min", "Hs max", "Frecuencia", "Fase"]
    st.dataframe(df_ded, use_container_width=True, hide_index=True)
    with st.expander("Lo que el sistema ya hace por vos (automatizado)"):
        for a in ded["automatizado_por_el_sistema"]:
            st.markdown(f"- {a}")
    st.caption(ded["caveat"])

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
        _line_chart(dfc.set_index("mes")[["capital", "aportado"]], height=240,
                      color=["#1e3a8a", "#8bc34a"])
        df_an = dfc[dfc["mes"] % 12 == 0][["anio", "capital", "aportado", "ocioso"]]
        st.dataframe(df_an, use_container_width=True, hide_index=True)
    st.caption("Honesto: la tasa fija compuesta es matematica de folleto. En FBA el rendimiento "
               "es alto sobre el capital desplegado, pero el techo de demanda corta la "
               "capitalizacion: mas plata no rinde si el nicho no la absorbe. Usa el techo "
               "para ver tu curva real; la exponencial pura solo aplica a instrumentos "
               "financieros sin tope de colocacion.")

# ============================ 10) ALERTAS ============================ #
with tabs[9]:
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

# ============================ 11) CONFIG ============================ #
with tabs[10]:
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

# ============================ 12) ASISTENTE IA ============================ #
with tabs[11]:
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

# ============================ 13) AYUDA ============================ #
with tabs[12]:
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

    st.divider()
    st.markdown(ui.seccion("Contacto y soporte",
                           "Escribinos tu consulta — se abre tu correo con todo completado"),
                unsafe_allow_html=True)
    with st.form("form_contacto"):
        ct1, ct2 = st.columns(2)
        ct_asunto = ct1.text_input("Asunto", placeholder="Ej: Consulta sobre licencia Pro",
                                   key="ct_asunto")
        ct_contacto = ct2.text_input("Tu teléfono o email de contacto",
                                     placeholder="Ej: +598 99 123 456 o vos@email.com",
                                     key="ct_contacto")
        ct_pregunta = st.text_area("Tu pregunta", height=110,
                                   placeholder="Contanos en qué te podemos ayudar...",
                                   key="ct_pregunta")
        ct_enviar = st.form_submit_button("Enviar consulta", type="primary")
    if ct_enviar:
        if not ct_pregunta.strip():
            st.warning("Escribí tu pregunta antes de enviar.")
        else:
            asunto = ct_asunto.strip() or "Consulta desde MV Amazon FBA IA"
            cuerpo = (f"{ct_pregunta.strip()}\n\n"
                     f"Contacto de quien consulta: {ct_contacto.strip() or '(no indicado)'}")
            mailto = ("mailto:" + config.ALERT_TO + "?subject=" + urllib.parse.quote(asunto)
                      + "&body=" + urllib.parse.quote(cuerpo))
            try:
                webbrowser.open(mailto)
                st.success(f"Abriendo tu programa de correo hacia {config.ALERT_TO} con el "
                          "mensaje completado. Si no se abrió solo, copiá el texto de abajo "
                          "y mandalo a mano.")
            except Exception:
                st.info("No se pudo abrir el correo automaticamente. Copiá el texto de abajo "
                       f"y envialo a mano a {config.ALERT_TO}.")
            st.code(f"Para: {config.ALERT_TO}\nAsunto: {asunto}\n\n{cuerpo}", language=None)
    st.caption(f"También podés escribir directo a **{config.ALERT_TO}**.")
