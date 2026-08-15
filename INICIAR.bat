@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA

echo.
echo  ============================================================
echo    MV AMAZON FBA IA - Cockpit inteligente Amazon FBA
echo    Panel + API + base de datos, todo con un doble clic.
echo  ============================================================
echo.

rem Runtime embebido si esta; si no, Python del sistema (ver _entorno.bat).
call "%~dp0_entorno.bat" buscar_python
if errorlevel 1 (
    echo  [ERROR] No se encontro Python.
    echo.
    echo  Si INSTALASTE MV FBA IA: reinstalalo, el runtime incluido
    echo  ^(runtime\python.exe^) esta incompleto o fue borrado.
    echo  Si bajaste el CODIGO del repositorio: instala Python 3.10+
    echo  desde python.org y volve a abrir este archivo.
    echo.
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo  [1/3] Runtime: !PYTHON!
echo  [2/3] Preparando base de datos...
"!PYTHON!" core\db.py >nul 2>&1

rem Puerto: NO pisar el de otra aplicacion. Si el 8000 esta tomado se usa el
rem primero libre hacia arriba, y se avisa cual quedo.
echo  [3/3] Buscando un puerto libre...
call "%~dp0_entorno.bat" buscar_puerto 8000
if errorlevel 1 (
    echo.
    echo  [ERROR] No hay ningun puerto libre entre el 8000 y el 8019.
    echo  Cerra alguna aplicacion que este usando esos puertos y volve a probar.
    echo.
    pause
    exit /b 1
)
if not "!PUERTO!"=="8000" (
    echo.
    echo  Aviso: el puerto 8000 lo esta usando otra aplicacion.
    echo  MV FBA IA arranca en el !PUERTO! -- no se toca lo que ya estaba.
)

echo.
echo  ============================================================
echo    Panel + API : http://localhost:!PUERTO!
echo    ^(el mismo servidor sirve el panel web y la API para n8n^)
echo    DEJA ESTA VENTANA ABIERTA mientras uses el sistema.
echo  ============================================================
echo.
rem Bind a 127.0.0.1 (solo esta PC), NO a 0.0.0.0. La API /api/* no tiene
rem autenticacion: con 0.0.0.0 cualquier equipo de la misma red (WiFi de
rem cowork, cafe, hotel) podia leer/escribir toda la base y hasta el .env
rem (POST /api/config). El panel y n8n corren en esta misma maquina, asi que
rem localhost alcanza. Si de verdad necesitas exponerlo a otra maquina de tu
rem red (n8n en otro host), poné antes de correr esto:  set MVFBA_HOST=0.0.0.0
rem -- pero solo en una red de confianza, porque queda sin auth.
if not defined MVFBA_HOST set "MVFBA_HOST=127.0.0.1"
start "" "http://localhost:!PUERTO!/"
"!PYTHON!" -m uvicorn app:app --host !MVFBA_HOST! --port !PUERTO!
echo.
echo  (el panel se cerro)
pause
