#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/cerebro.py — Fuente de keywords estilo Helium 10 Cerebro para el sistema FBA.

Hermano de data/importyeti.py. Mismo contrato de diseño:
  - MODO DEMO: datos [DEMO] ilustrativos, sin gastar nada.
  - PRODUCCION: NO inventa datos. Si no hay export CSV de Cerebro, devuelve
    estado vacio explicado (igual que ImportYeti sin APIFY_TOKEN).

POR QUE CSV
-----------
Helium 10 NO expone Cerebro por API en planes Platinum/Diamond (API solo Enterprise).
El camino sostenible es exportar el CSV de la tabla de keywords ("Export Data") o usar
Keepa como fuente programatica. Este modulo consume ese CSV.

STANDALONE + IMPORTABLE
-----------------------
  python cerebro.py --demo
  python cerebro.py --csv "Cerebro_B0XXXX.csv"
  python cerebro.py --categoria "cocina eco" --auto --json
Y desde el paquete:
  from data.cerebro import procesar_categoria, cerebro_con_estado, \
      enriquecer_market_intel, keywords_para_listing

DEPENDENCIAS: solo libreria estandar (csv, json, math, statistics, argparse, os, glob).
"""

import argparse
import csv
import glob
import json
import math
import os
import statistics
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

# --------------------------------------------------------------------------- #
# 0) CONFIG SELF-CONTAINED (no depende de config.py; lee .env si existe)
# --------------------------------------------------------------------------- #
def _cargar_dotenv():
    """Carga .env de la carpeta del modulo o del cwd, sin pisar variables ya seteadas."""
    rutas = []
    here = os.path.dirname(os.path.abspath(__file__))
    rutas.append(os.path.join(here, ".env"))
    rutas.append(os.path.join(os.path.dirname(here), ".env"))  # raiz del paquete
    rutas.append(os.path.join(os.getcwd(), ".env"))
    for ruta in rutas:
        if not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if not linea or linea.startswith("#") or "=" not in linea:
                        continue
                    k, v = linea.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    os.environ.setdefault(k, v)
        except OSError:
            pass


_cargar_dotenv()


def _env(clave, default=""):
    return os.environ.get(clave, default)


def _env_bool(clave, default=False):
    v = _env(clave, "1" if default else "0").strip().lower()
    return v in ("1", "true", "yes", "si", "sí", "on")


# Carpeta donde el usuario deja los export de Cerebro (.csv)
CEREBRO_CSV_DIR = _env("CEREBRO_CSV_DIR",
                       os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "cerebro_exports"))
USAR_CEREBRO = _env_bool("USAR_CEREBRO", True)
MARKETPLACE = _env("CEREBRO_MARKETPLACE", "US")


# --------------------------------------------------------------------------- #
# 1) ESQUEMA DE COLUMNAS — alias reales del export Cerebro (ingles / espaniol)
# --------------------------------------------------------------------------- #
COLUMN_ALIASES = {
    "keyword": ["keyword phrase", "keyword", "frase clave", "palabra clave"],
    "search_volume": ["search volume", "volumen de busqueda", "volumen de búsqueda"],
    "trend_pct": ["search volume trend", "tendencia del volumen",
                  "tendencia del volumen de búsquedas", "search volume trend (%)"],
    "cerebro_iq": ["cerebro iq score", "puntuacion cerebro iq",
                   "puntuación cerebro iq", "cerebro iq"],
    "competing": ["competing products", "productos de la competencia"],
    "cpr": ["cpr"],
    "title_density": ["title density", "densidad de titulos", "densidad de títulos"],
    "sponsored_asins": ["sponsored asins", "asin patrocinados"],
    "organic_rank": ["organic rank", "posicion organica", "posición orgánica"],
    "sponsored_rank": ["sponsored rank", "posicion patrocinada", "posición patrocinada"],
    "keyword_sales": ["keyword sales", "ventas por palabras clave",
                      "ventas por palabra clave"],
    "match_type": ["match type", "tipo de coincidencia"],
    "word_count": ["word count", "recuento de palabras"],
}


def _num(x, default=0.0, eu=False):
    """
    Parsea numeros de export tolerando %, $, N/A.
    eu=False (CSV delimitado por coma, formato US): ',' = miles, '.' = decimal.
    eu=True  (CSV delimitado por ';', formato europeo): '.' = miles, ',' = decimal.
    El locale se deduce del delimitador del CSV, asi 4.300 (EU) -> 4300, no 4.3.
    """
    if x is None:
        return default
    s = str(x).strip()
    if s in ("", "N/A", "n/a", "-", "—", "NaN", "nan", "None"):
        return default
    for ch in ("%", "$", ">", "<", " ", "\u00a0"):
        s = s.replace(ch, "")
    if eu:
        s = s.replace(".", "").replace(",", ".")          # 1.234,56 -> 1234.56
    elif "," in s and "." in s:
        s = s.replace(",", "")                              # 1,234.56 -> 1234.56
    elif "," in s:
        partes = s.split(",")
        if len(partes) >= 2 and len(partes[-1]) == 3:
            s = s.replace(",", "")                          # 1,234 (miles) -> 1234
        else:
            s = s.replace(",", ".")                          # 12,5 (decimal) -> 12.5
    try:
        return float(s)
    except ValueError:
        return default


@dataclass
class Keyword:
    keyword: str
    search_volume: float = 0.0
    trend_pct: float = 0.0
    cerebro_iq: float = 0.0
    competing: float = 0.0
    cpr: float = 0.0
    title_density: float = 0.0
    sponsored_asins: float = 0.0
    organic_rank: float = 0.0
    sponsored_rank: float = 0.0
    keyword_sales: float = 0.0
    match_type: str = ""
    word_count: float = 0.0
    opp_score: float = 0.0
    opp_breakdown: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 2) CARGA CSV (robusta: sniff de delimitador, BOM, dedupe)
# --------------------------------------------------------------------------- #
def _resolver_columnas(headers):
    norm = {(h or "").strip().lower(): h for h in headers}
    mapeo = {}
    for clave, alias in COLUMN_ALIASES.items():
        for a in alias:
            if a in norm:
                mapeo[clave] = norm[a]
                break
    return mapeo


def parse_cerebro_csv(path: str) -> list:
    """Lee un export de Cerebro. Sniff de ',' o ';'. Dedupe por keyword (mayor volumen)."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        muestra = f.read(8192)
        f.seek(0)
        try:
            dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t")
        except csv.Error:
            dialecto = csv.excel
        reader = csv.DictReader(f, dialect=dialecto)
        if not reader.fieldnames:
            return []
        eu = getattr(dialecto, "delimiter", ",") == ";"   # CSV europeo (Excel es-UY)
        m = _resolver_columnas(reader.fieldnames)
        if "keyword" not in m or "search_volume" not in m:
            raise ValueError(
                "El CSV no parece export de Cerebro: faltan 'Keyword Phrase' "
                "y/o 'Search Volume'. Columnas vistas: "
                + ", ".join(h for h in reader.fieldnames if h)
            )
        por_kw = {}
        for row in reader:
            nombre = str(row.get(m["keyword"], "")).strip()
            if not nombre:
                continue

            def n(clave):
                return _num(row.get(m.get(clave)), eu=eu)

            kw = Keyword(
                keyword=nombre,
                search_volume=n("search_volume"),
                trend_pct=n("trend_pct"),
                cerebro_iq=n("cerebro_iq"),
                competing=n("competing"),
                cpr=n("cpr"),
                title_density=n("title_density"),
                sponsored_asins=n("sponsored_asins"),
                organic_rank=n("organic_rank"),
                sponsored_rank=n("sponsored_rank"),
                keyword_sales=n("keyword_sales"),
                match_type=str(row.get(m.get("match_type"), "")).strip().upper()[:1],
                word_count=n("word_count"),
            )
            if kw.word_count == 0 and kw.keyword:
                kw.word_count = len(kw.keyword.split())
            prev = por_kw.get(nombre.lower())
            if prev is None or kw.search_volume > prev.search_volume:
                por_kw[nombre.lower()] = kw
    keywords = list(por_kw.values())
    for kw in keywords:
        kw.opp_score, kw.opp_breakdown = opportunity_score(kw)
    return keywords


