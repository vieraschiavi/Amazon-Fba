@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title MV FBA IA - Instalador (version sin instalador / portable)

set "URL=https://mvfbaia.com/api/descarga?demo=1&tipo=bat"
set "ZIP=%TEMP%\MV_FBA_IA_Portable.zip"
set "DESTINO=%USERPROFILE%\Desktop\MV FBA IA"

echo.
echo  ============================================================
echo    MV AMAZON FBA IA - Version SIN INSTALADOR (portable)
echo    Para PCs donde la empresa bloquea ejecutar .exe
echo  ============================================================
echo.
echo  Esto baja un .zip (no un .exe) y lo descomprime en:
echo    %DESTINO%
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
where tar >nul 2>&1
if errorlevel 1 (
  echo  [X] Este Windows no trae tar (hace falta Windows 10 1803 o mas nuevo^)
  echo      para descomprimir. Baja el .zip a mano y descomprimilo con
  echo      cualquier programa ^(el Explorador de Windows tambien puede^):
  echo      %URL%
  echo.
  pause
  exit /b 1
)

echo  [1/4] Descargando desde mvfbaia.com ...
if exist "%ZIP%" del /f /q "%ZIP%" >nul 2>&1
curl -L --fail --progress-bar -o "%ZIP%" "%URL%"
if errorlevel 1 goto :fallo
if not exist "%ZIP%" goto :fallo

echo  [2/4] Verificando el archivo ...
rem El .zip portable pesa bastante mas que esto (trae Python embebido con
rem sus dependencias adentro). Si bajo algo chico, lo que llego es una
rem pagina de error o un JSON, no el paquete real.
for %%A in ("%ZIP%") do set "BYTES=%%~zA"
if !BYTES! LSS 10485760 (
  echo  [X] Lo que se descargo pesa solo !BYTES! bytes: no es el paquete.
  echo      Probablemente el servidor respondio un error. Reintenta en un
  echo      rato o descargalo a mano desde: %URL%
  del /f /q "%ZIP%" >nul 2>&1
  echo.
  pause
  exit /b 1
)

echo  [3/4] Descomprimiendo en el Escritorio ...
if exist "%DESTINO%" (
  echo.
  echo  Ya existe "%DESTINO%": se sobreescriben los archivos del programa.
  echo  Tu base de datos y tu licencia, si ya la habias activado ahi, quedan
  echo  intactas -- viven en archivos que el paquete nuevo no trae adentro.
  echo.
) else (
  mkdir "%DESTINO%" >nul 2>&1
)
tar -xf "%ZIP%" -C "%DESTINO%"
if errorlevel 1 goto :fallo

echo  [4/4] Listo.
echo.
echo  ============================================================
echo    Carpeta:   %DESTINO%
echo    Abrir el programa:  doble clic en INICIAR.bat
echo    Icono de Escritorio y Menu Inicio ^(opcional^):
echo      doble clic en CREAR_ACCESOS_DIRECTOS.bat
echo  ============================================================
echo.
start "" "%DESTINO%"
exit /b 0

:fallo
echo.
echo  [X] Algo fallo bajando o descomprimiendo el paquete.
echo      Revisa tu conexion y reintenta, o descargalo a mano desde:
echo      %URL%
echo.
pause
exit /b 1
