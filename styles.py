#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
styles.py — Sistema de diseño de MV FBA IA (cockpit BI).
Paleta navy #1e3a8a + verde #8bc34a, tipografia Inter/Segoe UI, KPI cards con
sombra y acento, semaforos como estado real (verde/amarillo/rojo). Sin emojis.
La marca (nombre, tagline, logo) esta centralizada aca para todo el sistema.
"""

# --- Identidad de marca (fuente unica) ---
BRAND = "MV FBA IA"
BRAND_PREFIX = "MV FBA"                # se muestra en tinta normal
BRAND_ACCENT = "IA"                     # se resalta en verde
TAGLINE = "Cockpit inteligente para tu negocio Amazon FBA"

NAVY = "#1e3a8a"
NAVY_DEEP = "#152a63"
GREEN = "#8bc34a"
AMBER = "#d97706"
RED = "#dc2626"


def logo(size=34, on_dark=True):
    """Monograma 'MV' en SVG inline (sin dependencias). on_dark: para el header navy."""
    borde = "rgba(255,255,255,.25)" if on_dark else "rgba(30,58,138,.18)"
    tinta = "#ffffff" if on_dark else NAVY
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 44 44" fill="none" '
        f'style="flex:0 0 auto">'
        f'<rect x="1.5" y="1.5" width="41" height="41" rx="11" '
        f'fill="url(#mvg)" stroke="{borde}" stroke-width="1.5"/>'
        f'<defs><linearGradient id="mvg" x1="0" y1="0" x2="44" y2="44" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop stop-color="#2b4fb0"/><stop offset="1" stop-color="{NAVY_DEEP}"/>'
        f'</linearGradient></defs>'
        f'<path d="M9 31V14l7 10 7-10v17" stroke="{tinta}" stroke-width="2.6" '
        f'stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
        f'<path d="M27 14l5 13 5-13" stroke="{GREEN}" stroke-width="2.6" '
        f'stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
        f'</svg>')

_TONOS = {
    "navy": NAVY, "green": "#3f9142", "verde": "#3f9142",
    "amber": AMBER, "amarillo": AMBER, "red": RED, "rojo": RED,
}
_TONO_BG = {
    "verde": "rgba(63,145,66,.12)", "green": "rgba(63,145,66,.12)",
    "amarillo": "rgba(217,119,6,.12)", "amber": "rgba(217,119,6,.12)",
    "rojo": "rgba(220,38,38,.12)", "red": "rgba(220,38,38,.12)",
    "navy": "rgba(30,58,138,.10)",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Roboto+Mono:wght@500;600&display=swap');

:root{ --navy:#1e3a8a; --navy-deep:#152a63; --green:#8bc34a; --ink:#0f172a;
       --slate:#475569; --muted:#64748b; --line:#e2e8f0; --surface:#ffffff; }

html, body, [class*="css"], .stApp{
  font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
  color:var(--ink);
}
.stApp{ background:#eef2f7; }
.block-container{ padding-top:1.2rem; padding-bottom:2rem; max-width:1180px; }
#MainMenu, footer{ visibility:hidden; }
[data-testid="stToolbar"]{ display:none; }
[data-testid="stDecoration"]{ display:none; }
[data-testid="stHeader"]{ background:transparent; height:0; }

/* ---- Brand header ---- */
.brandbar{
  position:relative; overflow:hidden;
  background:
    radial-gradient(120% 140% at 100% 0%, rgba(139,195,74,.18) 0%, rgba(139,195,74,0) 42%),
    linear-gradient(135deg,var(--navy),var(--navy-deep));
  border-radius:18px; padding:22px 26px; color:#fff; margin-bottom:18px;
  box-shadow:0 22px 46px -22px rgba(30,58,138,.75);
  display:flex; justify-content:space-between; align-items:center; gap:16px;
}
.brandbar::after{ content:""; position:absolute; right:-40px; top:-60px; width:200px;
  height:200px; border-radius:50%; background:radial-gradient(circle,rgba(139,195,74,.16),transparent 70%); }
.brandbar .idwrap{ display:flex; align-items:center; gap:14px; position:relative; z-index:1; }
.brandbar .title{ font-size:23px; font-weight:800; letter-spacing:-.015em; line-height:1.1; }
.brandbar .title b{ color:var(--green); font-weight:800; }
.brandbar .sub{ font-size:13px; color:#c7d2fe; margin-top:3px; font-weight:500; }
.brandbar .chips{ position:relative; z-index:1; }
.brandbar .chips{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.chip{ background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.18);
  color:#e2e8f0; font-size:11px; font-weight:600; padding:5px 10px; border-radius:999px;
  display:inline-flex; align-items:center; gap:6px; }
.chip .dot{ width:7px; height:7px; border-radius:50%; background:var(--green); }
.chip.off .dot{ background:#94a3b8; }

/* ---- KPI cards ---- */
.kpi{ background:var(--surface); border:1px solid var(--line); border-left:4px solid var(--navy);
  border-radius:14px; padding:14px 16px; margin-bottom:6px;
  box-shadow:0 1px 2px rgba(15,23,42,.05), 0 14px 30px -20px rgba(15,23,42,.25); }
.kpi .lab{ font-size:11px; letter-spacing:.09em; text-transform:uppercase;
  color:var(--muted); font-weight:700; }
.kpi .val{ font-family:'Roboto Mono',ui-monospace,monospace; font-size:25px; font-weight:600;
  color:var(--navy); font-variant-numeric:tabular-nums; line-height:1.25; margin-top:2px; }
.kpi .sub{ font-size:12px; color:var(--slate); margin-top:1px; }
.kpi.hero{ background:linear-gradient(135deg,var(--navy),var(--navy-deep)); border:0; color:#fff; }
.kpi.hero .lab{ color:#c7d2fe; } .kpi.hero .val{ color:#fff; } .kpi.hero .sub{ color:#c7d2fe; }
.kpi.good{ border-left-color:var(--green); } .kpi.good .val{ color:#3f9142; }
.kpi.warn{ border-left-color:#d97706; } .kpi.warn .val{ color:#b45309; }
.kpi.bad{ border-left-color:#dc2626; }  .kpi.bad .val{ color:#dc2626; }

/* ---- Badge / semaforo ---- */
.badge{ display:inline-flex; align-items:center; gap:7px; padding:5px 13px; border-radius:999px;
  font-size:12.5px; font-weight:700; letter-spacing:.02em; }
.badge .dot{ width:8px; height:8px; border-radius:50%; }

/* ---- Section heading ---- */
.sec{ margin:6px 0 2px; }
.sec .h{ font-size:16px; font-weight:700; color:var(--ink); display:flex; align-items:center; gap:9px; }
.sec .h::before{ content:""; width:4px; height:16px; border-radius:3px;
  background:linear-gradient(180deg,var(--navy),var(--green)); display:inline-block; }
.sec .d{ font-size:12.5px; color:var(--muted); margin:2px 0 8px 13px; }

/* ---- Tabs ---- */
[data-baseweb="tab-list"]{ gap:2px; border-bottom:1px solid var(--line); }
[data-baseweb="tab"]{ font-weight:600; color:var(--muted); padding:9px 14px; }
[data-baseweb="tab"][aria-selected="true"]{ color:var(--navy); }
[data-baseweb="tab-highlight"]{ background:var(--navy); height:3px; }

/* ---- Buttons ---- */
.stButton>button, .stDownloadButton>button{
  background:var(--navy); color:#fff; border:0; border-radius:9px; font-weight:600;
  padding:.5rem 1rem; transition:filter .15s ease; }
.stButton>button:hover, .stDownloadButton>button:hover{ filter:brightness(1.12); color:#fff; }

/* ---- Inputs ---- */
[data-baseweb="input"], [data-baseweb="select"]{ border-radius:9px; }
[data-testid="stMetric"]{ background:#fff; border:1px solid var(--line); border-radius:12px;
  padding:10px 14px; box-shadow:0 10px 24px -18px rgba(15,23,42,.3); }

/* ---- Dataframe rounding ---- */
[data-testid="stDataFrame"]{ border-radius:10px; overflow:hidden; border:1px solid var(--line); }
hr{ margin:.8rem 0; border-color:var(--line); }
</style>
"""


