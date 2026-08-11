# MV FBA IA — versión portable (sin instalador)

Es el **mismo programa** que el instalador `.exe`, con el mismo motor Python y
la misma base de licencia — solo que no hay que instalar nada. Existe para las
PCs de empresa donde la política de seguridad bloquea ejecutar `.exe`
descargados de internet (SmartScreen/AppLocker), pero sí permite `.bat`/`.vbs`.

La diferencia de fondo con la versión Electron: acá el panel abre como una
**pestaña del navegador** (`http://localhost:PUERTO/`) en vez de una ventana
propia — es el mismo panel React, no una versión distinta.

## Usar

1. Descomprimí el `.zip` donde quieras (no hace falta ser administrador).
2. Doble clic en **`INICIAR.bat`**. La primera vez tarda unos segundos en
   preparar la base de datos; después abre el panel solo en el navegador.
3. Dejá esa ventana de consola abierta mientras usás el programa — al
   cerrarla, se apaga el motor.

## Icono de Escritorio y Menú Inicio (opcional)

Doble clic en **`CREAR_ACCESOS_DIRECTOS.bat`**. Crea:

- un icono en el Escritorio,
- un grupo **"MV FBA IA"** en el Menú Inicio, con accesos a abrir el
  programa, a *Diagnóstico* y a *Desinstalar*.

No pide permisos de administrador ni toca el registro de Windows: son
accesos directos comunes que apuntan a esta misma carpeta.

## Desinstalar

Doble clic en **`DESINSTALAR.bat`**. Borra el icono del Escritorio y el grupo
del Menú Inicio. Si además querés borrar la carpeta del programa y tus datos
(la base de datos local, tu `.env`), te lo pregunta antes de hacerlo — nada
se borra sin que lo confirmes.

Si nunca corriste `CREAR_ACCESOS_DIRECTOS.bat`, borrar la carpeta a mano
(o arrastrarla a la Papelera) alcanza: no queda nada instalado en ningún
otro lado — ni registro, ni servicios, ni tareas programadas.

## Otros lanzadores incluidos

| Archivo | Para qué |
|---|---|
| `DIAGNOSTICO.bat` | Revisa que Python y los módulos estén bien instalados |
| `CONECTAR.bat` | Verifica las conexiones reales (Keepa, Claude, SMTP, CSV) |
| `API.bat` | Levanta solo la API (para integrarla con n8n) |

## Si algo falla

- **"No se encontró Python"**: la carpeta `runtime\` tiene que venir completa
  del `.zip` — si la recortaste o algo la borró, volvé a descomprimir.
- **Windows Defender SmartScreen en el `.zip`**: pasa porque no tiene firma
  de código, igual que el instalador `.exe`. *Más información* → *Ejecutar
  de todas formas*.
- **El antivirus lo pone en cuarentena**: mismo motivo. Agregalo como
  excepción o descargalo desde el sitio oficial.
