#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/bsr.py — Estimacion de ventas a partir del BSR (Best Sellers Rank).

POR QUE EXISTE ESTE MODULO
--------------------------
La curva BSR -> ventas/mes ya vivia dentro de data/keepa.py, atada a que una API
PAGA trajera el BSR. Pero el BSR es un dato PUBLICO: figura en la pagina de
cualquier producto de Amazon, en el bloque "Best Sellers Rank". O sea que el
dato caro nunca fue la conversion: era el numero de entrada.

Este modulo separa las dos cosas para que la estimacion funcione GRATIS:
  - pegas el bloque que ves en Amazon (o escribis el BSR a mano),
  - el sistema lo convierte a unidades/mes con la misma curva documentada.

Sirve para CUALQUIER ASIN, incluido uno que todavia no vendes -- que es el caso
de uso real de investigar un producto. No scrapea nada: el dato lo trae el
usuario de una pagina que ya esta mirando.

HONESTIDAD (regla del proyecto: sin datos inventados)
-----------------------------------------------------
Una curva BSR -> ventas es una ESTIMACION GRUESA, no un dato exacto. Es tambien,
exactamente, lo que hacen Jungle Scout y Helium 10 por dentro: la diferencia no
es de metodo sino de calibracion (ellos ajustan la curva con ventas reales de
miles de vendedores). Sirve para ORDENAR candidatos y dimensionar un nicho, no
como verdad fina para proyectar caja al dolar.

El resultado siempre se etiqueta con su fuente para que sea auditable, y toda
estimacion viaja con su `confianza` para que la UI no la muestre como certeza.

