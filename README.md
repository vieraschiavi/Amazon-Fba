# MV Amazon FBA IA — cockpit inteligente de gestión Amazon FBA

Sistema **end to end** para operar un negocio Amazon FBA: investigación de nicho
(Cerebro), pricing, **portafolio de productos con análisis financiero por producto**,
proyección de caja, ventas/analítica, bot de atención, alertas por email, API REST y
automatización con n8n. Todo en español; copy del listing en inglés (mercado Amazon US);
esquema navy `#1e3a8a`; **sin datos inventados**.

## Arrancar (Windows, doble clic)

**`INICIAR.bat`** → detecta Python (Anaconda o instalación normal), instala las
dependencias la primera vez, crea la base de datos, **levanta la API en segundo plano**
y abre el panel en `http://localhost:8501`. La primera vez tarda (instala Streamlit,
FastAPI, etc.); después abre en segundos.

| Autorun | Qué hace |
|---|---|
| `INICIAR.bat` | Todo el sistema: panel + API + base, con un doble clic. |
| `API.bat` | Solo la API (`http://localhost:8000`), para n8n. |
| `CONECTAR.bat` | Crea `.env` desde la plantilla y valida cada conexión (verde/rojo). |
| `DIAGNOSTICO.bat` | Chequeo rápido si algo no arranca. |

## Estructura del proyecto

```
Amazon-Fba/
├── INICIAR.bat / API.bat / CONECTAR.bat / DIAGNOSTICO.bat
├── dashboard_app.py      Panel Streamlit (9 pestañas)
├── app.py                API FastAPI (puente con n8n)
├── config.py             Configuración central + guardado seguro de claves (.env)
├── styles.py             Sistema de diseño (cockpit BI navy/verde)
├── test_conexiones.py    Verificador de conexiones (Keepa, Claude, SMTP, CSV)
├── demo_pipeline.py      Pipeline CLI: Cerebro → score → listing
├── generar_pitch.py      Pitch HTML para inversores (mismo motor que el panel)
├── core/
│   ├── db.py             SQLite (esquema + migraciones automáticas)
│   └── notify.py         Alertas por email (sin SMTP → dry-run)
├── agents/
│   ├── market_intel.py   Score de nicho (fórmula documentada 0.35/0.30/0.35)
│   ├── listing.py        Título + 5 bullets + descripción (offline o Claude)
│   ├── pricing.py        Landed cost → precio → margen → ROI → semáforo
│   ├── productos.py      PORTAFOLIO: CRUD + análisis financiero por producto
│   ├── capital_planner.py Proyección de caja con techo de demanda
│   ├── portafolio.py     Planificación: interés compuesto + plan de productos
│   ├── analytics.py      Ventas, KPIs y mix por producto/país/segmento
│   └── customer_bot.py   Atención con whitelist (Amazon prohíbe texto libre)
├── data/
│   ├── cerebro.py        Keywords desde CSV de Helium 10 Cerebro + scoring
│   ├── keepa.py          Precio + BSR vía Keepa API (sin clave → estado vacío)
│   └── cerebro_exports/  Dejá acá tus CSV de Cerebro
└── n8n/                  3 workflows: research diario, mensajes, alertas de venta
```

## El panel (11 pestañas)

1. **Investigación** — keyword o CSV de Cerebro → score de nicho → veredicto → listing.
2. **Pricing** — costos → precio sugerido, margen, ROI, semáforo. Botón
   **Guardar en portafolio** para pasar del cálculo a la gestión.
3. **Portafolio** — el corazón de la gestión: todos tus productos persistidos con
   **análisis financiero de cada uno** (unit economics, capital en pipeline, sueldo
   en meseta proyectado, proyección de caja a 12 meses y **ventas reales** cruzadas
   por ASIN). Consolidado del negocio + export CSV.