def _buscar_csv(categoria: Optional[str]) -> Optional[str]:
    """Busca un .csv en CEREBRO_CSV_DIR. Si hay categoria, prioriza match por nombre."""
    if not os.path.isdir(CEREBRO_CSV_DIR):
        return None
    archivos = sorted(glob.glob(os.path.join(CEREBRO_CSV_DIR, "*.csv")),
                      key=os.path.getmtime, reverse=True)
    if not archivos:
        return None
    if categoria:
        tokens = [t for t in categoria.lower().split() if len(t) > 2]
        for a in archivos:
            base = os.path.basename(a).lower()
            if any(t in base for t in tokens):
                return a
    return archivos[0]  # el mas reciente


# --------------------------------------------------------------------------- #
# 3) SCORING DE OPORTUNIDAD (pesos explicitos, auditable)
# --------------------------------------------------------------------------- #
PESOS_OPP = {"volumen": 0.30, "title_density": 0.25, "competidores": 0.20,
             "cpr": 0.15, "tendencia": 0.10}


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def opportunity_score(kw: Keyword):
    vol = _clamp(math.log10(max(kw.search_volume, 1)) / math.log10(50000))
    td = _clamp(1 - kw.title_density / 12.0)
    comp = _clamp(1 - math.log10(max(kw.competing, 1)) / math.log10(10000))
    cpr = _clamp(1 - kw.cpr / 60.0)
    tend = _clamp(0.5 + kw.trend_pct / 200.0)
    bd = {"volumen": round(vol, 3), "title_density": round(td, 3),
          "competidores": round(comp, 3), "cpr": round(cpr, 3),
          "tendencia": round(tend, 3)}
    score = sum(PESOS_OPP[k] * bd[k] for k in PESOS_OPP)
    return round(score * 100), bd


