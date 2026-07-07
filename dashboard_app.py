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
from core import licencia
from core.i18n import t as t_ui, IDIOMAS as IDIOMAS_APP, NOMBRES_IDIOMA as NOMBRES_IDIOMA_APP
from agents.market_intel import market_intel
from agents.listing import generar as generar_listing
from agents.pricing import evaluar as evaluar_precio
from agents.pricing import acos_bancable
from agents.capital_planner import proyeccion_realista
from agents import analytics
from agents import productos
from agents import asistente
from agents import glosario
from agents import tutorial
from agents import publicador
from agents import exito
from agents import ganancias
from agents import dedicacion
from agents import creativos
from data import keepa
from data import mercado
from data import motor_propio
from agents import recomendador

db.init()

st.set_page_config(page_title="MV FBA IA",
                   page_icon=os.path.join(_AQUI, "mobile", "icons", "icon-512.png"),
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(ui.CSS, unsafe_allow_html=True)

# ==================== DEMO / REGISTRO — 3 dias completos, multi-idioma ==================== #
# Sin servidor de cuentas: el registro y el reloj de 3 dias viven en la base local
# (misma logica en mobile/js/licencia.js para PWA/Android/iOS). El dominio interno
# del producto para la clave de licencia es "MV-Amazon-Fba" (nombre comercial sin
# cambios: "MV FBA IA").
_IDIOMAS_DEMO = ["Español", "English", "Português"]
_COD_IDIOMA_DEMO = {"Español": "es", "English": "en", "Português": "pt"}
_TXT_DEMO = {
    "es": {
        "titulo": "Bienvenido a MV FBA IA",
        "sub": "Registrate para arrancar tu demo completa y gratis de 3 días — sin límites de funciones.",
        "nombre": "Tu nombre", "email": "Tu email",
        "empezar": "Empezar mi demo de 3 días",
        "falta_email": "Ingresá un email válido para arrancar la demo.",
        "vencida_titulo": "Tu demo de 3 días venció",
        "vencida_sub": "Activá tu licencia para seguir usando MV FBA IA sin límites, "
                       "o escribinos para comprarla.",
        "clave": "Clave de licencia", "activar": "Activar licencia",
        "clave_invalida": "Esa clave no es válida para este email.",
        "clave_ok": "Licencia activada. ¡Gracias por tu compra!",
        "contactar": "Escribinos para comprar tu licencia",
        "badge_licencia": "Licencia activa",
        "badge_demo": "Demo: {n} día(s) restante(s)",
    },
    "en": {
        "titulo": "Welcome to MV FBA IA",
        "sub": "Register to start your full, free 3-day demo — no feature limits.",
        "nombre": "Your name", "email": "Your email",
        "empezar": "Start my 3-day demo",
        "falta_email": "Enter a valid email to start the demo.",
        "vencida_titulo": "Your 3-day demo expired",
        "vencida_sub": "Activate your license to keep using MV FBA IA with no limits, "
                       "or contact us to buy it.",
        "clave": "License key", "activar": "Activate license",
        "clave_invalida": "That key is not valid for this email.",
        "clave_ok": "License activated. Thanks for your purchase!",
        "contactar": "Contact us to buy your license",
        "badge_licencia": "Active license",
        "badge_demo": "Demo: {n} day(s) left",
    },
    "pt": {
        "titulo": "Bem-vindo ao MV FBA IA",
        "sub": "Cadastre-se para começar seu demo completo e gratuito de 3 dias — sem limites de funções.",
        "nombre": "Seu nome", "email": "Seu email",
        "empezar": "Começar meu demo de 3 dias",
        "falta_email": "Digite um email válido para começar o demo.",
        "vencida_titulo": "Seu demo de 3 dias venceu",
        "vencida_sub": "Ative sua licença para continuar usando o MV FBA IA sem limites, "
                       "ou fale conosco para comprá-la.",
        "clave": "Chave de licença", "activar": "Ativar licença",
        "clave_invalida": "Essa chave não é válida para este email.",
        "clave_ok": "Licença ativada. Obrigado pela compra!",
        "contactar": "Fale conosco para comprar sua licença",
        "badge_licencia": "Licença ativa",
        "badge_demo": "Demo: {n} dia(s) restante(s)",
    },
}

if "demo_idioma" not in st.session_state:
    st.session_state["demo_idioma"] = "es"

_estado_demo = licencia.estado()

if not _estado_demo["vigente"]:
    _sel_idioma_lbl = st.selectbox(
        "Idioma / Language", _IDIOMAS_DEMO,
        index=list(_COD_IDIOMA_DEMO.values()).index(st.session_state["demo_idioma"]),
        key="demo_idioma_sel", label_visibility="collapsed")
    st.session_state["demo_idioma"] = _COD_IDIOMA_DEMO[_sel_idioma_lbl]
    t = _TXT_DEMO[st.session_state["demo_idioma"]]

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px'>"
        f"{ui.logo(34, on_dark=False)}"
        f"<div style='font-weight:800;color:{ui.NAVY};font-size:20px'>{t['titulo']}</div></div>",
        unsafe_allow_html=True)

    if not _estado_demo["registrado"]:
        st.info(t["sub"])
        with st.form("form_registro_demo"):
            r_nombre = st.text_input(t["nombre"], key="reg_nombre")
            r_email = st.text_input(t["email"], key="reg_email")
            r_ok = st.form_submit_button(t["empezar"], type="primary")
        if r_ok:
            if "@" not in (r_email or ""):
                st.warning(t["falta_email"])
            else:
                licencia.registrar(r_nombre, r_email)
                st.rerun()
        st.stop()
    else:
        st.error(f"**{t['vencida_titulo']}**")
        st.caption(t["vencida_sub"])
        with st.form("form_activar_licencia"):
            a_email = st.text_input(t["email"], value=_estado_demo["email"], key="act_email")
            a_clave = st.text_input(t["clave"], key="act_clave")
            a_ok = st.form_submit_button(t["activar"], type="primary")
        if a_ok:
            res = licencia.activar_licencia(a_email, a_clave)
            if res["ok"]:
                st.success(t["clave_ok"])
                st.rerun()
            else:
                st.warning(t["clave_invalida"])
        _asunto_lic = urllib.parse.quote(f"Compra de licencia {licencia.DOMINIO}")
        _cuerpo_lic = urllib.parse.quote(
            f"Quiero comprar la licencia. Email de registro: {_estado_demo['email']}")
        _mailto_lic = f"mailto:{config.ALERT_TO}?subject={_asunto_lic}&body={_cuerpo_lic}"
        st.markdown(f"[{t['contactar']}]({_mailto_lic})")
        st.stop()


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
    # Selector de idioma de TODO el programa (un click cambia pestañas,
    # encabezados y botones principales — ver core/i18n.py). Arranca con el
    # idioma elegido en la pantalla de demo/registro si ya se eligio uno.
    st.session_state.setdefault("idioma", st.session_state.get("demo_idioma", "es"))
    _idioma_sel_app = st.selectbox(
        t_ui("idioma_label"), [NOMBRES_IDIOMA_APP[c] for c in IDIOMAS_APP],
        index=IDIOMAS_APP.index(st.session_state["idioma"]),
        key="idioma_app_sel", label_visibility="collapsed")
    st.session_state["idioma"] = {v: k for k, v in NOMBRES_IDIOMA_APP.items()}[_idioma_sel_app]
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px'>{ui.logo(30, on_dark=False)}"
        f"<div style='font-weight:800;color:{ui.NAVY};font-size:17px;line-height:1.1'>"
        f"{ui.BRAND_PREFIX} <span style='color:{ui.GREEN}'>{ui.BRAND_ACCENT}</span></div></div>",
        unsafe_allow_html=True)
    st.caption(ui.TAGLINE)
    _t_badge = _TXT_DEMO[st.session_state.get("demo_idioma", "es")]
    if _estado_demo["licencia"]:
        st.markdown(ui.badge(_t_badge["badge_licencia"], "verde"), unsafe_allow_html=True)
    else:
        st.markdown(ui.badge(_t_badge["badge_demo"].format(n=_estado_demo["dias_restantes"]),
                             "amarillo" if _estado_demo["dias_restantes"] <= 1 else "verde"),
                    unsafe_allow_html=True)
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

