#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py — Configuracion central del sistema FBA. Lee .env (sin pisar el entorno).
Sin claves -> modo offline / dry-run (no inventa datos, no envia mails).
"""
import os

_AQUI = os.path.dirname(os.path.abspath(__file__))


def _cargar_dotenv():
    for ruta in (os.path.join(_AQUI, ".env"), os.path.join(os.getcwd(), ".env")):
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
# El usuario puede elegir OpenAI (ChatGPT) o Gemini pegando su clave en Config.
IA_PROVIDER = (env("IA_PROVIDER", "claude") or "claude").strip().lower()
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
MODEL_OPUS = env("MODEL_OPUS", "claude-opus-4-8")
MODEL_SONNET = env("MODEL_SONNET", "claude-sonnet-4-6")
MODEL_HAIKU = env("MODEL_HAIKU", "claude-haiku-4-5-20251001")
OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_API_KEY = env("GEMINI_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.0-flash")


def ia_provider_activo():
    """Devuelve (proveedor, clave, modelo) del proveedor elegido si tiene clave;
    si el elegido no tiene clave, cae al primero que si la tenga. (None, "", "")
    si no hay ninguna clave -> el asistente responde offline (glosario)."""
    disp = {
        "claude": (ANTHROPIC_API_KEY, MODEL_OPUS),
        "openai": (OPENAI_API_KEY, OPENAI_MODEL),
        "gemini": (GEMINI_API_KEY, GEMINI_MODEL),
    }
    orden = [IA_PROVIDER] + [p for p in ("claude", "openai", "gemini") if p != IA_PROVIDER]
    for prov in orden:
        clave, modelo = disp.get(prov, ("", ""))
        if (clave or "").strip():
            return prov, clave, modelo
    return None, "", ""

# --- Datos de mercado ---
KEEPA_API_KEY = env("KEEPA_API_KEY")
KEEPA_DOMAIN = int(env("KEEPA_DOMAIN", "1"))           # 1 = amazon.com (US)
CEREBRO_CSV_DIR = env("CEREBRO_CSV_DIR", os.path.join(_AQUI, "data", "cerebro_exports"))
USAR_CEREBRO = env_b("USAR_CEREBRO", True)
MARKETPLACE = env("CEREBRO_MARKETPLACE", "US")

# --- DB ---
DB_PATH = env("DB_PATH", os.path.join(_AQUI, "fba.db"))

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


def estado_config():
    """Resumen para el dashboard: que esta conectado y que esta en modo offline.
    NUNCA incluye el valor de una clave (se expone por /health)."""
    prov, clave, modelo = ia_provider_activo()
    _nom = {"claude": "Claude", "openai": "OpenAI (ChatGPT)", "gemini": "Gemini"}
    return {
        "llm": f"{_nom.get(prov, prov)} ({modelo})" if prov else "offline (glosario)",
        "ia_provider": IA_PROVIDER,
        "keepa": "conectado" if KEEPA_API_KEY else "sin clave",
        "cerebro_dir": CEREBRO_CSV_DIR,
        "email": "SMTP real" if (SMTP_USER and SMTP_PASS) else "dry-run (no envia)",
        "alert_to": ALERT_TO,
        "marketplace": MARKETPLACE,
    }


# --------------------------------------------------------------------------- #
# Guardado seguro de claves (.env) — usado por la pestana Config del panel.
# --------------------------------------------------------------------------- #
ENV_PATH = os.path.join(_AQUI, ".env")

# Claves que el panel puede guardar. Nada fuera de esta lista se escribe.
CLAVES_GUARDABLES = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                     "IA_PROVIDER", "KEEPA_API_KEY", "SMTP_USER",
                     "SMTP_PASS", "ALERT_TO", "CEREBRO_CSV_DIR")


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
    return {"ok": True, "guardadas": sorted(pares.keys()),
            "mensaje": f"{len(pares)} clave(s) guardada(s) en .env."}