# --------------------------------------------------------------------------- #
# 4) CLASIFICACION Top vs Opportunity
# --------------------------------------------------------------------------- #
def _percentil(vals, p):
    if not vals:
        return 0.0
    vals = sorted(vals)
    k = (len(vals) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return vals[int(k)]
    return vals[f] * (c - k) + vals[c] * (k - f)


def clasificar(keywords: list, td_max=8, vol_min_opp=200, opp_min=60) -> dict:
    if not keywords:
        return {"top": [], "opportunity": [], "todas": []}
    p75 = _percentil([k.search_volume for k in keywords], 0.75)
    top, opp = [], []
    for k in keywords:
        if k.search_volume >= p75 and k.keyword_sales > 0:
            top.append(k)
        if (k.opp_score >= opp_min and k.title_density <= td_max
                and k.search_volume >= vol_min_opp):
            opp.append(k)
    top.sort(key=lambda x: x.search_volume, reverse=True)
    opp.sort(key=lambda x: x.opp_score, reverse=True)
    return {"top": top, "opportunity": opp, "todas": keywords}


# --------------------------------------------------------------------------- #
# 5) ENRIQUECIMIENTO PARA agents/market_intel.py
# --------------------------------------------------------------------------- #
def enriquecer_market_intel(keywords: list, keyword_principal: str = "", top_n=10) -> dict:
    """
    Devuelve los 3 inputs de la formula score_nicho documentada:
        demanda          = min(demanda_mensual / 5000, 1)
        baja_competencia = max(0, 1 - competidores / 40)
        necesidad_valor  = oportunidad_valor / 100
        score_nicho      = round((0.35*d + 0.30*bc + 0.35*nv) * 100)
    """
    if not keywords:
        return {"keyword_principal": keyword_principal, "demanda_mensual": 0,
                "competidores": 0, "oportunidad_valor": 0, "score_nicho": 0,
                "n_keywords": 0, "n_oportunidad": 0, "fuente": "vacio"}
    por_vol = sorted(keywords, key=lambda k: k.search_volume, reverse=True)
    top = por_vol[:top_n]
    demanda_mensual = sum(k.search_volume for k in top)
    competidores = statistics.median([k.title_density for k in top]) if top else 0
    clas = clasificar(keywords)
    if clas["opportunity"]:
        oportunidad_valor = statistics.mean([k.opp_score for k in clas["opportunity"]])
    else:
        oportunidad_valor = statistics.mean([k.opp_score for k in top]) if top else 0
    demanda = min(demanda_mensual / 5000.0, 1.0)
    baja_competencia = max(0.0, 1 - competidores / 40.0)
    necesidad_valor = oportunidad_valor / 100.0
    score_nicho = round((0.35 * demanda + 0.30 * baja_competencia
                         + 0.35 * necesidad_valor) * 100)
    return {"keyword_principal": keyword_principal,
            "demanda_mensual": int(demanda_mensual),
            "competidores": round(competidores, 1),
            "oportunidad_valor": round(oportunidad_valor),
            "score_nicho": score_nicho, "n_keywords": len(keywords),
            "n_oportunidad": len(clas["opportunity"]), "fuente": "Cerebro CSV"}


def veredicto_nicho(keywords: list) -> dict:
    mi = enriquecer_market_intel(keywords)
    s, n_opp = mi["score_nicho"], mi["n_oportunidad"]
    if s >= 55 and n_opp >= 3:
        color, txt = "VERDE", "Hueco rankeable real. Avanzar a sourcing/muestra."
    elif s >= 40:
        color, txt = "AMARILLO", "Marginal: demanda ok pero hueco chico. Diferenciar fuerte o descartar."
    else:
        color, txt = "ROJO", "Saturado o baja demanda. No invertir capital."
    return {**mi, "veredicto": color, "comentario": txt}


# --------------------------------------------------------------------------- #
# 6) KEYWORDS PARA agents/listing.py
# --------------------------------------------------------------------------- #
def keywords_para_listing(keywords: list) -> dict:
    if not keywords:
        return {"titulo": [], "bullets": [], "backend": []}
    organicas = [k for k in keywords if k.match_type in ("O", "")]
    organicas.sort(key=lambda k: k.search_volume, reverse=True)
    titulo = [k.keyword for k in organicas if k.word_count <= 4][:5]
    clas = clasificar(keywords)
    bullets, usados = [], set(titulo)
    for k in clas["opportunity"]:
        if k.keyword not in usados:
            bullets.append(k.keyword)
            usados.add(k.keyword)
        if len(bullets) >= 8:
            break
    backend = []
    for k in sorted(keywords, key=lambda k: k.search_volume, reverse=True):
        if k.keyword not in usados:
            backend.append(k.keyword)
            usados.add(k.keyword)
        if len(backend) >= 15:
            break
    return {"titulo": titulo, "bullets": bullets, "backend": backend}


# --------------------------------------------------------------------------- #
# 7) DEMO (cocina eco / US) — todo prefijado [DEMO]
# --------------------------------------------------------------------------- #
def demo_keywords() -> list:
    crudo = [
        ("[DEMO] bamboo kitchen utensils set", 18500, 12, 4342, 1200, 28, 5, 6, 14, 8, 1850, "O", 4),
        ("[DEMO] silicone cooking utensils set", 22100, -6, 3780, 2400, 41, 9, 12, 22, 5, 2240, "O", 4),
        ("[DEMO] wooden spoons for cooking", 9800, 4, 5210, 640, 19, 3, 2, 9, 0, 980, "O", 4),
        ("[DEMO] eco friendly kitchen utensils", 4300, 28, 6100, 380, 14, 2, 1, 5, 0, 410, "O", 4),
        ("[DEMO] bamboo utensil holder", 6700, 9, 4880, 520, 17, 4, 3, 11, 7, 720, "O", 3),
        ("[DEMO] non scratch cooking utensils", 3100, 18, 5600, 290, 12, 2, 0, 4, 0, 330, "O", 4),
        ("[DEMO] silicone spatula set", 14200, -12, 1725, 3200, 48, 11, 18, 27, 4, 1410, "O", 3),
        ("[DEMO] kitchen utensil set", 41000, -3, 1100, 9200, 55, 16, 22, 38, 2, 4100, "O", 3),
        ("[DEMO] bamboo cooking utensils", 7600, 15, 4990, 470, 16, 3, 2, 8, 0, 760, "O", 3),
        ("[DEMO] heat resistant cooking utensils", 5200, 7, 5340, 410, 15, 4, 5, 13, 6, 540, "O", 4),
        ("[DEMO] silicone kitchen tools", 8900, 2, 3010, 1900, 33, 8, 10, 19, 9, 880, "A", 3),
        ("[DEMO] wooden cooking utensils set", 6100, 11, 4710, 540, 18, 4, 3, 10, 0, 610, "O", 4),
        ("[DEMO] kitchen gadgets eco", 1800, 33, 6400, 210, 11, 1, 0, 3, 0, 190, "O", 3),
        ("[DEMO] nonstick safe utensils", 2600, 22, 5900, 260, 13, 2, 1, 6, 0, 270, "O", 3),
        ("[DEMO] cooking utensils gift set", 3400, -8, 2200, 2800, 44, 13, 16, 31, 3, 320, "S", 4),
    ]
    kws = []
    for (k, v, tr, iq, cp, cpr, td, sp, orank, srank, sales, mt, wc) in crudo:
        kw = Keyword(k, v, tr, iq, cp, cpr, td, sp, orank, srank, sales, mt, wc)
        kw.opp_score, kw.opp_breakdown = opportunity_score(kw)
        kws.append(kw)
    return kws


# --------------------------------------------------------------------------- #
# 8) API DE PRODUCCION (lo que llaman dashboard / n8n / agentes)
# --------------------------------------------------------------------------- #
def cerebro_con_estado(categoria: Optional[str] = None, csv_path: Optional[str] = None,
                       demo: bool = False):
    """
    Mirror de sourcing_con_estado / ImportYeti. Devuelve (keywords, estado).
    estado = {ok, fuente, archivo, mensaje}. NUNCA inventa datos en produccion.
    """
    if demo or _env_bool("MODO_DEMO", False):
        return demo_keywords(), {"ok": True, "fuente": "DEMO", "archivo": None,
                                 "mensaje": "Datos [DEMO] ilustrativos (no reales)."}
    if not USAR_CEREBRO:
        return [], {"ok": False, "fuente": "desactivado", "archivo": None,
                    "mensaje": "USAR_CEREBRO=0. Activalo en .env para usar Cerebro."}
    ruta = csv_path or _buscar_csv(categoria)
    if not ruta:
        return [], {"ok": False, "fuente": "sin_datos", "archivo": None,
                    "mensaje": (f"No hay export de Cerebro en {CEREBRO_CSV_DIR}. "
                                "Exporta la tabla de keywords ('Export Data') y deja "
                                "el .csv ahi. El sistema no inventa datos.")}
    if not os.path.isfile(ruta):
        return [], {"ok": False, "fuente": "error", "archivo": ruta,
                    "mensaje": f"No existe el archivo: {ruta}"}
    try:
        kws = parse_cerebro_csv(ruta)
    except (ValueError, OSError) as e:
        return [], {"ok": False, "fuente": "error", "archivo": ruta,
                    "mensaje": f"Error leyendo {os.path.basename(ruta)}: {e}"}
    if not kws:
        return [], {"ok": False, "fuente": "vacio", "archivo": ruta,
                    "mensaje": f"{os.path.basename(ruta)} no tiene filas de keywords."}
    return kws, {"ok": True, "fuente": "Cerebro CSV", "archivo": ruta,
                 "mensaje": f"{len(kws)} keywords desde {os.path.basename(ruta)}."}


def procesar_categoria(categoria: Optional[str] = None, csv_path: Optional[str] = None,
                       demo: bool = False) -> dict:
    """Entrada unica de alto nivel: todo lo que el dashboard/n8n necesita."""
    kws, estado = cerebro_con_estado(categoria, csv_path, demo)
    if not kws:
        return {"ok": False, "estado": estado, "marketplace": MARKETPLACE,
                "veredicto": None, "listing": None, "market_intel": None,
                "opportunity": [], "top": []}
    clas = clasificar(kws)
    return {"ok": True, "estado": estado, "marketplace": MARKETPLACE,
            "categoria": categoria, "veredicto": veredicto_nicho(kws),
            "market_intel": enriquecer_market_intel(kws, categoria or ""),
            "listing": keywords_para_listing(kws),
            "opportunity": [asdict(k) for k in clas["opportunity"]],
            "top": [asdict(k) for k in clas["top"]]}


# --------------------------------------------------------------------------- #
# 9) INFORME DE TEXTO
# --------------------------------------------------------------------------- #
def informe(res: dict) -> str:
    if not res.get("ok"):
        return "[Cerebro] " + res["estado"]["mensaje"]
    v, clas_opp = res["veredicto"], res["opportunity"]
    lst = res["listing"]
    out = ["=" * 64,
           f"INVESTIGACION DE NICHO — Cerebro  ({res['estado']['fuente']}, mkt={res['marketplace']})",
           "=" * 64,
           f"Keywords analizadas : {v['n_keywords']}",
           f"Demanda mensual top : {v['demanda_mensual']:,} busquedas/mes",
           f"Competidores (med.) : {v['competidores']}  (densidad de titulos pag.1)",
           f"Oportunidad de valor: {v['oportunidad_valor']}/100",
           f"SCORE DE NICHO      : {v['score_nicho']}/100",
           f"VEREDICTO           : {v['veredicto']} — {v['comentario']}",
           "",
           f"OPPORTUNITY KEYWORDS ({len(clas_opp)}):"]
    for k in clas_opp[:8]:
        out.append(f"  [{k['opp_score']:>3}] {k['keyword']:<42} vol={int(k['search_volume']):>6}  "
                   f"TD={int(k['title_density']):>2}  CPR={int(k['cpr']):>2}  tend={k['trend_pct']:+.0f}%")
    out += ["", "KEYWORDS PARA EL LISTING:",
            "  Titulo : " + ", ".join(lst["titulo"]),
            "  Bullets: " + ", ".join(lst["bullets"][:5]),
            "  Backend: " + ", ".join(lst["backend"][:8]),
            "=" * 64]
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# 10) CLI
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="Investigacion de keywords estilo Cerebro (FBA).")
    ap.add_argument("--csv", help="Ruta al export CSV de Cerebro.")
    ap.add_argument("--categoria", help="Nicho/keyword principal (busca CSV en CEREBRO_CSV_DIR).")
    ap.add_argument("--demo", action="store_true", help="Datos [DEMO] (cocina eco / US).")
    ap.add_argument("--json", action="store_true", help="Salida JSON (n8n / dashboard).")
    ap.add_argument("--auto", action="store_true", help="Task Scheduler: JSON a stdout, sin texto.")
    args = ap.parse_args(argv)

    res = procesar_categoria(categoria=args.categoria, csv_path=args.csv, demo=args.demo)

    if args.json or args.auto:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(informe(res))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