tabs = st.tabs([f"  {t_ui('tab_investigacion')}  ", f"  {t_ui('tab_recomendador')}  ",
                f"  {t_ui('tab_mercado')}  ", f"  {t_ui('tab_pricing')}  ",
                f"  {t_ui('tab_portafolio')}  ", f"  {t_ui('tab_publicar')}  ",
                f"  {t_ui('tab_caja')}  ", f"  {t_ui('tab_ventas')}  ",
                f"  {t_ui('tab_inversores')}  ", f"  {t_ui('tab_plan')}  ",
                f"  {t_ui('tab_alertas')}  ", f"  {t_ui('tab_config')}  ",
                f"  {t_ui('tab_asistente')}  ", f"  {t_ui('tab_ayuda')}  "])

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
# Demo full-experience: cargar 1 producto de ejemplo con un clic para recorrer
# TODO el sistema (Pricing, Caja, Ventas, Asistente) con numeros reales.
from core import demo_seed  # noqa: E402
st.sidebar.markdown(f"### {t_ui('sb_demo_titulo')}")
if demo_seed.hay_ejemplo():
    if st.sidebar.button(t_ui("sb_demo_quitar"), use_container_width=True):
        demo_seed.quitar_ejemplo()
        st.rerun()
    st.sidebar.caption("Ejemplo cargado: elegilo abajo en «Producto activo» y "
                       "recorré las pestañas.")