4. **Caja** — proyección realista con lead time, DD+7, devoluciones y techo de demanda.
5. **Ventas** — registro de ventas y KPIs (facturación, neto, margen, mix).
6. **Inversores** — escenarios con capital externo y pitch HTML descargable.
7. **Plan** — cuántos productos necesitás para tu objetivo de ingreso + reinversión compuesta.
8. **Alertas** — outbox de emails (dry-run sin SMTP).
9. **Config** — estado de conexiones, prueba en vivo y **guardado seguro de claves**.
10. **Asistente IA (Claude)** — chat que responde sobre tus métricas, tu portafolio y
    la estrategia FBA, usando tus **datos reales** como contexto. Con `ANTHROPIC_API_KEY`
    responde Claude; sin clave, modo offline desde el glosario (nunca rompe).
11. **Ayuda** — guía de inicio en 3 pasos + **glosario** buscable de FBA y finanzas
    (ROI, BSR, landed cost, techo de demanda, ACoS…).

## Seguridad de las claves (API keys)

- Las claves viven **solo en `.env`** (local), que está en `.gitignore` y **nunca se
  sube al repositorio**. Plantilla: `.env.example`.
- Se cargan desde la pestaña **Config** del panel (campos tipo contraseña): se escriben
  de forma atómica, con permisos restringidos, y **nunca se muestran completas**
  (solo los últimos 4 caracteres).
- El endpoint `/health` y el resto de la API **no exponen ningún valor de clave**.
- Solo una lista blanca de claves puede escribirse desde el panel.

## Conectar datos reales

Guía paso a paso en **`CONEXIONES.md`**. Resumen:
- `KEEPA_API_KEY` → precio/BSR programático (Keepa, ~19 EUR/mes, sin free trial).
- `ANTHROPIC_API_KEY` → el listing lo redacta Claude (sin clave: modo offline).
- `SMTP_USER`/`SMTP_PASS` (App Password de Gmail) → alertas reales a `ALERT_TO`.
- Keywords: exportá la tabla de Cerebro (**Export Data**) y dejá el `.csv` en
  `data/cerebro_exports/` (o subilo desde la pestaña Investigación).

Para verificar: doble clic en **`CONECTAR.bat`** o botón **Probar conexiones** en Config.

## API y automatización (n8n)

La API (`INICIAR.bat` la deja corriendo, o `API.bat`) expone:

| Endpoint | Uso |
|---|---|
| `GET /health` | Estado del sistema (sin claves). |
| `POST /run/research` | Investigación de nicho (n8n la corre a diario 09:00). |
| `POST /webhook/message` | Mensajes de clientes → bot con whitelist. |
| `POST /webhook/sale` | Registrar venta → KPIs + alerta email. |
| `GET /dashboard` | KPIs de ventas. |
| `GET /portfolio` | Consolidado del portafolio (proyectado vs real). |
| `POST /portfolio/producto` | Alta de producto con métricas calculadas. |
| `GET /portfolio/producto/{id}` | Análisis financiero completo de un producto. |
| `POST /assistant` | Asistente IA (Claude) sobre el negocio; offline sin clave. |

Importá los 3 JSON de `n8n/` en n8n y apuntá la URL base a `http://localhost:8000`.

## Modo DEMO vs producción

- El panel arranca en **Modo DEMO** (toggle en el sidebar): datos `[DEMO]`
  ilustrativos para ver el flujo sin gastar nada.
- **Producción**: apagás DEMO. El sistema **no inventa datos**: sin CSV de Cerebro ni
  Keepa te avisa exactamente qué conectar.

## Verdades que el sistema respeta (sin maquillaje)

- **Helium 10 no tiene API en Platinum**: la fuente de keywords es el CSV de Cerebro.
  Keepa es la alternativa programática.
- **El bot no auto-responde texto libre** (lo prohíbe Amazon): solo FAQs de la
  whitelist; el resto queda para tu aprobación.
- **La proyección de caja tiene techo de demanda**: sin él, el sueldo "explota" y
  miente. Con techo, el sueldo se estabiliza en meseta (~techo × neto).
- **El score mide ganabilidad, no margen.** El margen lo decide el pricing + el costo
  real del proveedor. Nada reemplaza la **orden de prueba** (USD 1.000–2.000) antes
  de escalar.

## Validación

Todo se validó **corriendo, no solo compilando**: `py_compile` de los 17 módulos,
dashboard headless con AppTest (las 9 pestañas), API con TestClient (8 endpoints, 200),
pipeline CLI end-to-end, guardado de claves (atómico, permisos, whitelist) y JSON de n8n.
