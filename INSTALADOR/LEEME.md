# INSTALADOR — MV FBA IA

Esta carpeta es el punto de entrada para **poner a andar el programa en
Windows**. Hay DOS formas de correrlo — instalado (`.exe`) o portable
(`.zip`, sin instalador) — porque algunas empresas bloquean ejecutar `.exe`
bajados de internet (SmartScreen/AppLocker) pero sí permiten `.bat`/`.vbs`.
Las dos son el mismo programa, el mismo motor y la misma licencia.

Ninguno de los dos vive acá adentro: el `.exe` pesa ~126 MB y el `.zip`
portable no se queda muy atrás (los dos traen Python embebido) — GitHub
rechaza cualquier archivo de más de 100 MB en el repo. Viven en los
**Releases**, que es el lugar correcto para binarios grandes, y estos `.bat`
los traen de ahí con un doble clic.

| Doble clic en… | Qué trae | Para quién |
|---|---|---|
| `INSTALAR_CLIENTE.bat` | El instalador **`.exe`** (icono, Menú Inicio, desinstalador) | Cualquiera |
| `INSTALAR_CLIENTE_SIN_INSTALADOR.bat` | La versión **portable `.zip`** (sin instalar nada) | Cualquiera, sobre todo si el `.exe` está bloqueado |
| `INSTALAR_OWNER.bat` | Las dos versiones owner (`.exe` y `.zip`), pre-activadas | Solo el dueño |

Las dos versiones de cliente arrancan en **demo de 7 días** y pasan a
completas con la misma licencia (paga en la web → clave por email → la pegás
en la app). No hay versión "recortada": la portable tiene exactamente las
mismas funciones que la instalada.

---

## Versión CLIENTE — instalador `.exe`

`INSTALAR_CLIENTE.bat` descarga el instalador desde `mvfbaia.com` y lo
ejecuta. Es exactamente el mismo archivo que baja un comprador desde la web.

- Deja **elegir la carpeta de instalación** (podés mandarlo a `D:\` si `C:\`
  está lleno) y las tareas opcionales.
- Crea el **icono en el Escritorio** y el grupo en el **Menú Inicio**.
- Instala un **desinstalador** (Panel de control → Aplicaciones → *MV Amazon
  FBA IA* → Desinstalar), que borra todo lo que dejó, incluida la carpeta.
- El programa abre en **su propia ventana** (Electron con su Chromium propio):
  no abre el navegador, no depende de que Windows tenga WebView2 y **no usa
  Streamlit**.

## Versión CLIENTE — portable `.zip` (sin instalador)

`INSTALAR_CLIENTE_SIN_INSTALADOR.bat` descarga un `.zip` y lo descomprime en
el Escritorio (`%USERPROFILE%\Desktop\MV FBA IA`) — no instala nada, no pide
permisos de administrador, no toca el registro de Windows.

- El programa abre como una **pestaña del navegador** (`INICIAR.bat`), no una
  ventana propia — mismo panel, mismo motor Python, misma base de licencia.
- Un doble clic aparte en `CREAR_ACCESOS_DIRECTOS.bat` (adentro de esa
  carpeta) crea el **icono de Escritorio** y el grupo del **Menú Inicio**,
  con acceso también a **Diagnóstico** y a **Desinstalar**.
- `DESINSTALAR.bat` borra esos accesos directos y, si se confirma, la
  carpeta entera con los datos.

## Pasar una instalación YA HECHA a owner (sin recompilar)

Si ya tenés el programa instalado (la versión de cliente, o la portable) y
querés dejarlo en edición owner **sin bajar otro instalador ni esperar un
build**: copiá `ACTIVAR_OWNER.bat` y `activar_owner.py` dentro de la carpeta
del programa (la que tiene `app.py`) y doble clic en el `.bat`.

Le pide la licencia real al servidor y la deja instalada. Al reabrir el
programa, se activa solo — plan Pro, sin límite de días, sin pantalla de
activación.

**Necesita una cosa, una sola vez: un token de GitHub** con acceso de
escritura a este repo (o el `OWNER_BUILD_TOKEN`). No se puede evitar, y no es
un capricho del diseño: la clave se firma con `LICENCIA_SECRETO`, que vive
solo en Vercel, así que ningún programa local puede calcularla — hay que
pedírsela al servidor. Y el servidor no se la da a cualquiera que diga ser el
dueño, porque el mail del dueño es público y adivinarlo es trivial. Ese token
es lo único que separa "el dueño" de "un cliente que quiere Pro gratis".

El token se escribe a mano (no se muestra en pantalla) y **no se guarda en
ningún lado**. También se puede pasar por variable de entorno
`MV_GITHUB_TOKEN` para no tipearlo.

> **Uso interno.** No repartas estos dos archivos ni los pongas en el
> instalador. Aunque se filtraran no le servirían a nadie sin un token con
> acceso de escritura al repo (el servidor devuelve 403), pero no hay motivo
> para regalar el mapa.

## Versión OWNER (las dos)

`INSTALAR_OWNER.bat` abre la página del Release `owner-latest` en el
navegador. Ese Release es **privado**: solo alguien con acceso al repo lo ve.
Como ya estás logueado en GitHub para haber bajado este ZIP, la descarga sale
sola — **no hay que escribir ninguna clave, ni un token, ni el mail**. Ahí
hay dos archivos, los dos pre-activados como Pro (traen `owner_licencia.json`
adentro, emitido a nombre de `OWNER_EMAIL`): el instalador `.exe` y el `.zip`
portable. Elegís el que quieras probar.

> Si el Release todavía no existe: GitHub → pestaña **Actions** → workflow
> **Windows Installer** → *Run workflow* → tildar **owner** → *Run*. Cuando
> termina, los dos archivos quedan publicados en `owner-latest`.

---

## Cómo elegir (y cuándo cambiar de opinión)

- **Empezá por el `.exe`** si no sabés si hace falta la portable: es la
  experiencia más pulida (ventana propia, icono, desinstalador normal).
- Si Windows lo bloquea (SmartScreen, "el administrador restringió esta
  app", o directamente no deja hacer doble clic) — **pasá a la portable**
  sin perder nada: es el mismo programa, misma licencia, mismos datos si
  activaste la licencia primero.

## Si algo falla

- **"No se pudo descargar"** en cualquiera de los dos `.bat` de cliente →
  probá abrir la URL que imprime el propio error (`/api/descarga?demo=1`, o
  con `&tipo=bat` para la portable) a mano en el navegador.
- **Windows SmartScreen** ("Windows protegió tu PC") en el `.exe` → *Más
  información* → *Ejecutar de todas formas*. Pasa porque todavía no tiene
  firma de código; no es un error del instalador.
- **El antivirus lo pone en cuarentena** → misma razón; agregalo como
  excepción, o pasate a la versión portable si no podés hacer eso.
- **"Este Windows no trae curl/tar"** → hace falta Windows 10 versión 1803 o
  más nuevo (los trae de fábrica desde ahí). Bajá el archivo a mano con la
  URL que imprime el `.bat`.
