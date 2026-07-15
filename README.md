# MV FBA IA — cockpit inteligente de gestión Amazon FBA

Sistema **end to end** para operar un negocio Amazon FBA: investigación de nicho
(Cerebro), pricing, **portafolio de productos con análisis financiero por producto**,
proyección de caja, ventas/analítica, bot de atención, alertas por email, API REST y
automatización con n8n. Todo en español; copy del listing en inglés (mercado Amazon US);
esquema navy `#1e3a8a`; **sin datos inventados**.

## 🔗 Enlaces del proyecto

| Recurso | Enlace |
|---|---|
| 🌐 **Web / landing** | https://amazon-fba-seven.vercel.app |
| ▶️ **Demo real (probar la app)** | https://amazon-fba-seven.vercel.app/app |
| 💳 **Gracias / post-pago** (licencia automática) | https://amazon-fba-seven.vercel.app/gracias.html |
| 💻 **Código (GitHub)** | https://github.com/vieraschiavi/Amazon-Fba |

La web se despliega sola en Vercel en cada push a `main`. El dominio es
configuración externa: cuando conectes uno propio, nada del código cambia
(no hay URLs hardcodeadas) — ver [Landing web y dominio propio](#landing-web-landing-y-dominio-propio).

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

### Instalador de Windows (con wizard, para distribuir/vender)

`installer/MV_Amazon_FBA_IA.iss` es un instalador profesional con **Inno Setup**
(el estándar gratuito que usan VS Code, Git for Windows, etc.): asistente con
licencia, accesos directos en Escritorio/Menú Inicio, detección de Python y
desinstalador. Se instala en la carpeta del usuario (sin pedir admin/UAC).

Este proyecto corre en un contenedor Linux y **no puede compilar el `.exe`
final** (Inno Setup solo compila en Windows). El script está completo y listo:
compilarlo es un paso de un clic en Windows — instrucciones en
`installer/COMO_COMPILAR.md`.

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
│   ├── jungle_scout.py   Jungle Scout API (BYOK): productos + keywords (por término y por ASIN) + volumen histórico/estacionalidad + ventas y precio diarios por ASIN + share of voice
│   └── cerebro_exports/  Dejá acá tus CSV de Cerebro
├── n8n/                  3 workflows: research diario, mensajes, alertas de venta
├── installer/            Instalador Windows (Inno Setup) — ver COMO_COMPILAR.md
├── mobile/                UI móvil responsive (PWA) — ver mobile/README.md
└── android/               App Android NATIVA (Gradle/Java, WebView con la UI
                          embebida en el APK) — ver android/README.md
```

## App Android nativa — carpeta `android/`

Proyecto Android **nativo** (Gradle + Java, sin frameworks): la interfaz móvil
viaja **dentro del APK** (~80 KB), con ícono adaptativo de marca, splash navy y
links externos que abren en el navegador. El APK debug compilado es instalable
directo en cualquier Android 7+ ("instalar apps desconocidas"); además,
`.github/workflows/android-apk.yml` lo **recompila automáticamente en GitHub**
en cada push y lo deja descargable en la pestaña Actions. Detalles, compilación
local y camino a Play Store: `android/README.md`.

## UI móvil (PWA) — carpeta `mobile/`

Versión responsive para **gerentes y compradores**: resumen ejecutivo, portafolio,
simulador de ganancias, mercado y el asistente IA, adaptados a pantalla táctil,
instalable en la pantalla de inicio del celular (PWA — sin pasar por ninguna
tienda de apps). Consume la misma API que el panel de escritorio (`app.py`),
que ahora tiene CORS habilitado para esto. Ver `mobile/README.md` para probarla
en 2 minutos.

## Activar la IA del DEMO web (proxy con tu clave, 1 paso)

El demo público (`/app/`) trae el asistente con IA **incluida**: cuando el
visitante no puso su propia clave, la app llama al endpoint `api/ia.js`
(función serverless de Vercel) que responde con Claude usando **tu** clave
guardada **solo** como variable de entorno en Vercel — nunca en el repo ni en
el cliente. Modelo económico (Haiku) + `max_tokens` acotado para cuidar el
presupuesto. Si la clave no está configurada, el endpoint responde 503 y el
demo cae solo al asistente local (nunca se rompe).

Para encenderla (una sola vez, ~30 s):
1. Vercel → tu proyecto → **Settings → Environment Variables**.
2. Agregá `ANTHROPIC_API_KEY` = tu clave `sk-ant-...` (Production + Preview).
3. **Redeploy** (o el próximo push). Listo: el asistente del demo responde con
   IA real. Para apagarla, borrá la variable y redeploy.

En la versión **descargada** (APK/iOS/PC) no hay proxy: cada cliente usa su
propia clave (BYOK) o el asistente local — por eso el `fetch('/api/ia')` falla
en `file://` y cae al fallback, que es lo buscado.

## Cuota de IA del plan "Pro IA" (requiere una base de datos, 1 paso)

El plan "Pro IA" ($34, cobro **único** que extiende 30 días de acceso — no es
una suscripción automática de MercadoPago; se explica por qué en
`api/_cuotaia.js`) necesita contar cuántos tokens gastó cada cliente para no
regalar IA sin límite. Ese conteo vive en una base de datos chica (Vercel KV
o Upstash Redis) que **no viene provisionada por defecto** — sin ella, el
sistema no inventa una cuota: cae al mismo tope genérico que la demo gratis
(ver `api/_almacen.js`).

Para activarla (una sola vez, ~2 min):
1. Vercel → tu proyecto → **Storage → Create Database** → elegí **KV**
   (o conectá **Upstash for Redis** desde el Marketplace de integraciones).
2. Conectala a este proyecto. Vercel agrega solo las variables
   `KV_REST_API_URL` y `KV_REST_API_TOKEN` (Production + Preview).
3. **Redeploy**. Listo: cada pago del plan "Pro IA" activa 30 días de cuota
   mensual (tokens reales de la respuesta de Claude, no una estimación), y el
   cliente elige en **Config → Tu cuota de IA** si prefiere que lo que no usa
   se resetee cada mes ("tope fijo") o se acumule para el mes siguiente
   ("acumular", con un techo de 2x para que no crezca sin límite).

## Pagos con PayPal (opcional, para no perder ventas de extranjeros)

MercadoPago cobra siempre en **pesos uruguayos** (aunque muestre USD), lo cual
puede generar fricción o desconfianza en un comprador de otro país. Por eso
existe un segundo botón "o pagar con PayPal (USD)" en cada plan de la landing
— PayPal cobra en dólares reales, sin conversión para el comprador. Es
**opcional**: si no configurás las variables de abajo, el botón responde
"PayPal no disponible aún" y el resto del sitio sigue funcionando normal con
MercadoPago.

Costo real de PayPal a tener en cuenta: no cobra fee mensual ni de alta, pero
sí ~5.4% + US$0.30 por transacción, más ~3.5% adicional si retirás a pesos en
vez de gastar el saldo en USD (ej. para pagar servicios en dólares) — conviene
sobre todo para no perder la venta, no para maximizar margen en esa venta.

Para activarlo (una sola vez, ~5 min):
1. Creá una cuenta **PayPal Business** (developer.paypal.com si no la tenés).
2. **Developer Dashboard → Apps & Credentials** → creá una app REST.
   Primero probá en **Sandbox** antes de pasar a Live.
3. Vercel → tu proyecto → **Settings → Environment Variables**, agregá:
   - `PAYPAL_CLIENT_ID` y `PAYPAL_CLIENT_SECRET` (de la app creada arriba).
   - `PAYPAL_SANDBOX` = `true` mientras probás (usa `api-m.sandbox.paypal.com`
     y no mueve plata real); quitala o poné cualquier otro valor para pasar a
     producción real (`api-m.paypal.com`).
4. **Redeploy**. Listo: el botón de PayPal queda activo, comparte la misma
   licencia (`api/_licencia.js`), cuota de IA (`api/_cuotaia.js`) y garantía de
   7 días (`api/reembolso.js`) que el flujo de MercadoPago — todo el código
   vive en `api/_paypal.js` y los endpoints que ya conocés (`checkout`,
   `licencia`, `descarga`, `reembolso`) simplemente detectan `proc=paypal`.

## Revocación de licencia al reembolsar

Antes, un reembolso devolvía la plata pero la licencia seguía funcionando
para siempre (limitación documentada a propósito). Ahora `api/reembolso.js`
marca la licencia como revocada (`api/_revocacion.js`) y `api/validar.js` la
chequea además del HMAC. Si el mismo email vuelve a pagar de verdad más
adelante, esa compra nueva levanta la revocación sola — no hace falta nada
manual. **Requiere el mismo almacén (Vercel KV/Upstash)** que ya usás para la
cuota de IA; si no está configurado, el reembolso se sigue procesando igual
(la plata se devuelve siempre), solo que sin revocar la licencia.

## Atribución de ventas: qué canal/red social trae clientes

Cada botón de "Comprar" guarda los parámetros `utm_source`/`utm_medium`/
`utm_campaign` (si el link que trajo al visitante los tenía, ej.
`...?utm_source=instagram&utm_campaign=post1`) y los asocia al pago. Cuando
el pago se confirma, queda un registro en el almacén con plan, monto y de
dónde vino. Para verlo:

```
GET /api/ventas
Header: x-admin-secret: <tu ADMIN_SECRET>
```

Devuelve el total facturado y un desglose por canal (`utm_source`) y por
plan. Necesita `ADMIN_SECRET` (elegí cualquier string largo y agregalo en
Vercel → Environment Variables) — sin esa variable, el endpoint responde 503
en vez de quedar abierto sin protección.

## Recordatorio de la demo antes de que venza (email)

Quien arranca la demo de 3 días ahora también queda registrado
server-side (solo para esto, no cambia cómo funciona la demo en sí — ver
`api/_demo.js`). Un cron job diario revisa quién está en su segundo día sin
haber comprado todavía y le manda un email recordándole que la demo vence
mañana, con el link a precios.

Para activarlo:
1. Creá una cuenta gratis en [resend.com](https://resend.com) (no pide
   tarjeta) y sacá una API key.
2. Vercel → **Environment Variables**, agregá:
   - `RESEND_API_KEY` — la clave de Resend.
   - `RESEND_FROM` (opcional) — ej. `MV FBA IA <hola@tudominio.com>`, una vez
     que verifiques un dominio propio en Resend. Sin esto, manda desde
     `onboarding@resend.dev` (funciona pero con límites más bajos).
   - `CRON_SECRET` — cualquier string largo; Vercel lo manda solo como
     header al disparar el cron, así nadie más puede activar el envío de
     emails pegándole a la URL.
3. **Redeploy**. El cron (`vercel.json` → `crons`) ya está configurado para
   correr una vez por día. Sin `RESEND_API_KEY` o sin el almacén (KV/Upstash)
   configurados, el cron corre igual pero no manda nada — no rompe nada.

## Calculadora de ahorro en la landing

En la sección de precios hay una calculadora que compara cuánto gastaría el
visitante en Helium 10/Jungle Scout (según el plan y meses que elija) contra
el pago único de MV FBA IA. Es 100% client-side (no llama a ningún API), con
precios de referencia hardcodeados que conviene revisar cada tanto — quedó
aclarado en la propia página que son precios de referencia y pueden cambiar.

## Landing web (`landing/`) y dominio propio

La landing (`landing/index.html`) se despliega sola en Vercel en cada push
(`vercel.json` + `scripts/vercel-build.sh`, que además copia `mobile/` dentro
de `landing/app/` para que el botón "Probar demo" abra la app real). Hoy vive
en la URL de preview de la rama — nada en el código depende de esa URL (no
hay dominios hardcodeados en `landing/index.html` ni en `vercel.json`), así
que pasar a un dominio propio es una operación de configuración, sin tocar
código:

1. **Comprá/tené a mano tu dominio** (el registrador no importa).
2. En el proyecto de Vercel: **Settings → Domains → Add** → escribí el
   dominio. Vercel te va a pedir un registro DNS (`A` a `76.76.21.21` para un
   dominio raíz, o `CNAME` a `cname.vercel-dns.com` para un subdominio como
   `app.tudominio.com`) — lo cargás en tu proveedor de DNS y Vercel emite el
   certificado SSL solo.
3. Una vez que el dominio esté activo, actualizá estos dos lugares que SÍ
   quedan afuera del repo (viven en paneles externos):
   - **MercadoPago** → tu aplicación → URL del sitio/tienda (hoy tiene la URL
     de preview de Vercel, cargada como parche temporal).
   - Cualquier "back_url"/redirect que se configure cuando se conecte el
     checkout real de MercadoPago (pendiente, ver sección de pagos).
4. Opcional pero recomendado antes de vender en serio: agregar
   `<link rel="canonical">` y meta `og:url`/`og:image` en `landing/index.html`
   con el dominio final (no se agregaron todavía para no hardcodear una URL
   que iba a cambiar).

## El panel (14 pestañas, en español/inglés/portugués)

El **selector de idioma** arriba del sidebar cambia con un click las pestañas,
encabezados, botones y el tutorial completo a **español, inglés o portugués**
(`core/i18n.py`).

1. **Investigación** — dos fuentes: el **motor propio embebido** (gratis, sin APIs
   pagas: descubre keywords y nichos reales vía el autocompletado público de Amazon,
   la misma señal que explotan Helium 10/Jungle Scout) o CSV de Cerebro (suma
   volúmenes de búsqueda). Score de nicho → veredicto → listing.
2. **Recomendador** — el modo **proactivo**: sin escribir ninguna keyword, escanea
   categorías FBA probadas con el motor propio, filtra por tu rango de precio y
   devuelve una **lista rankeada de oportunidades** (demanda, competencia, precio)
   usando la misma fórmula auditable del asesor de éxito. Con Keepa conectada se
   afina con ventas estimadas reales; sin clave funciona igual, gratis
   (`agents/recomendador.py`).
3. **Mercado** — **productos estrella por rango de precios** (Keepa Product Finder:
   precio, BSR, ventas estimadas, rating y reseñas de cada competidor; sin clave,
   links directos a Amazon filtrados por precio), señales de competencia (barrera
   de reseñas, hueco de calidad), **proveedores mejor rankeados con link directo**
   (Alibaba Trade Assurance + Verified, RFQ Marketplace, Global Sources…) y el
   **asesor de probabilidad de éxito**: fórmula auditable (demanda 30 %, barrera de
   entrada 25 %, hueco de calidad 20 %, precio 15 %, margen 10 %) + análisis
   razonado con Claude si hay clave. Cierra con **¿Cuánto podrías ganar?**: invertís
   X plata (o comprás X unidades) y te desglosa cada costo (producto, flete,
   arancel, prep, comisión Amazon, FBA fee, publicidad) hasta la **ganancia neta
   para vos**, con ROI, tiempo de venta al techo y el escenario sostenido a 12
   meses reciclando capital.
4. **Pricing** — costos → precio sugerido, margen, ROI, semáforo. Botón
   **Guardar en portafolio** para pasar del cálculo a la gestión.
5. **Portafolio** — el corazón de la gestión: todos tus productos persistidos con
   **análisis financiero de cada uno** (unit economics, capital en pipeline, sueldo
   en meseta proyectado, proyección de caja a 12 meses y **ventas reales** cruzadas
   por ASIN). Consolidado del negocio + export CSV.
6. **Publicar** — el paquete completo para salir a vender: listing (título, bullets,
   descripción, backend keywords), **brief de las 7 fotos** que Amazon espera,
   **banner hero + infografía de beneficios generados como imagen PNG real**
   (Pillow, sin costo ni API — paleta de marca, descargables), precio y unit
   economics, **cantidades** (orden de prueba y primera compra al techo),
   **checklist de proveedor serio + RFQ en inglés** listo para Alibaba, y el paso
   a paso de Seller Central. Descargable como HTML imprimible.
7. **Caja** — proyección realista con lead time, DD+7, devoluciones y techo de demanda.
8. **Ventas** — registro de ventas y KPIs (facturación, neto, margen, mix).
9. **Inversores** — escenarios con capital externo y pitch HTML descargable.
10. **Plan** — cuántos productos necesitás para tu objetivo de ingreso, **cuántas horas por
    semana necesitás REALMENTE** (desglosado por tarea, distinguiendo lo que el bot y las
    alertas ya automatizan) + reinversión compuesta.
11. **Alertas** — outbox de emails (dry-run sin SMTP).
12. **Config** — estado de conexiones, prueba en vivo y **guardado seguro de claves**.
13. **Asistente IA (multi-proveedor, BYOK)** — chat que responde sobre tus métricas, tu
    portafolio y la estrategia FBA, usando tus **datos reales** como contexto. Elegís el
    proveedor en Config: **Claude (recomendada)**, OpenAI (ChatGPT) o Gemini — pegás la
    clave del que elijas. Sin clave, modo offline desde el glosario (nunca rompe). El
    asistente da **consejo**: no busca productos (los datos de mercado son de Keepa, no de
    un LLM — un modelo de lenguaje los inventaría).
14. **Ayuda** — **tutorial completo** del programa paso a paso (13 secciones, en el
    idioma elegido — `agents/tutorial.py`), **chat "Dudas del programa (IA)"** que
    responde cómo usar cualquier función desde el manual oficial (online con tu clave
    de IA, offline devuelve la sección del tutorial que corresponde), **glosario**
    buscable de FBA y finanzas (ROI, BSR, landed cost, techo de demanda, ACoS…),
    **guía de Amazon Advertising (PPC)** — Sponsored Products/Brands/Display,
    automática vs. manual, CPC — con calculadora de **ACoS máximo bancable**
    conectada al margen real de tu pricing, y el formulario de contacto/soporte.

## Motor propio vs herramientas pagas (honesto)

| Necesidad | Motor propio (gratis) | Herramienta paga |
|---|---|---|
| Descubrir keywords y nichos reales | ✅ Autocompletado público de Amazon | Helium 10 Magnet/Cerebro |
| Volumen de búsqueda numérico | Con `JUNGLE_SCOUT_API_KEY` (volumen real) o proxy de interés gratis | Helium 10 / Jungle Scout |
| Precio y BSR de un ASIN | Con `KEEPA_API_KEY` | Keepa |
| Productos estrella por rango de precio (ventas, rating, reseñas) | Con **Jungle Scout API** o `KEEPA_API_KEY` (Product Finder), o links filtrados gratis | Helium 10 Black Box / JS Product DB |
| Proveedores mejor rankeados | ✅ Links filtrados (Trade Assurance + Verified) + RFQ | — |
| Probabilidad de éxito del producto | ✅ Fórmula auditable + Claude | Jungle Scout Opportunity Score |
| Copy del listing | ✅ (offline o Claude) | — |
| Publicar en Amazon | ✅ Manual gratis, o **SP-API oficial de Amazon (gratis para sellers)** | — |

El motor propio **no inventa volúmenes**: lo dice explícitamente en el panel. Amazon
ordena su autocompletado por volumen real de búsqueda, así que el *ranking* es dato
real; el *número* de búsquedas/mes es la base de datos paga de esas herramientas.

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
| `GET /motor/keywords?seed=` | Motor propio: keywords y nichos reales, gratis. |
| `POST /publicar` | Paquete completo de publicación (listing, fotos, RFQ, pasos). |
| `GET /mercado/estrellas` | Productos estrella por rango de precios + competencia + proveedores. |
| `GET /exito` | Probabilidad de éxito del producto (fórmula auditable). |
| `POST /ganancias` | Ganancia potencial: desglose de costos y neto para X inversión o unidades. |
| `GET /dedicacion` | Horas por semana necesarias, por tarea (lanzamiento vs operación). |
| `GET /creativos/banner` | Banner hero PNG (marca, título, badges). |
| `GET /creativos/infografia` | Infografía de beneficios PNG. |

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
