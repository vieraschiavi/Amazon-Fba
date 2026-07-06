# MV FBA IA — App móvil NATIVA (corre en el teléfono, sin PC)

App autocontenida para **gerentes y compradores**: administrás tu negocio Amazon
FBA entero desde el celular — portafolio, ganancias, mercado y asistente — **sin
depender de ninguna PC y sin internet** para lo esencial.

Toda la matemática del negocio corre **en el teléfono** (`js/nucleo.js`, un port
fiel del motor Python, validado campo a campo contra el original) y tus datos
viven en `localStorage` del propio dispositivo. Lo único que usa internet son dos
funciones opcionales (keywords reales de Amazon y el asistente Claude abierto), y
usan los **datos móviles del celular**, nunca una PC.

## Qué incluye

- **Inicio** — resumen ejecutivo: facturación, neto, margen y semáforo del
  portafolio, calculado a partir de tus productos y ventas.
- **Portafolio** — cargás cada producto (costo, flete, arancel, prep, precio,
  competencia, techo de demanda) y ves margen, ROI, neto/unidad y semáforo al
  instante. Registrás ventas reales por producto. Todo persiste en el teléfono.
- **Ganancias** — el simulador "¿cuánto podría ganar?" con desglose completo de
  costos, ROI, meses de venta y sueldo en meseta reciclando capital 12 meses.
- **Mercado** — probabilidad de éxito de un nicho (demanda, barrera de entrada,
  hueco de calidad, precio, margen), productos estrella ilustrativos y, si hay
  internet, las keywords reales del autocompletado público de Amazon.
- **Asistente IA** — responde desde tus datos (sueldo meseta, portafolio,
  margen/ROI/ACOS, dedicación) **offline**. Con una clave de Claude cargada en
  Config y con internet, responde cualquier consulta abierta.
- **Config** — claves opcionales (Keepa, Claude), backup exportar/importar,
  cargar datos de ejemplo y borrar todo. Nada sale del teléfono sin tu acción.

## Cómo se usa

1. Abrí la app (APK de Android, o esta carpeta servida como PWA en el navegador).
2. La primera vez, la bienvenida te lleva a cargar tu primer producto (o probar
   con datos de ejemplo).
3. Listo: margen, ROI, ganancias, mercado y asistente funcionan **sin conectar
   nada**. Si querés keywords en vivo de Amazon o el asistente abierto, cargá las
   claves en Config y usá los datos/WiFi del celular.

## Android nativo (APK)

El proyecto Gradle en `../android/` empaqueta esta carpeta como assets dentro de
un APK y la hospeda en un `WebView`. La app es nativa y autocontenida: abre
offline y no le pide nada a ninguna PC. Las llamadas online opcionales pasan por
un **puente nativo** (`MainActivity.java` → `PuenteNativo.httpRequest`) que hace
el HTTP en Java para esquivar el bloqueo CORS del origen `file://`. En JS, ese
puente se usa transparentemente desde `pedirHTTP()` (si no está —p. ej. en el
navegador durante desarrollo— cae a `fetch` directo).

## Probar como PWA (desarrollo)

No tiene build step: serví la carpeta como sitio estático y abrila en el
navegador del celular o de la PC.

```
python -m http.server 8090   # parado en mobile/
```

Se puede "instalar" a la pantalla de inicio (Android: *Agregar a pantalla de
inicio*; iOS: *Compartir → Agregar a inicio*): abre a pantalla completa con ícono
propio y funciona offline gracias al service worker.

## Validación del motor

`../test/verificar_nucleo.js` corre el motor JavaScript con los mismos inputs que
el motor Python (`../agents/*`) y compara **cada campo** contra la referencia
(`../test/nucleo_referencia.json`). Deben dar idéntico: hasta el centavo, la
unidad y la redacción. Regenerá la referencia con
`python ../test/generar_referencia.py` si cambian las fórmulas en `agents/`.

```
node ../test/verificar_nucleo.js   # OK = motor JS idéntico al Python
```

## Estructura

```
mobile/
├── index.html          Shell de la app (una sola pagina, 6 vistas por tab)
├── manifest.json        Metadata de instalacion (nombre, iconos, colores)
├── service-worker.js     Cache del shell para abrir/operar 100% offline
├── css/estilos.css       Diseño responsive, paleta navy/verde de marca
├── js/nucleo.js          Motor de negocio (port fiel del Python) — corre en el telefono
├── js/app.js             UI, navegacion, persistencia en localStorage, puente de red
└── icons/                Icono de la app (192/512/512-maskable)
```