else:
    if st.sidebar.button(t_ui("sb_demo_cargar"), type="primary",
                         use_container_width=True):
        demo_seed.cargar_ejemplo()
        st.rerun()
    st.sidebar.caption("1 producto listo (costo, precio, margen, ROI y ventas) para "
                       "ver el sistema completo funcionando.")

st.sidebar.markdown(f"### {t_ui('sb_activo_titulo')}")
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
    st.markdown(ui.seccion(t_ui("inv_titulo"), t_ui("inv_sub")),
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
    correr = c2.button(t_ui("inv_btn"), type="primary", use_container_width=True)
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

# ============================ 2) RECOMENDADOR ============================ #
with tabs[1]:
    st.markdown(ui.seccion(t_ui("rec_titulo"), t_ui("rec_sub")),
        unsafe_allow_html=True)
    st.caption("A diferencia de Investigacion/Mercado (vos traes la keyword), esta "
               "pestaña recorre categorias FBA probadas con el motor propio y te "
               "trae una lista rankeada para arrancar. Después profundizá el "
               "candidato elegido en Investigacion o Mercado.")
    r1, r2, r3, r4 = st.columns([1, 1, 1, 1])
    rc_min = r1.number_input("Precio min (USD)", value=15.0, min_value=1.0,
                             step=1.0, key="rc_min")
    rc_max = r2.number_input("Precio max (USD)", value=45.0, min_value=1.0,
                             step=1.0, key="rc_max")
    _rc_mkts = motor_propio.MARKETPLACES
    _rc_mk_labels = {f"{cod} — {d['nombre']}": cod for cod, d in _rc_mkts.items()}
    rc_mk_sel = r3.selectbox("Marketplace", list(_rc_mk_labels.keys()),
                             index=list(_rc_mk_labels.values()).index(
                                 st.session_state.get("rc_mkt", "US")),
                             key="rc_mkt_label")
    rc_mkt_cod = _rc_mk_labels[rc_mk_sel]
    st.session_state["rc_mkt"] = rc_mkt_cod
    rc_go = r4.button(t_ui("rec_btn"), type="primary",
                      use_container_width=True, key="rc_go")
    if rc_go:
        with st.spinner("Escaneando categorias con el motor propio "
                        "(puede tardar 1-2 minutos)..."):
            st.session_state["rc_res"] = recomendador.escanear_oportunidades(
                precio_min=rc_min, precio_max=rc_max, marketplace=rc_mkt_cod,
                demo=demo)
    res_rc = st.session_state.get("rc_res")
    if res_rc:
        if not res_rc["ok"]:
            st.info(res_rc["mensaje"])
        else:
            top_op = res_rc["oportunidades"]
            _cols_html([
                ui.kpi("Oportunidades", ui.fmt_int(len(top_op)),
                       f"de {res_rc['n_candidatos_evaluados']} candidatos evaluados",
                       hero=True),
                ui.kpi("Mejor potencial", f"{top_op[0]['potencial']}/100"
                       if top_op else "0", top_op[0]["nicho"][:28] if top_op else "—"),
                ui.kpi("Rango de precio", f"USD {res_rc['precio_min']:.0f}-{res_rc['precio_max']:.0f}",
                       res_rc["marketplace"]),
                ui.kpi("Costo", "$0", "sin APIs pagas" if "Keepa" not in res_rc["fuente"]
                       else "+ Keepa conectado", tone="good"),
            ])
            st.caption(f"Fuente: {res_rc['fuente']} · categorias escaneadas: "
                       + ", ".join(res_rc["seeds_usadas"]))
            st.warning(res_rc["nota_honesta"])
            dfr = pd.DataFrame([{
                "Nicho": o["nicho"], "Potencial": o["potencial"],
                "Veredicto": o["veredicto"], "Interes (proxy)": o["interes_proxy"],
                "Competidores": o["n_competidores"] if o["n_competidores"] is not None else "s/d",
                "Ventas/mes (est.)": o["ventas_estim_total"] if o["ventas_estim_total"] is not None else "s/d",
                "Precio mediana": o["precio_mediana"] if o["precio_mediana"] is not None else "s/d",
                "Comentario": o["comentario"],
            } for o in top_op])
            st.dataframe(dfr, use_container_width=True, hide_index=True)
            st.caption("Copiá el nicho que te interese y pegalo en **Investigacion** "
                       "(para keywords/listing) o **Mercado** (para competidores y "
                       "probabilidad de exito) y seguí el flujo normal.")
    else:
        st.caption("Elegí un rango de precio y tocá Buscar oportunidades — no hace "
                   "falta escribir ninguna keyword.")

# ============================ 3) MERCADO ============================ #
with tabs[2]:
    st.markdown(ui.seccion(t_ui("mk_titulo"), t_ui("mk_sub")),
                unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns([3, 1, 1, 1])
    mk_kw = m1.text_input("Producto / keyword", value="bamboo kitchen utensils",
                          key="mk_kw")
    mk_min = m2.number_input("Precio min (USD)", value=10.0, min_value=0.0,
                             step=1.0, key="mk_min")
    mk_max = m3.number_input("Precio max (USD)", value=50.0, min_value=1.0,
                             step=1.0, key="mk_max")
    mk_go = m4.button(t_ui("mk_btn"), type="primary", use_container_width=True,
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
        ex_go = e3.button(t_ui("mk_ex_btn"), type="primary", use_container_width=True,
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
        if st.button(t_ui("mk_ga_btn"), type="primary", key="ga_btn"):
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

# ============================ 4) PRICING ============================ #
with tabs[3]:
    st.markdown(ui.seccion(t_ui("pr_titulo"), t_ui("pr_sub")),
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
        if st.button(t_ui("pr_btn"), type="primary", key="pr_g_btn"):
            r = productos.guardar(g_nombre, asin=g_asin, costo=costo, flete=flete,
                                  arancel_pct=arancel, prep=prep, fba_fee=fba,
                                  precio_competencia=(comp if comp > 0 else None),
                                  techo_demanda=int(g_techo))
            if r["ok"]:
                st.success(r["mensaje"] + " Velo en la pestana Portafolio.")
            else:
                st.error(r["mensaje"])

# ============================ 5) PORTAFOLIO ============================ #
with tabs[4]:
    st.markdown(ui.seccion(t_ui("pf_titulo"), t_ui("pf_sub")),
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
            alta_ok = st.form_submit_button(t_ui("pf_btn"), type="primary")
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
            if st.button(t_ui("pf_del_btn"), key="pf_del"):
                productos.desactivar(opciones[sel])
                st.rerun()

# ============================ 6) PUBLICAR ============================ #
with tabs[5]:
    st.markdown(ui.seccion(t_ui("pub_titulo"), t_ui("pub_sub")),
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
    if st.button(t_ui("pub_btn"), type="primary", key="pub_btn"):
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

# ============================ 7) CAJA ============================ #
with tabs[6]:
    st.markdown(ui.seccion(t_ui("cj_titulo"), t_ui("cj_sub")),
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

# ============================ 8) VENTAS ============================ #
with tabs[7]:
    st.markdown(ui.seccion(t_ui("vt_titulo"), t_ui("vt_sub")),
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
        ok = st.form_submit_button(t_ui("vt_btn"), type="primary")
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

# ============================ 9) INVERSORES ============================ #
with tabs[8]:
    from agents.capital_planner import escenario_inversor
    st.markdown(ui.seccion(t_ui("iv_titulo"), t_ui("iv_sub")),
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

# ============================ 10) PLAN ============================ #
with tabs[9]:
    from agents.portafolio import interes_compuesto, recomendar_portafolio

    st.markdown(ui.seccion(t_ui("pl_titulo"), t_ui("pl_sub")),
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

# ============================ 11) ALERTAS ============================ #
with tabs[10]:
    st.markdown(ui.seccion(t_ui("al_titulo"), t_ui("al_sub")),
                unsafe_allow_html=True)
    outbox = db.rows("SELECT fecha,asunto,para,enviado FROM alerts_outbox ORDER BY id DESC LIMIT 50")
    if outbox:
        df = pd.DataFrame(outbox)
        df["estado"] = df["enviado"].map({1: "ENVIADO", 0: "dry-run"})
        st.dataframe(df[["fecha", "asunto", "para", "estado"]],
                     use_container_width=True, hide_index=True)
    else:
        st.caption("Sin alertas todavia.")

# ============================ 12) CONFIG ============================ #
with tabs[11]:
    st.markdown(ui.seccion(t_ui("cfg_titulo"), t_ui("cfg_sub")), unsafe_allow_html=True)
    st.json(config.estado_config())
    st.markdown(ui.seccion(t_ui("cfg_test_btn")), unsafe_allow_html=True)
    asin_test = st.text_input("ASIN para probar Keepa (opcional, gasta 1 token)", value="")
    if st.button(t_ui("cfg_test_btn"), type="primary"):
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
               f"OPENAI_API_KEY: {config.mask(config.OPENAI_API_KEY)} · "
               f"GEMINI_API_KEY: {config.mask(config.GEMINI_API_KEY)} · "
               f"SMTP_USER: {config.mask(config.SMTP_USER)}")
    st.markdown("**Asistente con IA — elegí tu proveedor.** El asistente da consejo "
                "sobre tus números; **no** busca productos (eso es Keepa). Recomendado: "
                "**Claude** (mejor razonamiento). Pegás solo la clave del que elijas.")
    _provs = ["claude", "openai", "gemini"]
    _prov_label = {"claude": "Claude / Anthropic — recomendada",
                   "openai": "OpenAI (ChatGPT)", "gemini": "Google Gemini"}
    with st.form("form_claves"):
        in_prov = st.selectbox("Proveedor de IA", _provs,
                               index=_provs.index(config.IA_PROVIDER)
                               if config.IA_PROVIDER in _provs else 0,
                               format_func=lambda p: _prov_label[p])
        a1, a2, a3 = st.columns(3)
        in_anth = a1.text_input("ANTHROPIC_API_KEY", type="password",
                                help="console.anthropic.com -> API Keys")
        in_openai = a2.text_input("OPENAI_API_KEY", type="password",
                                  help="platform.openai.com -> API keys")
        in_gemini = a3.text_input("GEMINI_API_KEY", type="password",
                                  help="aistudio.google.com -> Get API key")
        st.markdown("**Búsqueda real de productos (por API).** Con Keepa, Mercado trae "
                    "productos reales de Amazon. Ningún modelo de IA da estos datos.")
        k1, k2 = st.columns(2)
        in_keepa = k1.text_input("KEEPA_API_KEY", type="password",
                                 help="keepa.com -> Keepa API -> Private API access key")
        k3, k4, k5 = st.columns(3)
        in_su = k3.text_input("SMTP_USER (Gmail)", key="cf_smtp_user")
        in_sp = k4.text_input("SMTP_PASS (App Password)", type="password",
                              key="cf_smtp_pass")
        in_to = k5.text_input("ALERT_TO (destino de alertas)", value=config.ALERT_TO,
                              key="cf_alert_to")
        guardar_claves = st.form_submit_button(t_ui("cfg_save_btn"), type="primary")
    if guardar_claves:
        r_env = config.guardar_env(KEEPA_API_KEY=in_keepa, ANTHROPIC_API_KEY=in_anth,
                                   OPENAI_API_KEY=in_openai, GEMINI_API_KEY=in_gemini,
                                   IA_PROVIDER=(in_prov if in_prov != config.IA_PROVIDER else ""),
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

# ============================ 13) ASISTENTE IA ============================ #
with tabs[12]:
    st.markdown(ui.seccion(t_ui("ia_titulo"), t_ui("ia_sub")),
                unsafe_allow_html=True)
    est = asistente.estado()
    _nom_prov = {"claude": "Claude", "openai": "OpenAI", "gemini": "Gemini"}
    _badge_txt = (f"{_nom_prov.get(est.get('proveedor'), 'IA')} conectado"
                  if est["ok"] else "Modo offline (glosario)")
    st.markdown(ui.badge(_badge_txt, "verde" if est["ok"] else "amarillo"),
                unsafe_allow_html=True)
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
        if st.button(t_ui("ia_clear_btn"), key="chat_clear"):
            st.session_state.chat_hist = []
            st.rerun()
    st.caption("El asistente usa tus datos reales (ventas, portafolio) como contexto y "
               "respeta los principios honestos del sistema. No es consejo financiero "
               "garantizado: el retorno FBA es variable.")

# ============================ 14) AYUDA ============================ #
with tabs[13]:
    st.markdown(ui.seccion(t_ui("ayu_titulo"), t_ui("ayu_sub")),
                unsafe_allow_html=True)

    st.markdown(ui.seccion(t_ui("ayu_tut_titulo"), t_ui("ayu_tut_sub")),
                unsafe_allow_html=True)
    st.info("Modo DEMO (toggle del sidebar) muestra datos ilustrativos para ver el "
            "flujo sin gastar nada. Apagalo para produccion: el sistema no inventa datos.")
    _idioma_ayuda = st.session_state.get("idioma", "es")
    for _sec in tutorial.secciones(_idioma_ayuda):
        _abierto = _sec["clave"] == "flujo"   # la vision general arranca abierta
        with st.expander(_sec["titulo"], expanded=_abierto):
            st.caption(_sec["para_que"])
            for _i, _paso in enumerate(_sec["pasos"], 1):
                st.markdown(f"{_i}. {_paso}")
            for _tip in _sec["tips"]:
                st.markdown(f"> **{t_ui('ayu_tip_label')}:** {_tip}")

    st.divider()
    st.markdown(ui.seccion(t_ui("ayu_ia_titulo"), t_ui("ayu_ia_sub")),
                unsafe_allow_html=True)
    _est_ayuda = asistente.estado()
    if _est_ayuda["ok"]:
        st.caption(_est_ayuda["mensaje"] + " Este chat responde SOLO sobre el uso del "
                   "programa; para tus numeros del negocio usa la pestana Asistente IA.")
    else:
        st.caption("Sin clave de IA responde desde el manual (offline). " +
                   _est_ayuda["mensaje"])
    if "ayuda_chat" not in st.session_state:
        st.session_state.ayuda_chat = []
    for _m in st.session_state.ayuda_chat:
        with st.chat_message(_m["role"]):
            st.markdown(_m["content"])
    _cols_ayuda = st.columns(3)
    _sugeridas_ayuda = [t_ui("ayu_sug_1"), t_ui("ayu_sug_2"), t_ui("ayu_sug_3")]
    _pregunta_sug = None
    for _n_sug, (_c, _txt) in enumerate(zip(_cols_ayuda, _sugeridas_ayuda), 1):
        if _c.button(_txt, use_container_width=True, key=f"ayu_sug_{_n_sug}"):
            _pregunta_sug = _txt
    _pregunta_ayuda = st.chat_input(t_ui("ayu_ia_input"),
                                    key="ayuda_chat_input") or _pregunta_sug
    if _pregunta_ayuda:
        st.session_state.ayuda_chat.append({"role": "user", "content": _pregunta_ayuda})
        with st.chat_message("user"):
            st.markdown(_pregunta_ayuda)
        with st.chat_message("assistant"):
            with st.spinner("..."):
                _r_ayuda = asistente.responder_programa(
                    _pregunta_ayuda, historial=st.session_state.ayuda_chat[:-1],
                    idioma=_idioma_ayuda)
            st.markdown(_r_ayuda["texto"])
        st.session_state.ayuda_chat.append(
            {"role": "assistant", "content": _r_ayuda["texto"]})

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
    st.markdown(ui.seccion("Publicidad en Amazon (Amazon Advertising / PPC)",
                           "Marco general para entender el terreno — el sistema no "
                           "gestiona campañas, te ayuda a leer los números"),
                unsafe_allow_html=True)
    st.markdown(
        "Se hace desde tu Seller Central, en **Advertising -> Campaign Manager**. "
        "Solo podés promocionar productos que ganen la Buy Box.\n\n"
        "**Los 3 tipos principales de campaña:**\n"
        "- **Sponsored Products** — la más importante y por donde arranca todo el "
        "mundo. Promociona un producto puntual en resultados de búsqueda y fichas "
        "de competidores. La que mejor convierte para empezar.\n"
        "- **Sponsored Brands** — banners con tu logo y varios productos. Requiere "
        "Brand Registry (marca registrada). Se deja para más adelante.\n"
        "- **Sponsored Display** — retargeting a gente que vio tu producto u otros "
        "similares. Secundaria al inicio.\n\n"
        "**Cómo se estructura una campaña de Sponsored Products:**\n"
        "- **Automática**: Amazon elige las keywords por vos según tu listing. "
        "Ideal al principio para descubrir qué términos convierten de verdad.\n"
        "- **Manual**: vos elegís las keywords y cuánto pagás por cada una. Se usa "
        "después, con los datos que sacaste de la automática.\n\n"
        "**Estrategia típica de lanzamiento:** arrancás con una automática para "
        "juntar datos -> ves qué keywords te trajeron ventas reales -> esas las "
        "pasás a una manual con más presupuesto, y las que no rinden las cortás o "
        "las ponés como negativas.\n\n"
        "**Cómo se paga:** por clic (CPC), no por venta. Definís un presupuesto "
        "diario y una puja máxima por clic — sale de tu bolsillo antes de cobrar "
        "la venta.\n\n"
        "**El número que tenés que vigilar siempre: el ACoS** (gasto en ads / "
        "facturación que generó). Es tu termómetro de si la pauta es rentable o "
        "te está comiendo el margen.")
    st.info("Este cockpit no configura ni corre campañas (eso se hace en Seller "
            "Central). Lo que sí hace: calcular cuánto ACoS podés bancar sin "
            "quedar en rojo, según el margen real de tu pricing.")
    ac1, ac2, ac3 = st.columns(3)
    ac_margen = ac1.number_input("Margen actual del producto (%)",
                                 value=float(A("margen", 30.0)), min_value=0.0,
                                 step=0.5, key="ac_margen",
                                 help="Precargado del producto activo si hay uno elegido "
                                      "en el sidebar; lo podés cambiar igual.")
    ac_min = ac2.number_input("Margen minimo que querés mantener (%)",
                              value=float(config.UMBRAL_AMARILLO), min_value=0.0,
                              step=0.5, key="ac_min",
                              help="Por defecto, el umbral 'amarillo' (no caer a rojo).")
    ac_max = acos_bancable(ac_margen, ac_min)
    ac3.markdown(ui.kpi("ACoS máximo bancable", f"{ac_max}%",
                        f"con margen {ac_margen:.1f}% y piso {ac_min:.1f}%", hero=True),
                unsafe_allow_html=True)
    _precio_act, _techo_act = A("precio", None), A("techo_demanda", None)
    if _precio_act and _techo_act:
        gasto_mes = round(ac_max / 100.0 * _precio_act * _techo_act, 2)
        st.caption(f"Con el precio (USD {_precio_act:.2f}) y el techo de demanda "
                   f"({int(_techo_act)} u/mes) del producto activo, eso equivale a un "
                   f"presupuesto de ads de hasta ~USD {gasto_mes:,.0f}/mes sin perforar "
                   "el margen minimo elegido.")
    st.caption("El calculo asume que el margen de arriba ya viene con el ACoS supuesto "
              f"del sistema ({config.ACOS_PCT:.0f}%, ver Config): cada punto de ACoS de "
              "más resta un punto de margen. Es una guía para decidir presupuesto, no "
              "una promesa de resultado — el ACoS real depende de tu nicho y tu listing.")

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
        ct_enviar = st.form_submit_button(t_ui("ayu_contacto_btn"), type="primary")
    if ct_enviar:
        if not ct_pregunta.strip():
            st.warning("Escribí tu pregunta antes de enviar.")
        else:
            asunto = ct_asunto.strip() or "Consulta desde MV FBA IA"
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
