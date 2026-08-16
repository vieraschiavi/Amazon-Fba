#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
core/db.py — SQLite del sistema FBA. Esquema segun DOCUMENTACION.md.
Helpers: init(reset=False), insert(table, **cols), rows(sql, params=()), connect().
"""
import os
import sqlite3
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
import config  # noqa: E402

ESQUEMA = {
    "products": """CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, asin TEXT, costo REAL,
        flete REAL, arancel_pct REAL, prep REAL, fba_fee REAL, landed REAL,
        precio REAL, neto REAL, margen REAL, roi REAL, semaforo TEXT,
        techo_demanda INTEGER, marketplace TEXT, notas TEXT,
        stock INTEGER, lead_time_dias INTEGER, stock_fecha TEXT,
        ventas_estim_mes INTEGER, ventas_estim_fuente TEXT, ventas_estim_fecha TEXT,
        ventas_estim_confianza TEXT, bsr INTEGER, bsr_categoria TEXT,
        activo INTEGER DEFAULT 1, fecha TEXT DEFAULT (datetime('now')))""",
    "listings": """CREATE TABLE IF NOT EXISTS listings(
        id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, titulo TEXT,
        bullets TEXT, descripcion TEXT, banner_brief TEXT,
        fecha TEXT DEFAULT (datetime('now')))""",
    "orders": """CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, asin TEXT, unidades INTEGER, precio REAL,
        neto_unitario REAL, ingreso REAL, neto REAL, pais TEXT, segmento TEXT,
        product_id INTEGER, fecha TEXT DEFAULT (datetime('now')))""",
    "messages": """CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, texto TEXT, categoria TEXT,
        confianza REAL, respuesta TEXT, requiere_aprobacion INTEGER,
        fecha TEXT DEFAULT (datetime('now')))""",
    "alerts_outbox": """CREATE TABLE IF NOT EXISTS alerts_outbox(
        id INTEGER PRIMARY KEY AUTOINCREMENT, para TEXT, asunto TEXT, cuerpo TEXT,
        enviado INTEGER, fecha TEXT DEFAULT (datetime('now')))""",
    "seleccion": """CREATE TABLE IF NOT EXISTS seleccion(
        id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT, proveedor TEXT, contacto TEXT,
        pais TEXT, costo REAL, precio REAL, margen REAL, roi REAL, score REAL, nicho REAL,
        segmento TEXT, marketplace TEXT, fecha TEXT DEFAULT (datetime('now')))""",
    "seguimiento": """CREATE TABLE IF NOT EXISTS seguimiento(
        id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT, proveedor TEXT, etapa TEXT,
        nota TEXT, fecha TEXT DEFAULT (datetime('now')))""",
    "checklist": """CREATE TABLE IF NOT EXISTS checklist(
        clave TEXT PRIMARY KEY, hecho INTEGER, fecha TEXT)""",
    "recordatorios": """CREATE TABLE IF NOT EXISTS recordatorios(
        id INTEGER PRIMARY KEY AUTOINCREMENT, producto TEXT, proveedor TEXT, tipo TEXT,
        vence TEXT, enviado INTEGER)""",
}


def connect():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


# Columnas agregadas despues de la primera version del esquema: se migran con
# ALTER TABLE para no romper bases ya creadas.
_MIGRACIONES = {
    "products": {"asin": "TEXT", "fba_fee": "REAL", "neto": "REAL",
                 "techo_demanda": "INTEGER", "notas": "TEXT",
                 "stock": "INTEGER", "lead_time_dias": "INTEGER",
                 "stock_fecha": "TEXT", "activo": "INTEGER DEFAULT 1",
                 # Estimacion de ventas de mercado por ASIN (Jungle Scout o
                 # Keepa): cuanto vende ESE producto en Amazon, guardado en la
                 # ficha con su fuente y fecha para que sea auditable.
                 "ventas_estim_mes": "INTEGER", "ventas_estim_fuente": "TEXT",
                 "ventas_estim_fecha": "TEXT",
                 # BSR publico de la pagina de Amazon: lo carga el usuario y
                 # permite estimar ventas GRATIS, sin ninguna API paga. Se
                 # guarda para poder re-estimar y para auditar de donde salio.
                 "ventas_estim_confianza": "TEXT", "bsr": "INTEGER",
                 "bsr_categoria": "TEXT"},
    # orders viejas (creadas antes de estas columnas) rompian el registro de
    # ventas con "table orders has no column named neto_unitario".
    "orders": {"neto_unitario": "REAL", "ingreso": "REAL", "neto": "REAL",
               "pais": "TEXT", "segmento": "TEXT", "product_id": "INTEGER"},
}


def _migrar(con):
    for tabla, columnas in _MIGRACIONES.items():
        existentes = {r[1] for r in con.execute(f"PRAGMA table_info({tabla})")}
        for col, tipo in columnas.items():
            if col not in existentes:
                con.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")


def init(reset=False):
    if reset and os.path.isfile(config.DB_PATH):
        os.remove(config.DB_PATH)
    con = connect()
    try:
        for ddl in ESQUEMA.values():
            con.execute(ddl)
        _migrar(con)
        con.commit()
    except sqlite3.OperationalError as e:
        # "database or disk is full" es un problema del DISCO, no del programa,
        # pero sqlite lo tira como un traceback crudo que no le dice nada a
        # quien compro esto. Se traduce a algo accionable, diciendo DONDE
        # escribe la base -- que no es la carpeta de instalacion: va a
        # %LOCALAPPDATA% (ver _dir_datos en config.py), asi que el disco que
        # hay que liberar suele ser C: aunque el programa este instalado en D:.
        if "disk is full" in str(e).lower():
            raise RuntimeError(
                "No hay espacio en el disco para la base de datos.\n"
                f"La base se guarda en: {config.DB_PATH}\n"
                "Liberá espacio en ese disco (normalmente C:, aunque hayas "
                "instalado el programa en otro) y volvé a abrir el programa."
            ) from e
        raise
    finally:
        con.close()


def execute(sql, params=()):
    con = connect()
    try:
        cur = con.execute(sql, params)
        con.commit()
        return cur.rowcount
    finally:
        con.close()


def insert(table, **cols):
    keys = ",".join(cols.keys())
    ph = ",".join("?" for _ in cols)
    sql = f"INSERT INTO {table}({keys}) VALUES({ph})"
    valores = tuple(cols.values())
    try:
        con = connect()
        try:
            cur = con.execute(sql, valores)
            con.commit()
            return cur.lastrowid
        finally:
            con.close()
    except sqlite3.OperationalError as e:
        # Auto-reparacion: si a la tabla le falta una columna (base vieja creada
        # antes de una migracion), corremos las migraciones y reintentamos una vez
        # en vez de romper la app entera.
        if "has no column named" not in str(e) and "no such table" not in str(e):
            raise
        init()
        con = connect()
        try:
            cur = con.execute(sql, valores)
            con.commit()
            return cur.lastrowid
        finally:
            con.close()


def rows(sql, params=()):
    con = connect()
    try:
        return [dict(r) for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()


if __name__ == "__main__":
    init(reset="--reset" in sys.argv)
    print(f"DB lista en {config.DB_PATH}")
    print("Tablas:", [r["name"] for r in rows(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")])
