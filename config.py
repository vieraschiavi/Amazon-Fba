#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py — Configuracion central del sistema FBA. Lee .env (sin pisar el entorno).
Sin claves -> modo offline / dry-run (no inventa datos, no envia mails).
"""
import os

_AQUI = os.path.dirname(os.path.abspath(__file__))


def _dir_datos():
    """Carpeta de datos DEL USUARIO (base, .env, CSV), separada del programa.

    Antes todo esto vivia dentro de la carpeta de instalacion, lo que obligaba a
    instalar en %LOCALAPPDATA% (en "Archivos de programa" Windows bloquea la
    escritura). Separandolo, el instalador puede dejar elegir cualquier carpeta.
    Se puede forzar con MVFBA_DATA_DIR (util para tests y portable).
    """
    forzado = os.environ.get("MVFBA_DATA_DIR", "").strip()
    if forzado:
        return forzado
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "MV FBA IA")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "mv-fba-ia")


DIR_DATOS = _dir_datos()
try:
    os.makedirs(DIR_DATOS, exist_ok=True)
except OSError:            # sin permisos: se cae al comportamiento viejo
    DIR_DATOS = _AQUI


def _migrar_legacy(nombre, destino):
    """Instalaciones viejas guardaban los datos junto al programa. Si aparece
    ese archivo y todavia no hay uno nuevo, se copia (no se mueve: si algo sale
    mal, el original sigue donde estaba). Se hace una sola vez."""
    viejo = os.path.join(_AQUI, nombre)
    if destino == viejo or os.path.exists(destino) or not os.path.isfile(viejo):
        return
    try:
        import shutil
        shutil.copy2(viejo, destino)
    except OSError:
        pass


def _cargar_dotenv():
    # El .env de la carpeta de datos manda: es donde el panel guarda las claves.
    for ruta in (os.path.join(DIR_DATOS, ".env"),
                 os.path.join(_AQUI, ".env"), os.path.join(os.getcwd(), ".env")):
        if os.path.isfile(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    for ln in f:
                        ln = ln.strip()
                        if ln and not ln.startswith("#") and "=" in ln:
                            k, v = ln.split("=", 1)
                            os.environ.setdefault(k.strip(),
                                                  v.strip().strip('"').strip("'"))
            except OSError:
                pass


_cargar_dotenv()


def env(k, d=""):
    return os.environ.get(k, d)


def env_f(k, d):
    try:
        return float(os.environ.get(k, d))
    except (TypeError, ValueError):
        return float(d)


def env_b(k, d=False):
    return os.environ.get(k, "1" if d else "0").strip().lower() in (
        "1", "true", "yes", "si", "sí", "on")


# --- LLM (asistente multi-proveedor, BYOK) ---
# Proveedor recomendado: Claude (mejor razonamiento sobre los numeros del negocio).
# El usuario puede elegir otro pegando su clave en Config.
MODEL_OPUS = env("MODEL_OPUS", "claude-opus-4-8")
MODEL_SONNET = env("MODEL_SONNET", "claude-sonnet-4-6")
MODEL_HAIKU = env("MODEL_HAIKU", "claude-haiku-4-5-20251001")

# UN SOLO lugar donde vive la lista de proveedores de IA. Agregar uno nuevo es
# agregar una entrada aca: la whitelist del .env, el endpoint de configuracion,
# el selector del panel y el listado de modelos se derivan todos de esta tabla.
# Antes la lista estaba repetida en cuatro archivos y agregar un proveedor
# obligaba a acordarse de los cuatro.
#
# Como se consulta la lista de modelos de cada uno (para el boton "Actualizar
# modelos") vive en data/modelos_ia.py: aca va la CONFIGURACION del proveedor,
# no el formato de su API.
PROVEEDORES_IA = (
    {"codigo": "claude", "nombre": "Claude (Anthropic)",
     "clave_env": "ANTHROPIC_API_KEY", "modelo_env": "ANTHROPIC_MODEL",
     "modelo_default": MODEL_OPUS},
    {"codigo": "openai", "nombre": "OpenAI (ChatGPT)",
     "clave_env": "OPENAI_API_KEY", "modelo_env": "OPENAI_MODEL",
     "modelo_default": "gpt-4o-mini"},
    {"codigo": "gemini", "nombre": "Google Gemini",
     "clave_env": "GEMINI_API_KEY", "modelo_env": "GEMINI_MODEL",
     "modelo_default": "gemini-2.0-flash"},
    {"codigo": "grok", "nombre": "Grok (xAI)",
     "clave_env": "GROK_API_KEY", "modelo_env": "GROK_MODEL",
     "modelo_default": "grok-2-latest"},
    {"codigo": "deepseek", "nombre": "DeepSeek",
     "clave_env": "DEEPSEEK_API_KEY", "modelo_env": "DEEPSEEK_MODEL",
     "modelo_default": "deepseek-chat"},
)

_POR_CODIGO = {p["codigo"]: p for p in PROVEEDORES_IA}


def proveedor_ia(codigo):
    """Ficha del proveedor (o None si el codigo no existe)."""
    return _POR_CODIGO.get((codigo or "").strip().lower())


def clave_ia(codigo):
    """Clave BYOK del proveedor.

    Sale de la global del modulo (config.ANTHROPIC_API_KEY y companía), que es
    como la lee el resto del sistema y lo que los tests pisan para forzar modo
    offline. _refrescar_globals() la mantiene al dia con el .env."""
    p = proveedor_ia(codigo)
    return (globals().get(p["clave_env"]) or "").strip() if p else ""


def modelo_ia(codigo):
    """Modelo elegido para ese proveedor, o su default si el usuario no eligio."""
    p = proveedor_ia(codigo)
    if not p:
        return ""
    return (globals().get(p["modelo_env"]) or "").strip() or p["modelo_default"]


def ia_provider_activo():
    """Devuelve (proveedor, clave, modelo) del proveedor elegido si tiene clave;
    si el elegido no tiene clave, cae al primero que si la tenga. (None, "", "")
    si no hay ninguna clave -> el asistente responde offline (glosario)."""
    elegido = (IA_PROVIDER or "claude").strip().lower()
    orden = [elegido] + [p["codigo"] for p in PROVEEDORES_IA if p["codigo"] != elegido]
    for prov in orden:
        clave = clave_ia(prov)
        if clave:
            return prov, clave, modelo_ia(prov)
    return None, "", ""

# --- Datos de mercado ---
# (las globales de IA se definen abajo, en _refrescar_globals)
KEEPA_API_KEY = env("KEEPA_API_KEY")
KEEPA_DOMAIN = int(env("KEEPA_DOMAIN", "1"))           # 1 = amazon.com (US)
# Jungle Scout API (BYOK): a diferencia de Helium 10 (solo CSV), SI tiene API.
# Da volumen de busqueda real + ventas por ASIN. Requiere DOS valores: el
# nombre de la clave y la clave (el auth es "Key_Name:API_Key").
JUNGLE_SCOUT_API_KEY = env("JUNGLE_SCOUT_API_KEY")
JUNGLE_SCOUT_KEY_NAME = env("JUNGLE_SCOUT_KEY_NAME")
JUNGLE_SCOUT_MARKETPLACE = env("JUNGLE_SCOUT_MARKETPLACE", "us")
CEREBRO_CSV_DIR = env("CEREBRO_CSV_DIR", os.path.join(DIR_DATOS, "cerebro_exports"))
USAR_CEREBRO = env_b("USAR_CEREBRO", True)
MARKETPLACE = env("CEREBRO_MARKETPLACE", "US")

# --- DB ---
DB_PATH = env("DB_PATH", os.path.join(DIR_DATOS, "fba.db"))
_migrar_legacy("fba.db", DB_PATH)

# --- Email / alertas ---
ALERT_TO = env("ALERT_TO", "vieraschiavi@gmail.com")
SMTP_HOST = env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER")
SMTP_PASS = env("SMTP_PASS")

# --- Pricing ---
REFERRAL_PCT = env_f("REFERRAL_PCT", 15)               # comision Amazon %
ACOS_PCT = env_f("ACOS_PCT", 10)                       # publicidad %
TARGET_MARGIN = env_f("TARGET_MARGIN", 25)             # margen objetivo %
FBA_FEE_DEFAULT = env_f("FBA_FEE_DEFAULT", 3.65)

# --- Semaforo de margen ---
UMBRAL_VERDE = env_f("UMBRAL_VERDE", 25)
UMBRAL_AMARILLO = env_f("UMBRAL_AMARILLO", 12)

# --- Seguimiento ---
RECORDATORIO_DIAS = int(env("RECORDATORIO_DIAS", "3"))

# --- Whitelist del bot ---
WHITELIST_BOT = ["envio", "tiempo_entrega", "garantia", "estado_pedido", "caracteristicas"]


def _refrescar_globals():
    """Recalcula las globales de conexion desde el entorno.

    Existen como globales (config.ANTHROPIC_API_KEY y companía) porque medio
    sistema las lee asi: agents/exito.py, poa.py, traductor.py, recomendador.py,
    listing.py, customer_bot.py, test_conexiones.py y el panel legacy.
    El problema era que se calculaban UNA vez al importar el modulo: guardar una
    clave desde el panel actualizaba el .env y os.environ, pero NO estas
    globales, asi que el programa seguia creyendose sin clave hasta que lo
    reiniciabas -- pegabas tu clave de Claude, tocabas "Probar conexion" y te
    decia que no habia clave. Ahora guardar_env() llama aca y todo toma efecto
    en el momento.
    """
    g = globals()
    g["IA_PROVIDER"] = (env("IA_PROVIDER", "claude") or "claude").strip().lower()
    for p in PROVEEDORES_IA:
        g[p["clave_env"]] = env(p["clave_env"])
        # Del ENTORNO, no de modelo_ia(): esa lee justamente esta global, asi
        # que derivarla de si misma dejaba el valor viejo pegado para siempre.
        g[p["modelo_env"]] = env(p["modelo_env"]).strip() or p["modelo_default"]
    for k in ("KEEPA_API_KEY", "JUNGLE_SCOUT_API_KEY", "JUNGLE_SCOUT_KEY_NAME",
              "SMTP_USER", "SMTP_PASS"):
        g[k] = env(k)
    g["ALERT_TO"] = env("ALERT_TO", "vieraschiavi@gmail.com")
    g["CEREBRO_CSV_DIR"] = env("CEREBRO_CSV_DIR",
                               os.path.join(DIR_DATOS, "cerebro_exports"))


_refrescar_globals()


def estado_config():
    """Resumen para el dashboard: que esta conectado y que esta en modo offline.
    NUNCA incluye el valor de una clave (se expone por /health)."""
    prov, clave, modelo = ia_provider_activo()
    p = proveedor_ia(prov)
    return {
        "llm": f"{p['nombre'] if p else prov} ({modelo})" if prov else "offline (glosario)",
        "ia_provider": IA_PROVIDER,
        "keepa": "conectado" if KEEPA_API_KEY else "sin clave",
        "jungle_scout": "conectado" if (JUNGLE_SCOUT_API_KEY and JUNGLE_SCOUT_KEY_NAME) else "sin clave",
        "cerebro_dir": CEREBRO_CSV_DIR,
        "email": "SMTP real" if (SMTP_USER and SMTP_PASS) else "dry-run (no envia)",
        "alert_to": ALERT_TO,
        "marketplace": MARKETPLACE,
    }


# --------------------------------------------------------------------------- #
# Guardado seguro de claves (.env) — usado por la pestana Config del panel.
# --------------------------------------------------------------------------- #
ENV_PATH = os.path.join(DIR_DATOS, ".env")
_migrar_legacy(".env", ENV_PATH)

# Claves que el panel puede guardar. Nada fuera de esta lista se escribe.
# Las de IA (clave + modelo elegido de cada proveedor) salen de PROVEEDORES_IA
# para que agregar un proveedor no obligue a acordarse de tocar tambien aca.
CLAVES_IA = tuple(v for p in PROVEEDORES_IA for v in (p["clave_env"], p["modelo_env"]))
CLAVES_GUARDABLES = CLAVES_IA + (
    "IA_PROVIDER", "KEEPA_API_KEY", "JUNGLE_SCOUT_API_KEY",
    "JUNGLE_SCOUT_KEY_NAME", "SMTP_USER",
    "SMTP_PASS", "ALERT_TO", "CEREBRO_CSV_DIR")

# Las claves de IA son SECRETAS (se muestran enmascaradas); el modelo elegido
# no lo es -- es un nombre publico tipo "gpt-4o-mini" y el panel necesita
# mostrarlo tal cual para que el selector arranque en el valor correcto.
CLAVES_SECRETAS = tuple(k for k in CLAVES_GUARDABLES
                        if k.endswith(("_API_KEY", "_KEY_NAME")) or k == "SMTP_PASS")


def mask(valor: str) -> str:
    """Version mostrable de un secreto: solo largo + ultimos 4 caracteres."""
    v = (valor or "").strip()
    if not v:
        return "(vacia)"
    if len(v) <= 6:
        return "*" * len(v)
    return "*" * (len(v) - 4) + v[-4:]


def guardar_env(**pares) -> dict:
    """
    Actualiza/agrega claves en .env de forma atomica, preservando el resto del
    archivo (comentarios incluidos). Solo acepta CLAVES_GUARDABLES. Aplica
    permisos 600 y refresca os.environ para que rija sin reiniciar.
    Nunca registra ni devuelve el valor de la clave.
    """
    pares = {k: (v or "").strip() for k, v in pares.items()
             if k in CLAVES_GUARDABLES and (v or "").strip()}
    if not pares:
        return {"ok": False, "mensaje": "Nada para guardar."}
    lineas, vistas = [], set()
    if os.path.isfile(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for ln in f.read().splitlines():
                cuerpo = ln.strip()
                if cuerpo and not cuerpo.startswith("#") and "=" in cuerpo:
                    k = cuerpo.split("=", 1)[0].strip()
                    if k in pares:
                        lineas.append(f"{k}={pares[k]}")
                        vistas.add(k)
                        continue
                lineas.append(ln)
    for k, v in pares.items():
        if k not in vistas:
            lineas.append(f"{k}={v}")
    tmp = ENV_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas).rstrip("\n") + "\n")
    try:
        os.chmod(tmp, 0o600)                 # solo el dueno lee/escribe (POSIX)
    except OSError:
        pass                                 # Windows: lo protege el perfil de usuario
    os.replace(tmp, ENV_PATH)
    for k, v in pares.items():
        os.environ[k] = v
    _refrescar_globals()                     # rige sin reiniciar el programa
    return {"ok": True, "guardadas": sorted(pares.keys()),
            "mensaje": f"{len(pares)} clave(s) guardada(s) en .env."}
