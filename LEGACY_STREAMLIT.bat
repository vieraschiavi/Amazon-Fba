@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA

echo.
echo  ============================================================
echo    PANEL VIEJO (Streamlit) - VERSION OBSOLETA
echo  ============================================================
echo.
echo   Esto NO es el programa MV FBA IA que se vende.
echo   Es el panel LEGACY de Streamlit: se abre en el navegador,
echo   se ve distinto y ya no recibe mejoras. No se instala en el
echo   producto final.
echo.
echo   El programa REAL es una aplicacion de escritorio (React +
echo   Electron): ventana propia, sin navegador ni consola.
echo   Se instala con MV_Amazon_FBA_IA_Setup.exe y te deja elegir
echo   la carpeta de instalacion.
echo.
echo      https://github.com/vieraschiavi/Amazon-Fba/releases/tag/pc-latest
echo.
echo   Si bajaste el CODIGO (Amazon-Fba-main) y solo queres probar
echo   el programa real desde aca, cerra esta ventana y abri:
echo      INICIAR.bat        (panel nuevo React en el navegador)
echo.
echo  ============================================================
echo.
choice /C SN /N /M "  Abrir igual el panel VIEJO de Streamlit? (S/N): "
if errorlevel 2 exit /b 0
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

echo  [1/4] Python: !PYTHON!
echo  [2/4] Verificando dependencias (instala solo la primera vez, puede tardar)...
"!PYTHON!" -c "import streamlit,pandas,fastapi,uvicorn" >nul 2>&1
if errorlevel 1 "!PYTHON!" -m pip install --user -r requirements.txt

"!PYTHON!" -c "import streamlit,pandas" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] No se pudieron instalar las dependencias.
    echo  Revisa tu conexion a internet y volve a abrir este archivo.
    echo  Detalle del error:
    "!PYTHON!" -m pip install --user -r requirements.txt
    pause
    exit /b 1
)

rem En Python muy nuevo (3.13/3.14), altair viejo revienta los graficos; si
rem importar altair falla, lo actualizamos (typing_extensions + altair 5.5+).
"!PYTHON!" -c "import altair" >nul 2>&1
if errorlevel 1 "!PYTHON!" -m pip install --user -U typing_extensions "altair>=5.5.0" >nul 2>&1

echo  [3/4] Preparando base de datos...
"!PYTHON!" core\db.py >nul 2>&1

rem Puertos: no pisar los de otra aplicacion (bind real, core/puerto.py).
call "%~dp0_entorno.bat" buscar_puerto 8000
set "PUERTO_API=!PUERTO!"
call "%~dp0_entorno.bat" buscar_puerto 8501
set "PUERTO_PANEL=!PUERTO!"
if not defined PUERTO_PANEL (
    echo  [ERROR] No hay puerto libre para el panel entre el 8501 y el 8520.
    pause
    exit /b 1
)

if not defined PUERTO_API (
    echo  [4/4] API omitida: no hay puerto libre entre el 8000 y el 8019.
) else (
    "!PYTHON!" -c "import fastapi,uvicorn" >nul 2>&1
    if errorlevel 1 (
        echo  [4/4] API omitida: faltan fastapi/uvicorn ^(reintenta con internet^).
    ) else (
        echo  [4/4] Levantando API en http://localhost:!PUERTO_API! ^(ventana minimizada^)...
        start "FBA - API" /min "!PYTHON!" -m uvicorn app:app --host 0.0.0.0 --port !PUERTO_API!
    )
)

echo.
echo  ============================================================
echo    Panel : http://localhost:!PUERTO_PANEL!
echo    API   : http://localhost:!PUERTO_API!  ^(para n8n / automatizacion^)
echo    DEJA ESTA VENTANA ABIERTA mientras uses el sistema.
echo    Si el navegador no abre solo, copia el link del panel a mano.
echo  ============================================================
echo.
"!PYTHON!" -m streamlit run dashboard_app.py --server.port !PUERTO_PANEL!
echo.
echo  (el panel se cerro)
pause
