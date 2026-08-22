# CLAUDE.md — MV FBA IA (Amazon-Fba)

Guía para Claude Code al trabajar en este repo. Leela antes de tocar código.

## Qué es

**MV FBA IA** es un cockpit end-to-end para operar un negocio real de Amazon FBA:
investigación de nicho (keywords vía CSV de Helium 10 Cerebro, precio/BSR vía Keepa,
Jungle Scout BYOK), pricing (landed cost → precio → margen → ROI → semáforo),
portafolio de productos con análisis financiero, proyección de caja con techo de
demanda, analítica de ventas, bot de atención con whitelist (Amazon prohíbe texto
libre), asistente con IA multi-proveedor (Claude/OpenAI/Gemini, BYOK) y una API REST
que alimenta automatizaciones de n8n. Corre como app de escritorio (Windows, con
runtime Python embebido + Electron/pywebview), PWA Android y app Android nativa, con
landing propia deployada en Vercel. Todo en español; el copy de listing sale en inglés
(mercado Amazon US). **Sin datos inventados**: si falta un CSV o una API key, el
sistema lo dice en vez de simular un resultado.

## Stack

- **Python 3.11** — motor y backend:
  - `app.py` : API **FastAPI** (puente con n8n, sirve también el panel web) —
    `uvicorn app:app --host 0.0.0.0 --port 8000`.
  - `api_rutas.py` : rutas adicionales de la API.
  - `config.py` : configuración central + guardado seguro de claves (`.env`).
  - `desktop.py` : envoltorio de escritorio nativo (pywebview sobre WebView2) que
    levanta el server local y muestra `frontend/dist` en una ventana propia.
  - `dashboard_app.py` : panel **Streamlit** legado (9 pestañas) — `styles.py` define
    el sistema de diseño (cockpit BI navy `#1e3a8a`).
  - `agents/` : lógica de negocio (market_intel, pricing, productos, portafolio,
    capital_planner, analytics, customer_bot, asistente, listing, exito, ganancias,
    dedicacion, creativos, publicador, recomendador, tutorial, glosario, poa,
    inventario, traductor).
  - `core/` : `db.py` (SQLite, esquema + migraciones), `i18n.py`, `licencia.py`,
    `notify.py` (alertas email, dry-run sin SMTP), `prefs.py`, `demo_seed.py`.
  - `data/` : conectores externos — `cerebro.py` (CSV Helium 10), `keepa.py` (API),
    `jungle_scout.py` (API BYOK), `mercado.py`, `motor_propio.py`, `demanda_nativa.py`.
  - Deps clave (`requirements.txt`): streamlit, fastapi, uvicorn, httpx, anthropic,
    pillow, pywebview, pandas, python-multipart. `requirements-desktop.txt` es el
    subconjunto sin streamlit/altair para el bundle de escritorio.
- **Node.js / Vercel** — `api/*.js`: funciones serverless (checkout, licencia,
  créditos IA, email, PayPal, reseñas, cron de recordatorio) sin framework ni deps
  propias; `scripts/vercel-build.sh` copia `mobile/` dentro de `landing/app/` para el
  deploy. No hay `package.json` en la raíz del repo para esta parte.
