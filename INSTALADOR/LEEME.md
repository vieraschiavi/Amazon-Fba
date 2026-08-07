# INSTALADOR — MV FBA IA

Esta carpeta es el punto de entrada para **instalar el programa en Windows**.

El instalador (`.exe`) **no vive acá adentro**: pesa ~126 MB (trae Python
embebido + Electron con su propio Chromium) y GitHub rechaza cualquier archivo
de más de 100 MB en el repo. Vive en los **Releases**, que es el lugar correcto
para binarios grandes, y estos dos `.bat` lo traen de ahí con un doble clic.

| Doble clic en… | Qué instala | Para quién |
|---|---|---|
| `INSTALAR_CLIENTE.bat` | Versión **cliente** (arranca en demo de 7 días; con la licencia pasa a completa) | Cualquiera |
| `INSTALAR_OWNER.bat` | Versión **owner** (arranca ya activada, plan Pro, sin pedir clave) | Solo el dueño |

---

## Versión CLIENTE

`INSTALAR_CLIENTE.bat` descarga el instalador desde `mvfbaia.com` y lo ejecuta.
Es exactamente el mismo archivo que baja un comprador desde la web, así que
sirve para probar de punta a punta lo que recibe el cliente.

Cómo funciona el ciclo del cliente:

1. Baja el instalador desde `https://mvfbaia.com` (botón *"Descargar demo de
   escritorio"*) o con este `.bat`.
2. Instala y usa el programa **7 días completos**, con todas las funciones.
3. Cuando se le vence, la app le pide la licencia.
4. Paga en la web → recibe la clave por email → la pega en la app → queda
   activada la versión completa. **No hay que volver a descargar nada**: es el
   mismo programa, la licencia le saca el límite.

## Versión OWNER

`INSTALAR_OWNER.bat` abre la página del Release `owner-latest` en el navegador.
Ese Release es **privado**: solo alguien con acceso al repo lo ve. Como ya
estás logueado en GitHub para haber bajado este ZIP, la descarga sale sola —
**no hay que escribir ninguna clave, ni un token, ni el mail**.

El instalador owner trae adentro la licencia ya horneada (`owner_licencia.json`,
emitida por el build a nombre de `OWNER_EMAIL`), así que el programa abre
directamente en Pro: sin pantalla de activación, sin cuenta regresiva.

> Si el Release todavía no existe: GitHub → pestaña **Actions** → workflow
> **Windows Installer** → *Run workflow* → tildar **owner** → *Run*. Cuando
> termina, el `.exe` queda publicado en `owner-latest`.

---

## Qué hace el instalador (las dos versiones)

- Deja **elegir la carpeta de instalación** (podés mandarlo a `D:\` si `C:\`
  está lleno) y las tareas opcionales.
- Crea el **icono en el Escritorio** y el grupo en el **Menú Inicio**.
- Instala un **desinstalador** (Panel de control → Aplicaciones → *MV Amazon
  FBA IA* → Desinstalar), que borra todo lo que dejó, incluida la carpeta.
- El programa abre en **su propia ventana** (Electron con su Chromium propio):
  no abre el navegador, no depende de que Windows tenga WebView2 y **no usa
  Streamlit**.
- Elige un **puerto libre real** al arrancar (se lo pide al sistema operativo),
  así que no choca con nada que ya tengas escuchando.

## Si algo falla

- **"No se pudo descargar"** en el `.bat` de cliente → probá abrir
  `https://mvfbaia.com/api/descarga?demo=1` a mano en el navegador.
- **Windows SmartScreen** ("Windows protegió tu PC") → *Más información* →
  *Ejecutar de todas formas*. Pasa porque el `.exe` todavía no tiene firma de
  código; no es un error del instalador.
- **El antivirus lo pone en cuarentena** → misma razón; agregalo como excepción
  o descargalo desde la web oficial.
