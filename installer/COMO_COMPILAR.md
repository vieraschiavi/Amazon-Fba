# Instalador de Windows — cómo compilarlo

Este instalador se genera con **Inno Setup** (gratis, el estándar de facto para
instaladores de Windows — lo usan VS Code, Notepad++, Git for Windows, etc).
Este proyecto corre en un contenedor Linux y **no puede compilar un ejecutable
`.exe` de Windows** (necesita el compilador de Inno Setup, que solo corre en
Windows). El script `.iss` de acá está completo y listo: compilarlo es un paso
de un clic en una PC con Windows.

## Pasos (una sola vez, ~2 minutos)

1. Descargá **Inno Setup 6** (gratis): https://jrsoftware.org/isdl.php
2. Instalalo (siguiente, siguiente, listo).
3. Abrí `installer/MV_Amazon_FBA_IA.iss` con Inno Setup (doble clic si asociaste
   la extensión, o `Abrir` desde la app).
4. Apretá **Build → Compile** (o `F9`).
5. El instalador final queda en `installer/Output/MV_Amazon_FBA_IA_Setup.exe`.

Ese `.exe` es el que le das al cliente/gerente/comprador: un instalador con
asistente (wizard), licencia, accesos directos en Escritorio y Menú Inicio, y
desinstalador — el mismo tipo de experiencia que un programa comercial.

## Qué hace el instalador

- Instala en `%LOCALAPPDATA%\Programs\MV Amazon FBA IA` (carpeta del usuario,
  **sin pedir permisos de administrador** — así no choca con el control de
  cuentas de usuario de Windows).
- Crea accesos directos: abrir el panel (silencioso, sin ventana de consola),
  Diagnóstico, Verificar conexiones y Desinstalar.
- Si no detecta Python instalado, ofrece abrir la página de descarga oficial.
- El primer uso sigue haciendo lo mismo que `INICIAR.bat`: instala las
  dependencias de Python (una vez, con internet) y abre el panel en el
  navegador.
- Al desinstalar, pregunta si también querés borrar tu base de datos y tus
  claves guardadas (por si vas a reinstalar más adelante).

## Firma de código (opcional, para verse 100% "de confianza")

Windows SmartScreen puede advertir la primera vez que alguien ejecuta un
instalador sin firmar (esto le pasa a cualquier instalador nuevo, no es un
error). Para eliminar esa advertencia definitivamente hace falta un
**certificado de firma de código** (Code Signing Certificate), que se compra a
una autoridad certificadora (ej. DigiCert, Sectigo) — es un trámite pago y
verificado por identidad, no algo que se pueda generar automáticamente. Si lo
comprás, firmás el `.exe` resultante con `signtool.exe` (incluido en el SDK de
Windows) y la advertencia desaparece.

## Alternativa sin compilar nada

Si por ahora no tenés una PC con Windows a mano para compilar, `INICIAR.bat`
(en la raíz del proyecto) ya funciona como "instalador de un clic": detecta
Python, instala dependencias y abre el panel. No tiene wizard ni desinstalador,
pero es 100% funcional hoy mismo sin pasos adicionales.
