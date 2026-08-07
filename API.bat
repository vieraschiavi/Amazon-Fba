@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA - API (n8n)

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

rem Puerto: NO pisar el de otra aplicacion. Antes se miraba
rem `netstat | findstr ":8000"` y, si estaba tomado, se cortaba diciendo "la
rem API ya esta corriendo" -- pero el que tenia el puerto podia ser CUALQUIER
rem programa, no esta API. Ademas ":8000" sin espacio matchea tambien 18000.
rem Ahora se busca el primer puerto libre de verdad (bind real, core/puerto.py).
call "%~dp0_entorno.bat" buscar_puerto 8000
if errorlevel 1 (
    echo.
    echo  [ERROR] No hay ningun puerto libre entre el 8000 y el 8019.
    echo  Cerra alguna aplicacion que este usando esos puertos y volve a probar.
    echo.
    pause
    exit /b 1
)

"!PYTHON!" -c "import fastapi,uvicorn" >nul 2>&1
if errorlevel 1 "!PYTHON!" -m pip install --user -r requirements.txt
"!PYTHON!" core\db.py >nul 2>&1

if not "!PUERTO!"=="8000" (
    echo.
    echo  ============================================================
    echo   Aviso: el puerto 8000 lo esta usando otra aplicacion.
    echo   Esta API arranca en el !PUERTO! y NO toca lo que ya estaba.
    echo.
    echo   Si la usas desde n8n, actualiza la URL de los workflows a
    echo   http://localhost:!PUERTO!  ^(estaban apuntando al 8000^).
    echo  ============================================================
)
echo.
echo  API en http://localhost:!PUERTO!  (Ctrl+C para cortar)
"!PYTHON!" -m uvicorn app:app --host 0.0.0.0 --port !PUERTO!
pause
