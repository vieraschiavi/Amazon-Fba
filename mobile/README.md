# MV Amazon FBA IA — App móvil (Android/iOS, PWA responsive)

App web progresiva (PWA), pensada para **gerentes y compradores**: chequeás el
estado del negocio, evaluás un producto o le preguntás al asistente IA desde el
celular, sin instalar nada de una tienda de apps. Consume la misma API
(`app.py`) que ya usa el panel de escritorio — no duplica lógica de negocio,
solo la muestra de forma responsive y táctil.

## Qué incluye

- **Inicio** — resumen ejecutivo: facturación, neto, margen, semáforo del
  portafolio.
- **Portafolio** — cada producto con su margen, ROI y ventas reales.
- **Ganancias** — el simulador "¿cuánto podría ganar?" con desglose completo.
- **Mercado** — productos estrella, competencia y probabilidad de éxito.
- **Asistente IA** — el mismo chat con Claude (u offline) del panel.
- **Config** — la IP/puerto de tu API (se guarda en el celular).

Instalable en la pantalla de inicio de Android ("Agregar a pantalla de
inicio") e iOS ("Compartir → Agregar a inicio"): abre a pantalla completa,
como una app nativa, con ícono propio.

## Cómo probarlo

1. Corré la API en tu PC: doble clic en `API.bat` (o dejá `INICIAR.bat`
   abierto) — queda escuchando en el puerto `8000`.
2. Serví esta carpeta como sitio estático. Ejemplos:
   - `python -m http.server 8090` parado en `mobile/`
   - o cualquier hosting estático (Netlify, GitHub Pages, Vercel — la carpeta
     no tiene build step, se sube tal cual).
3. Abrí la URL en el navegador del celular (Chrome/Android o Safari/iOS).
4. Entrá a **Config** y escribí la URL de la API — si el celular está en la
   misma red WiFi que la PC, usá la IP local de la PC (ej.
   `http://192.168.0.10:8000`), no `localhost` (ese apuntaría al celular).
5. Guardá — si conecta bien, ya podés usar todas las pestañas.

## CORS

`app.py` ya tiene `CORSMiddleware` habilitado con `allow_origins=["*"]` para
que esta app (servida desde otro origen/puerto) pueda llamarla sin bloqueos
del navegador. Como la API no maneja sesiones ni cookies, abrir el origen no
expone datos de otros usuarios — solo hace que cualquier front-end pueda
consumirla (igual que ya hacía n8n).

## Qué NO es

No es una app nativa de Android (no usa Kotlin/Java ni pasa por Google Play).
Es una PWA: HTML/CSS/JS puro, sin dependencias ni paso de build, que corre en
cualquier navegador moderno y se "instala" como acceso directo con ícono
propio. Es el camino más liviano y mantenible para tener una versión móvil
real sin duplicar todo el desarrollo en un lenguaje distinto.

## Estructura

```
mobile/
├── index.html          Shell de la app (una sola pagina, 6 vistas por tab)
├── manifest.json        Metadata de instalacion (nombre, iconos, colores)
├── service-worker.js     Cache del shell estatico (los datos SIEMPRE se piden en vivo)
├── css/estilos.css       Diseño responsive, misma paleta navy/verde del panel
├── js/app.js             Logica: navegacion, fetch a la API, render de cada vista
└── icons/                Icono de la app (192/512/512-maskable)
```