- **frontend/** — subproyecto aparte: **React 18 + Vite + TypeScript + Tailwind 4**
  (recharts, zustand, react-router-dom). Es el panel SaaS que se compila
  (`frontend/dist`) y se empaqueta dentro del instalador de Windows y de
  `desktop.py`; no corre en el deploy web de Vercel (ese usa `mobile/`).
- **mobile/** : PWA responsive (HTML/CSS/JS vanilla) — es lo que se copia a
  `landing/app/` para la demo pública y lo que consume `android/` (WebView nativo).
- **Tests**: `test/test_api_local.py` — suite **pytest** que compara cada endpoint de
  la API contra la llamada directa a la función Python equivalente (usa una DB SQLite
  temporal). `test_conexiones.py` en la raíz es un verificador de conexiones reales
  (Keepa, Claude, SMTP, CSV de Cerebro) con salida verde/rojo, no una suite de tests.

## Comandos

| Objetivo | Comando |
|---|---|
| Instalar deps Python | `pip install -r requirements.txt` |
| Instalar deps de test | `pip install -r requirements-test.txt` |
| Correr la API + panel | `python -m uvicorn app:app --host 0.0.0.0 --port 8000` (o `API.bat` / `INICIAR.bat` en Windows) |
| Correr el panel Streamlit legado | `streamlit run dashboard_app.py` (o `LEGACY_STREAMLIT.bat`) |
| Verificar conexiones (Keepa/Claude/SMTP/CSV) | `python test_conexiones.py` |
| Tests (Python) | `python -m pytest test/test_api_local.py test/test_activar_owner.py -q` |
| Un test puntual | `python -m pytest test/test_api_local.py::test_legacy_health -v` |
| Tests (JS: motor portado + seguridad + créditos) | `node test/verificar_nucleo.js && node test/verificar_escapar.js && node test/verificar_seguridad.mjs && node test/verificar_creditosia.mjs && node test/verificar_sin_innerhtml_crudo.mjs && node test/verificar_i18n_landing.mjs && node test/verificar_demo_sin_motor.mjs && node test/verificar_lanzadores.mjs && node test/verificar_sw_precache.mjs && node test/verificar_instalador.mjs && node test/verificar_licencia_dueno.mjs && node test/verificar_owner_github.mjs && node test/verificar_keystore_android.mjs && node test/verificar_licencia_secreto.mjs && node test/verificar_descarga_limite.mjs && node test/verificar_descarga_plan.mjs && node test/verificar_limite_endpoints_pago.mjs && node test/verificar_escapar_email_demo.mjs && node test/verificar_ventas_admin.mjs` (sin `npm install`, solo Node >= 18) |
| Instalar deps del frontend | `cd frontend && npm install` |
| Frontend en desarrollo | `cd frontend && npm run dev` |
| Build del frontend (para desktop/instalador) | `cd frontend && npm run build` |
| App de escritorio (requiere `frontend/dist` compilado) | `python desktop.py` |
| Pipeline CLI Cerebro → score → listing | `python demo_pipeline.py` |

> No hay linter/formatter configurado en el repo (ni Python ni JS). No introduzcas uno
> sin que te lo pidan.
> Los `.bat` (`INICIAR.bat`, `API.bat`, `CONECTAR.bat`, `DIAGNOSTICO.bat`,
> `LEGACY_STREAMLIT.bat`, `APP_ESCRITORIO.bat`), el instalador de `installer/` (Inno
> Setup) y el workflow de Android/iOS son para Windows/CI — no corren en este entorno
> Linux.

## Estructura

```
├── app.py               API FastAPI (puente n8n + panel) — entrypoint real
├── api_rutas.py          Rutas adicionales de la API
├── config.py             Configuración central + guardado seguro de claves (.env)
├── desktop.py            Envoltorio de escritorio (pywebview) sobre frontend/dist
├── dashboard_app.py       Panel Streamlit legado (9 pestañas)
├── styles.py             Sistema de diseño (cockpit BI navy/verde)
├── test_conexiones.py     Verificador de conexiones reales (no es suite de tests)
├── demo_pipeline.py       Pipeline CLI: Cerebro → score → listing
├── generar_pitch.py       Pitch HTML para inversores
├── agents/               Lógica de negocio (pricing, portafolio, market_intel, bot...)
├── core/                 db.py, i18n.py, licencia.py, notify.py, prefs.py
├── data/                 Conectores: cerebro.py, keepa.py, jungle_scout.py, mercado.py
├── api/                  Funciones serverless Node (Vercel): pagos, licencias, IA
├── frontend/             Panel SaaS React+Vite+TS (se compila a frontend/dist)
├── mobile/               PWA Android (HTML/CSS/JS vanilla) — demo web y APK
├── android/               App Android nativa (Gradle/Java, WebView)
├── ios/                  Proyecto iOS (build de Simulador únicamente, sin firma)
├── installer/             Instalador Windows (Inno Setup) — no corre en Linux
├── n8n/                  Workflows n8n (research, mensajes, alertas de venta)
├── landing/              Landing web trilingüe + demo (deploy Vercel)
├── scripts/              vercel-build.sh (copia mobile/ a landing/app/)
└── test/                 test_api_local.py (pytest) + fixtures de referencia
```

## Flujo de trabajo

1. **Plan** — ante un cambio no trivial, planificá primero (`/plan`). Solo lectura
   hasta aprobar.
2. **Cambio** — editá el mínimo necesario. Respetá la separación motor (`agents/`,
   `core/`, `data/`) vs. API (`app.py`, `api_rutas.py`) vs. UI (`dashboard_app.py`,
   `frontend/`, `mobile/`).
3. **Test** — `python -m pytest test/test_api_local.py test/test_activar_owner.py -q` (`/test`). No declares
   éxito sin correrlos.
4. **Ship** — `/ship`: test → commit descriptivo → push → PR draft.

## Convenciones

- **Sin datos inventados**: si falta el CSV de Cerebro o una API key (Keepa, Jungle
  Scout), el sistema debe avisarlo explícitamente, nunca simular un resultado.
- **El bot de atención no responde texto libre**: solo FAQs de una whitelist
  (`agents/customer_bot.py`) — Amazon prohíbe auto-respuesta de texto libre.
- **La proyección de caja tiene techo de demanda** (`agents/capital_planner.py`): sin
  techo la proyección "explota" y miente; no lo quites sin entender por qué existe.
- **El score de nicho mide ganabilidad, no margen** (`agents/market_intel.py`,
  fórmula documentada 0.35/0.30/0.35) — el margen lo decide el pricing.
- **Secretos por entorno**: API keys (Keepa, Jungle Scout, Anthropic/OpenAI/Gemini,
  SMTP) van en `.env` (ver `.env.example`), nunca hardcodeadas ni commiteadas.
  `config.py` maneja el guardado seguro.
- **Español rioplatense** en código, comentarios y textos de usuario; el copy de
  listing generado para Amazon es en inglés (mercado US) a propósito.

## Do / Don't

**Do**
- Correr `python -m pytest test/test_api_local.py test/test_activar_owner.py -q` antes de cerrar cualquier
  cambio en `agents/`, `core/`, `data/` o `app.py`/`api_rutas.py`.
- Usar `git status` / `git diff` para revisar antes de commitear.
- Preferir editar la lógica en `agents/`/`core`/`data` y consumirla desde `app.py`,
  `dashboard_app.py` o `frontend/`.

**Don't**
- No hardcodees ni commitees `.env`, claves de Keepa/Jungle Scout/Anthropic/SMTP,
  `src/clave-embebida*`, `*.keystore` ni tokens de pago (MercadoPago/PayPal).
- No corras los `.bat`, el instalador de `installer/` (Inno Setup) ni los workflows
  de Android/iOS en este entorno Linux.
- No agregues datos de productos/clientes reales al modo DEMO: es 100% sintético.
- No uses `git push --force` ni `rm -rf`.

## Contexto / Compact

- Empezá por este archivo y el `README.md` (tiene el detalle de cada endpoint y
  módulo) y `PENDIENTES.md` (estado real de bloqueadores de infraestructura).
- Para entender un flujo, seguí `app.py` → el `agents/*` correspondiente → el
  conector en `data/*` si aplica.
- Si el contexto se llena, compactá reteniendo: la tabla de comandos, las reglas de
  dominio (sin datos inventados, techo de demanda, whitelist del bot) y qué archivos
  tocaste.