La curva base es la de Home & Kitchen (US) que ya estaba en keepa.py: se dejo
NUMERICAMENTE IGUAL para no cambiar el comportamiento de lo que ya funcionaba.
Las categorias se aplican como un FACTOR sobre esa base, y el factor por defecto
es 1.0 -- sin categoria, el resultado es identico al de antes.
"""
import math
import re

# Curva BSR -> ventas/mes (categoria base: Home & Kitchen US). GRUESA y editable.
# Pares (bsr, ventas_mensuales) interpolados en escala log.
# Identica a la que estaba en data/keepa.py: no se toco ningun valor.
CURVA_BASE = [(100, 9000), (500, 3000), (1000, 1800), (5000, 500),
              (10000, 230), (50000, 45), (100000, 18), (500000, 3)]

# Factor por categoria, RELATIVO a Home & Kitchen (= 1.0).
#
# Logica: en una categoria mas grande se venden mas unidades en total, asi que
# un mismo puesto de ranking equivale a mas ventas. Puesto #1.000 en Clothing
# mueve mucho mas que #1.000 en Musical Instruments.
#
# Son APROXIMACIONES para ordenar candidatos, no constantes fisicas. Estan acá,
# en una sola tabla, justamente para que se puedan recalibrar cuando tengas
# ventas reales propias con las que contrastar (ver calibrar()).
FACTOR_CATEGORIA = {
    "clothing, shoes & jewelry": 1.20,
    "books": 0.90,
    "health & household": 0.85,
    "home & kitchen": 1.00,
    "beauty & personal care": 0.80,
    "electronics": 0.75,
    "sports & outdoors": 0.70,
    "toys & games": 0.70,
    "tools & home improvement": 0.65,
    "cell phones & accessories": 0.60,
    "automotive": 0.55,
    "pet supplies": 0.55,
    "grocery & gourmet food": 0.50,
    "patio, lawn & garden": 0.50,
    "office products": 0.45,
    "baby": 0.40,
    "video games": 0.35,
    "arts, crafts & sewing": 0.35,
    "industrial & scientific": 0.30,
    "musical instruments": 0.20,
}

# Alias frecuentes: como Amazon nombra la categoria en español y variantes
# cortas que la gente escribe a mano.
_ALIAS = {
    "hogar y cocina": "home & kitchen",
    "home and kitchen": "home & kitchen",
    "kitchen & dining": "home & kitchen",
    "ropa": "clothing, shoes & jewelry",
    "clothing": "clothing, shoes & jewelry",
    "libros": "books",
    "salud y hogar": "health & household",
    "health and household": "health & household",
    "belleza": "beauty & personal care",
    "beauty": "beauty & personal care",
    "electronica": "electronics",
    "electrónica": "electronics",
    "deportes y aire libre": "sports & outdoors",
    "sports and outdoors": "sports & outdoors",
    "juguetes y juegos": "toys & games",
    "toys and games": "toys & games",
    "herramientas": "tools & home improvement",
    "tools": "tools & home improvement",
    "automotriz": "automotive",
    "productos para mascotas": "pet supplies",
    "mascotas": "pet supplies",
    "alimentos y bebidas": "grocery & gourmet food",
    "grocery": "grocery & gourmet food",
    "jardin": "patio, lawn & garden",
    "jardín": "patio, lawn & garden",
    "oficina": "office products",
    "productos de oficina": "office products",
    "bebe": "baby",
    "bebé": "baby",
    "videojuegos": "video games",
    "instrumentos musicales": "musical instruments",
}


def normalizar_categoria(categoria):
    """Devuelve la clave canonica de FACTOR_CATEGORIA, o None si no la reconoce.

    No adivina por parecido: si no la reconoce devuelve None y el factor queda
    en 1.0 (base). Preferimos un factor neutro antes que uno inventado."""
    if not categoria:
        return None
    c = " ".join(str(categoria).strip().lower().split())
    # Amazon suele agregar cosas como "(See Top 100 in Home & Kitchen)".
    c = re.sub(r"\(.*?\)", "", c).strip()
    c = c.replace(" and ", " & ")
    if c in FACTOR_CATEGORIA:
        return c
    if c in _ALIAS:
        return _ALIAS[c]
    return None


def factor_de(categoria):
    """Factor multiplicador de la categoria. 1.0 (base) si no se reconoce."""
    clave = normalizar_categoria(categoria)
    return FACTOR_CATEGORIA.get(clave, 1.0) if clave else 1.0


def ventas_desde_bsr(bsr, categoria=None):
    """Convierte un BSR en unidades/mes estimadas. 0 si el BSR no es valido.

    Sin `categoria` el resultado es IDENTICO al de la curva historica de
    keepa.py (factor 1.0), asi que ningun llamador viejo cambia de resultado."""
    try:
        bsr = int(bsr)
    except (TypeError, ValueError):
        return 0
    if bsr <= 0:
        return 0

    if bsr <= CURVA_BASE[0][0]:
        base = float(CURVA_BASE[0][1])
    elif bsr >= CURVA_BASE[-1][0]:
        base = float(CURVA_BASE[-1][1])
    else:
        base = 0.0
        for (b1, v1), (b2, v2) in zip(CURVA_BASE, CURVA_BASE[1:]):
            if b1 <= bsr <= b2:
                t = ((math.log10(bsr) - math.log10(b1)) /
                     (math.log10(b2) - math.log10(b1)))
                base = v1 * (v2 / v1) ** t
                break

    return int(round(base * factor_de(categoria)))


def confianza_de(bsr, categoria=None):
    """Que tan confiable es la estimacion: alta / media / baja.

    La curva es mas fiable en el tramo donde hay muchos productos y el ranking
    se mueve poco (BSR chico-medio). En la cola larga (BSR > 200k) el ranking
    salta con una sola venta, asi que ahi cualquier estimacion es floja."""
    try:
        bsr = int(bsr)
    except (TypeError, ValueError):
        return "baja"
    if bsr <= 0:
        return "baja"
    conocida = normalizar_categoria(categoria) is not None
    if bsr > 200000:
        return "baja"
    if bsr > 50000:
        return "media" if conocida else "baja"
    return "alta" if conocida else "media"


# --------------------------------------------------------------------------- #
# Parser del bloque publico de Amazon
# --------------------------------------------------------------------------- #

# "#1,234 in Home & Kitchen"  /  "nº1.234 en Hogar y cocina"  /  "No. 1234 in X"
_RE_RANK = re.compile(
    r"(?:#|n[.º°o]{0,3}\s*|no\.?\s*)"      # #, nº, n.º, No.
    r"([\d][\d., \s]*)"                          # 1,234 / 1.234 / 1 234
    r"\s*(?:in|en)\s+"                                # in / en
    r"([^\n(#]+)",                                    # nombre de categoria
    re.IGNORECASE)


def _mil(n):
    """12345 -> '12.345' (separador de miles rioplatense).

    Se formatea SOLO el numero: aplicar un replace(',', '.') sobre el mensaje
    entero se comia las comas de la prosa."""
    return f"{int(n):,}".replace(",", ".")


def _a_entero(txt):
    """'1,234' / '1.234' / '1 234' -> 1234. None si no queda un entero."""
    limpio = re.sub(r"[^\d]", "", txt or "")
    if not limpio:
        return None
    try:
        return int(limpio)
    except ValueError:
        return None


def parsear_bloque(texto):
    """Extrae (bsr, categoria) del bloque 'Best Sellers Rank' de Amazon.

    Acepta que le pegues el bloque entero, con subcategorias incluidas:

        Best Sellers Rank: #1,234 in Home & Kitchen (See Top 100 in Home & Kitchen)
                           #5 in Cutting Boards

    Se queda con el PRIMER rank, que es el de la categoria principal. Es a
    proposito: el rank de subcategoria (#5) es un numero chico y, pasado por la
    curva, daria una estimacion disparatada hacia arriba. La curva esta
    calibrada contra el ranking general, no contra el de subcategoria.

    Devuelve {ok, bsr, categoria, mensaje}. Si no encuentra nada, ok=False y NO
    inventa: avisa que hay que pegar el bloque o escribir el BSR a mano.
    """
    texto = (texto or "").strip()
    if not texto:
        return {"ok": False, "bsr": None, "categoria": None,
                "mensaje": "Pegá el bloque \"Best Sellers Rank\" de la página del "
                           "producto en Amazon, o escribí el número de BSR."}

    # Caso simple: el usuario escribio solo el numero.
    if re.fullmatch(r"[\d., \s]+", texto):
        n = _a_entero(texto)
        if n and n > 0:
            return {"ok": True, "bsr": n, "categoria": None,
                    "mensaje": "BSR leído sin categoría: se usa la curva base. "
                               "Si además pegás la categoría, la estimación afina."}
        return {"ok": False, "bsr": None, "categoria": None,
                "mensaje": "Ese número de BSR no es válido."}

    m = _RE_RANK.search(texto)
    if not m:
        return {"ok": False, "bsr": None, "categoria": None,
                "mensaje": "No encontré un ranking con el formato \"#1,234 in "
                           "Categoría\". Pegá el bloque tal cual sale en Amazon o "
                           "escribí sólo el número de BSR."}

    bsr = _a_entero(m.group(1))
    if not bsr or bsr <= 0:
        return {"ok": False, "bsr": None, "categoria": None,
                "mensaje": "No pude leer el número de BSR del texto pegado."}

    categoria = m.group(2) or ""
    # Cortes de ruido cuando la linea viene de una tabla pegada: el parentesis
    # de "(See Top 100 in ...)", un precio a la derecha, o dos o mas espacios
    # (que en un pegado tabular separan columnas, no palabras de la categoria).
    categoria = re.split(r"\(|\bUS\$|\$|\s{2,}|\t|\||;", categoria)[0]
    categoria = " ".join(categoria.split()).strip(" .,-")
    conocida = normalizar_categoria(categoria)
    if categoria and not conocida:
        msg = (f"BSR {_mil(bsr)} leído. La categoría \"{categoria}\" no está en la "
               "tabla, así que se usa la curva base (sin ajuste por categoría).")
    elif categoria:
        msg = f"BSR {_mil(bsr)} en {categoria} leído correctamente."
    else:
        msg = f"BSR {_mil(bsr)} leído (sin categoría: curva base)."
    return {"ok": True, "bsr": bsr, "categoria": categoria or None, "mensaje": msg}


def estimar(texto_o_bsr, categoria=None):
    """Camino completo: texto pegado (o BSR suelto) -> estimacion de ventas/mes.

    Devuelve {ok, bsr, categoria, ventas_estim, confianza, fuente, mensaje}.
    Nunca inventa: si no puede leer el BSR devuelve ok=False.
    """
    if isinstance(texto_o_bsr, (int, float)) and not isinstance(texto_o_bsr, bool):
        leido = {"ok": True, "bsr": int(texto_o_bsr), "categoria": categoria,
                 "mensaje": ""}
    else:
        leido = parsear_bloque(texto_o_bsr)
        if categoria and leido.get("ok"):
            leido["categoria"] = categoria          # el explicito manda

    if not leido.get("ok"):
        return {"ok": False, "bsr": None, "categoria": None, "ventas_estim": None,
                "confianza": None, "fuente": None, "mensaje": leido["mensaje"]}

    bsr, cat = leido["bsr"], leido.get("categoria")
    if bsr <= 0:
        return {"ok": False, "bsr": None, "categoria": None, "ventas_estim": None,
                "confianza": None, "fuente": None,
                "mensaje": "El BSR tiene que ser un número positivo."}

    ventas = ventas_desde_bsr(bsr, cat)
    conf = confianza_de(bsr, cat)
    cat_txt = f" en {cat}" if cat else ""
    return {
        "ok": True, "bsr": bsr, "categoria": cat, "ventas_estim": ventas,
        "confianza": conf, "fuente": "BSR de Amazon (curva)",
        "mensaje": (f"BSR #{_mil(bsr)}{cat_txt} → ~{_mil(ventas)} u/mes estimadas "
                    f"(confianza {conf}). Es una estimación por curva, igual que "
                    "la que hacen Jungle Scout y Helium 10."),
    }


def calibrar(bsr, unidades_mes_reales, categoria=None):
    """Compara la curva contra una venta REAL tuya y dice cuanto se desvia.

    No cambia la curva sola (eso seria tocar la logica sin que la pidas): te
    devuelve el factor de correccion para que decidas vos si recalibrar
    FACTOR_CATEGORIA con tus propios numeros."""
    est = ventas_desde_bsr(bsr, categoria)
    try:
        reales = float(unidades_mes_reales)
    except (TypeError, ValueError):
        return {"ok": False, "mensaje": "Las unidades reales tienen que ser un número."}
    if est <= 0 or reales <= 0:
        return {"ok": False, "mensaje": "Hacen falta un BSR válido y ventas reales > 0."}
    factor = reales / est
    return {"ok": True, "bsr": int(bsr), "categoria": categoria,
            "estimado": est, "real": int(reales), "factor_correccion": round(factor, 3),
            "mensaje": (f"Para BSR #{_mil(bsr)} la curva estima {_mil(est)} u/mes y "
                        f"vos vendiste {_mil(reales)}. Factor de corrección: "
                        f"{factor:.2f}×.")}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        description="Estima ventas/mes desde el BSR publico de Amazon (sin API).")
    ap.add_argument("--bsr", help="BSR o bloque 'Best Sellers Rank' pegado.")
    ap.add_argument("--categoria", default=None, help="Categoria principal.")
    a = ap.parse_args(argv)
    if not a.bsr:
        ap.error("Pasá --bsr con el número o el bloque pegado de Amazon.")
    import json as _json
    print(_json.dumps(estimar(a.bsr, a.categoria), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
