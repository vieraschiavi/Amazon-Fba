@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title MV FBA IA - Instalador (version cliente)

rem La demo abierta se dio de baja: /api/descarga?demo=1 ya no entrega nada
rem (devuelve 410). El instalador se baja con el LINK PROPIO que cada cliente
rem recibe en la pagina de gracias despues de pagar -- ese link lleva su
rem payment_id y vence, asi que no puede quedar fijo aca adentro.

set "DESTINO=%TEMP%\MV_Amazon_FBA_IA_Setup.exe"
set "COMPRA=https://mvfbaia.com/#precios"
set "DEMO=https://mvfbaia.com/#solicitar-demo"

echo.
echo  ============================================================
echo    MV AMAZON FBA IA - Instalador para Windows
echo    Version CLIENTE (se activa con tu licencia)
echo  ============================================================
echo.
echo  Necesitas el link de descarga de TU compra:
echo    1. Abri la pagina de gracias que te quedo despues de pagar
echo       ^(tambien te llego por mail^).
echo    2. Click derecho en "Programa para PC (Windows)" ^> Copiar direccion del enlace.
echo    3. Pegalo aca abajo y apreta Enter.
echo.
echo  Si todavia no compraste:  %COMPRA%
echo  Si queres verlo primero:  %DEMO%  ^(demo 1:1, te lo muestro en vivo^)
echo.

set "URL="
set /p "URL=Pega aca tu link de descarga: "
if not defined URL (
  echo.
  echo  [X] No pegaste ningun link. Cerra y volve a intentar.
  pause
  exit /b 1
)
rem Solo https de dominios propios: sin esto, pegar cualquier cosa hace que
rem este .bat baje y EJECUTE un binario de donde sea.
echo !URL! | findstr /I /R "^https://mvfbaia\.com/ ^https://github\.com/vieraschiavi/ ^https://release-assets\.githubusercontent\.com/" >nul
if errorlevel 1 (
  echo.
  echo  [X] Ese link no es del sitio oficial. Copialo de nuevo desde tu pagina de compra.
  pause
  exit /b 1
)

where curl >nul 2>&1
if errorlevel 1 (
  echo  [X] Este Windows no trae curl ^(hace falta Windows 10 1803 o mas nuevo^).
  echo      Bajalo a mano pegando tu link en el navegador.
  pause
  exit /b 1
)

echo.
echo  [1/2] Descargando ...
curl -L --fail -o "%DESTINO%" "!URL!"
if errorlevel 1 (
  echo.
  echo  [X] No se pudo descargar. El link puede haber vencido:
  echo      volve a abrir tu pagina de compra y copia uno nuevo.
  pause
  exit /b 1
)

echo  [2/2] Abriendo ...
start "" "%DESTINO%"
echo.
echo  Listo. Segui los pasos en pantalla.
pause
exit /b 0
