# Sistema FBA — completo, end to end

Reconstrucción **autónoma y validada** del sistema FBA: investigación de nicho (Cerebro),
pricing, proyección de caja, ventas/analítica, bot de atención, alertas por email, API y
n8n. Corre de cero, sin depender de la PC vieja ni del zip original. Todo en español;
copy del listing en inglés (mercado Amazon US); esquema navy `#1e3a8a`; sin datos inventados.

## Arrancar (Windows, doble clic)
**`INICIAR.bat`** → detecta Python (Anaconda), instala dependencias la primera vez,
crea la base, levanta la API y abre el panel en `http://localhost:8501`.

La primera vez tarda (instala Streamlit etc.). Después abre en segundos.

## Qué hace cada pieza
| Archivo | Rol |
|---|---|
| `dashboard_app.py` | Panel Streamlit: Investigación, Pricing, Caja, Ventas/Analítica, Alertas, Config. |
| `data/cerebro.py` | Keywords desde el CSV de Helium 10 Cerebro (Export Data) + scoring de oportunidad. |
| `data/keepa.py` | Fuente **programática** real: precio + BSR vía Keepa API (sin clave → estado vacío). |
| `agents/market_intel.py` | Score de nicho (fórmula documentada 0.35/0.30/0.35) + veredicto. |
| `agents/listing.py` | Título + 5 bullets + descripción + banner (offline o Claude si hay API key). |
| `agents/pricing.py` | Landed cost → precio → margen → ROI → semáforo; entra 5% bajo el líder si aguanta. |
| `agents/capital_planner.py` | Proyección de caja con lead time, DD+7, devoluciones y **techo de demanda**. |
| `agents/analytics.py` | Registra ventas, KPIs y mix por producto/país/segmento. |
| `agents/customer_bot.py` | Atención con whitelist; auto-responde solo FAQs, el resto a aprobación. |
| `core/db.py` | SQLite (10 tablas del esquema documentado). |
| `core/notify.py` | Alertas por email; sin SMTP → dry-run (registra, no envía). |
| `app.py` | API FastAPI (`/health`, `/webhook/message`, `/webhook/sale`, `/run/research`, `/dashboard`). |
| `n8n/*.json` | 3 workflows: research diario 09:00, mensajes de cliente, alertas de venta. |
| `INICIAR.bat` / `API.bat` | Autorun del panel / de la API. |

## Modo DEMO vs producción
- El panel arranca en **Modo DEMO** (toggle en el sidebar): datos `[DEMO]` ilustrativos
  para ver el flujo sin gastar nada.
- **Producción**: apagás DEMO. El sistema **no inventa datos**: sin CSV de Cerebro ni
  Keepa, te avisa qué conectar.

## Conectar datos reales (`.env`)
Copiá `.env.example` a `.env` y completá lo que tengas. Guía paso a paso en
**`CONEXIONES.md`**. Para chequear qué quedó conectado, doble clic en **`CONECTAR.bat`**
(valida Keepa, Anthropic, SMTP y Cerebro y reporta verde/rojo), o usá el botón
**Probar conexiones** en la pestaña Config del panel.
- `KEEPA_API_KEY` → fuente programática de precio/BSR (Keepa, ~19 EUR/mes, **sin free trial**).
- `ANTHROPIC_API_KEY` → el listing lo redacta Claude (si no, modo offline).
- `SMTP_USER` / `SMTP_PASS` (App Password de Gmail) → alertas reales a `ALERT_TO`.
- Keywords: exportá la tabla de Cerebro (**Export Data**) y dejá el `.csv` en
  `data/cerebro_exports/` (o subilo desde la pestaña Investigación).

## Automatización (n8n)
1. Levantá la API (`API.bat` o la deja andando `INICIAR.bat`).
2. Importá los 3 JSON de `n8n/` en n8n y apuntá la URL base a `http://localhost:8000`.

## Verdades que el sistema respeta (sin maquillaje)
- **Helium 10 no tiene API en Platinum**: la fuente de keywords es el CSV de Cerebro.
  Keepa es la alternativa programática.
- **El bot no auto-responde texto libre** (lo prohíbe Amazon): solo FAQs de la whitelist;
  el resto queda para tu aprobación.
- **La proyección de caja tiene techo de demanda**: sin él, el sueldo "explota" y miente.
  Con techo, el sueldo se estabiliza en meseta (~techo × neto). Reciclar capital (el landed
  repone stock, el neto se retira) da ingreso sostenido; retirar todo lo agota.
- **El score mide ganabilidad, no margen.** El margen lo decide el pricing + el costo real
  del proveedor. Nada reemplaza la **orden de prueba** (USD 1.000–2.000) antes de escalar.

## Validación
Todo se validó corriendo, no solo compilando: `py_compile` de los 15 módulos, dashboard
**headless con AppTest** (Streamlit 1.45.1, los 6 tabs + clicks), API con TestClient
(5 endpoints 200), pipeline CLI end-to-end y JSON de n8n.

## Nota de continuidad
En sesiones previas se entregaron módulos Cerebro con otros nombres (`data/helium10.py`,
`agents/cerebro_intel.py`). Este sistema es **autónomo** y no los necesita; si recuperás
aquello, reconciliá para no tener dos motores Cerebro en paralelo.
