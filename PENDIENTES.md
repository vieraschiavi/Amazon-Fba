# Pendientes — MV FBA IA

> Estado verificado el **2026-08-12** contra producción (mvfbaia.com), GitHub y
> CI real. La versión anterior de este archivo (2026-07-25) describía tres
> bloqueadores que **ya se resolvieron**; se reescribe entero en vez de
> parchearlo para no arrastrar información vieja mezclada con la nueva.

---

## Ya resuelto desde la última vez (no reabrir sin evidencia nueva)

| Bloqueador viejo | Qué pasó |
|---|---|
| CI sin runner, `pc-latest` congelado en julio | El repo pasó a público (Actions con minutos ilimitados) y volvió a privado; el build owner se arregló para funcionar en los dos casos (ver `api/_owner_github.js`). `pc-latest` se republicó, última vez **2026-08-12 04:41**. |
| Descarga daba 401 (`GITHUB_RELEASE_TOKEN`) | Verificado en producción: `/api/descarga?demo=1` → `302`, igual `&tipo=bat`. |
| Instalador owner nunca compilado | El mecanismo ya funciona sin configurar nada (autorización = acceso de escritura al repo). Sigue faltando que alguien **corra el workflow una vez** — ver más abajo. |

Y de yapa, cosas que no estaban ni en la lista vieja:

- **Versión portable sin instalador** (`.zip`, para PCs que bloquean `.exe`): en producción, `MV_FBA_IA_Portable.zip`, 81.7 MB.
- Migración completa de Streamlit a **Electron + React** para el cliente (el panel legacy ya no se distribuye).
- Herramienta `ACTIVAR_OWNER.bat` para pasar una instalación ya hecha a edición owner sin recompilar.
- Auditoría de validación de entrada en toda la API de negocio: 3 endpoints devolvían resultados imposibles con HTTP 200 (unidades/facturación negativas), uno **crasheaba con HTTP 500** (`/api/plan/interes-compuesto` con años muy altos), y uno **corrompía datos** (`/api/ventas` guardaba ventas negativas en la base). Los cinco arreglados y con test de regresión.
- **Suite de tests**: 82 pytest + 12 suites JS (antes: "47/47" sin más detalle).

---

## Pendiente 1 — Compilar el build owner (una vez)

El instalador owner (`.exe` y `.zip`, pre-activados en Pro, sin pedir mail ni
clave al abrir) **todavía no existe** — nadie corrió el workflow con
`owner: true` desde que el mecanismo se arregló.

```
GitHub → Actions → "Windows Installer (EXE)" → Run workflow → tildar "owner" → Run
```

Yo no puedo dispararlo: mi integración no tiene permiso de `workflow_dispatch`.

**Cómo verificar que quedó bien:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  https://github.com/vieraschiavi/Amazon-Fba/releases/tag/owner-latest
# 200 -> ya existe.  404 -> todavia no se corrio el build owner.
```

---

## Pendiente 2 — Cargar los 3 secrets del keystore de Android nuevo

El keystore de firma viejo estaba commiteado en texto plano y se rotó (PR
#69). El nuevo se entregó **fuera del repo**. Sin cargar los secrets, el
próximo build de Android falla mostrando exactamente cuál falta — ya se
confirmó en CI real, no es un bug:

```
##[error]Falta el secret MVFBA_KEYSTORE_BASE64. Sin el keystore no se puede firmar el APK.
```

```
GitHub → tu repo → Settings → Secrets and variables → Actions → New repository secret
  MVFBA_KEYSTORE_BASE64     <- del archivo que te mandé
  MVFBA_KEYSTORE_PASSWORD   <- del archivo que te mandé
  MVFBA_KEY_ALIAS           <- mvfba-release
```

Nadie había descargado el APK viejo (`download_count: 0`), así que rotar la
clave no rompe ninguna instalación existente — no hay apuro por el lado de
usuarios, solo por tener el build de Android funcionando de nuevo.

---

## Pendiente 3 — El keystore viejo sigue en el historial de git

Se sacó del árbol actual (`git rm --cached`), pero **no se reescribió
historia** — eso es una operación destructiva (`git filter-repo` o similar +
force-push) que requiere tu confirmación explícita antes de que la haga.
La clave vieja está rotada y no sirve para firmar nada que el proyecto vaya
a aceptar, así que el riesgo práctico hoy es bajo — pero si en algún momento
querés que el historial quede completamente limpio, avisame y lo encaramos
aparte (cambia los hashes de commit de toda la rama, así que hay que
coordinarlo).

---

## Pendiente de producto — falta traducir la PWA / app de celular

El **panel de escritorio** ya está traducido a inglés y portugués
(formularios, KPI, tablas, textos que arma el backend). La **PWA / app de
celular** (`mobile/`) sigue casi toda en español: solo cambia de idioma la
pantalla de licencia. Es otra base de código (JS a mano, sin el sistema de
i18n del panel), así que merece su propio cambio — sin tocar todavía.

---

## Pendiente de verificación — nadie probó el instalador en Windows real

Todo lo de esta sesión se verificó con: pytest local, 12 suites JS, CI de
GitHub Actions (que sí compila en un Windows real, pero no instala/desinstala
interactivamente), y sondeo directo de la API en producción. Lo que **ningún
test cubre**: instalar de verdad en una PC Windows, mandarlo a `D:\`, abrir
desde el ícono del Escritorio (no el navegador), desinstalar y confirmar que
la carpeta desaparece entera. Es el único hueco real del "end to end".

---

## Nota — el plan free de Vercel tiene 100 deploys/día

Se agotó una vez esta sesión (varios pushes seguidos disparan un preview
cada uno). Mensaje si vuelve a pasar:
```
Resource is limited - try again in 24 hours (more than 100, code: "api-deployments-free-per-day")
```
No afecta producción (`mvfbaia.com` sigue sirviendo lo último ya desplegado),
solo bloquea publicar cambios **nuevos** por 24 horas. Se resuelve solo; no
hay nada para arreglar en código.

---

## Notas para retomar

- La **visibilidad del repo** (público/privado) cambió varias veces en esta
  sesión — antes de asumir cuál es, chequeala en GitHub. El build owner
  funciona en los dos casos desde el PR #66; el resto de los workflows
  también, aunque un repo público tiene minutos de Actions ilimitados y uno
  privado tiene cuota mensual.
- `landing/app/` **no se commitea**: lo genera `scripts/vercel-build.sh`
  copiando `mobile/`. Si tocás la PWA, editá `mobile/` (es la fuente de
  verdad).
- `DOMINIO = "MV-Amazon-Fba"` y `LICENCIA_SECRETO` **no se cambian nunca**:
  cambiarlos invalida las licencias ya vendidas.
- Las dos fuentes de verdad del reloj de la demo son `core/licencia.py` (PC)
  y `mobile/js/licencia.js` (PWA/Android). Si cambia la duración, hay que
  ajustar también la ventana del mail recordatorio en
  `api/cron-recordatorio-demo.js`.
- El keystore de Android (`android/app/mv-release.keystore`) **no vive en el
  repo** desde el PR #69: variables de entorno / GitHub Secrets, ver
  `android/README.md`. Si perdés el archivo, no hay forma de recuperarlo.
