@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title MV FBA IA - Instalador (version cliente)

set "URL=https://mvfbaia.com/api/descarga?demo=1"
set "DESTINO=%TEMP%\MV_Amazon_FBA_IA_Setup.exe"

echo.
echo  ============================================================
echo    MV AMAZON FBA IA - Instalador para Windows
echo    Version CLIENTE (demo de 7 dias, se activa con licencia)
echo  ============================================================
echo.
echo  El instalador no viaja dentro del ZIP porque pesa ~126 MB
echo  (GitHub no acepta archivos de mas de 100 MB en el repo).
echo  Este paso lo baja del sitio oficial y lo ejecuta.
echo.

where curl >nul 2>&1
if errorlevel 1 (
  echo  [X] Este Windows no trae curl (hace falta Windows 10 1803 o mas nuevo^).
  echo      Descargalo a mano desde:
  echo      %URL%
  echo.
  pause
  exit /b 1
)

echo  [1/3] Descargando desde mvfbaia.com ...
if exist "%DESTINO%" del /f /q "%DESTINO%" >nul 2>&1
curl -L --fail --progress-bar -o "%DESTINO%" "%URL%"
if errorlevel 1 goto :fallo
if not exist "%DESTINO%" goto :fallo

echo  [2/3] Verificando el archivo ...
rem Un instalador real de Inno pesa mas de 50 MB. Si bajo algo chico, lo que
rem llego es una pagina de error o un JSON, no el programa: mejor avisarlo
rem ahora que dejar que Windows falle con "no es una aplicacion valida".
for %%A in ("%DESTINO%") do set "BYTES=%%~zA"
if !BYTES! LSS 52428800 (
  echo  [X] Lo que se descargo pesa solo !BYTES! bytes: no es el instalador.
  echo      Probablemente el servidor respondio un error. Reintentá en un rato
  echo      o descargalo a mano desde: %URL%
  del /f /q "%DESTINO%" >nul 2>&1
  echo.
  pause
  exit /b 1
)

echo  [3/3] Abriendo el instalador ...
echo.
echo  Si aparece "Windows protegio tu PC": Mas informacion ^> Ejecutar de todas
echo  formas. Es porque el .exe todavia no tiene firma de codigo.
echo.
start "" "%DESTINO%"
exit /b 0

:fallo
echo.
echo  [X] No se pudo descargar el instalador.
echo      Revisá tu conexion y reintentá, o descargalo a mano desde:
echo      %URL%
echo.
pause
exit /b 1