def header(titulo=None, subtitulo="", chips=None):
    """Header de marca con logo monograma. Sin titulo -> usa la marca oficial."""
    if titulo is None:
        titulo = f'{BRAND_PREFIX} <b>{BRAND_ACCENT}</b>'
    subtitulo = subtitulo or TAGLINE
    chip_html = ""
    for txt, on in (chips or []):
        cls = "chip" if on else "chip off"
        chip_html += f'<span class="{cls}"><span class="dot"></span>{txt}</span>'
    return (f'<div class="brandbar"><div class="idwrap">{logo(38)}'
            f'<div><div class="title">{titulo}</div>'
            f'<div class="sub">{subtitulo}</div></div></div>'
            f'<div class="chips">{chip_html}</div></div>')


def kpi(label, value, sub="", tone="navy", hero=False):
    cls = "kpi"
    if hero:
        cls += " hero"
    elif tone in ("good", "green", "verde"):
        cls += " good"
    elif tone in ("warn", "amber", "amarillo"):
        cls += " warn"
    elif tone in ("bad", "red", "rojo"):
        cls += " bad"
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f'<div class="{cls}"><div class="lab">{label}</div><div class="val">{value}</div>{sub_html}</div>'


def badge(texto, tono="navy"):
    color = _TONOS.get(tono, NAVY)
    bg = _TONO_BG.get(tono, "rgba(30,58,138,.10)")
    return (f'<span class="badge" style="background:{bg};color:{color}">'
            f'<span class="dot" style="background:{color}"></span>{texto}</span>')


def seccion(titulo, desc=""):
    d = f'<div class="d">{desc}</div>' if desc else ""
    return f'<div class="sec"><div class="h">{titulo}</div>{d}</div>'


def fmt_money(x):
    try:
        return f"${x:,.0f}"
    except (TypeError, ValueError):
        return "$0"


def usd(x):
    """Para texto markdown/success: 'USD 1,234' (evita que Streamlit lo lea como LaTeX)."""
    try:
        return f"USD {x:,.0f}"
    except (TypeError, ValueError):
        return "USD 0"


def fmt_int(x):
    try:
        return f"{x:,.0f}"
    except (TypeError, ValueError):
        return "0"


def fmt_pct(x, dec=1):
    try:
        return f"{x:.{dec}f}%"
    except (TypeError, ValueError):
        return "0%"
