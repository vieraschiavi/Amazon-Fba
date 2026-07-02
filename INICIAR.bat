@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title FBA Operations

echo.
echo  ============================================================
echo    FBA OPERATIONS - Sistema de gestion Amazon FBA
echo    Panel + API + base de datos, todo con un doble clic.
echo  ============================================================
echo.

set "PYTHON="
if exist "C:\ProgramData\Anaconda3\python.exe" set "PYTHON=C:\ProgramData\Anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\anaconda3\python.exe" set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\miniconda3\python.exe" set "PYTHON=%USERPROFILE%\miniconda3\python.exe"
if not defined PYTHON if exist "C:\ProgramData\miniconda3\python.exe" set "PYTHON=C:\ProgramData\miniconda3\python.exe"
if not defined PYTHON if exist "%LOCALAPPDATA%\anaconda3\python.exe" set "PYTHON=%LOCALAPPDATA%\anaconda3\python.exe"
if not defined PYTHON ( for %%V in (313 312 311 310) do if not defined PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" )
if not defined PYTHON (
    py -c "import sys;print(sys.executable)" >"%TEMP%\pyfba.txt" 2>nul
    if not errorlevel 1 set /p PYTHON=<"%TEMP%\pyfba.txt"
    del "%TEMP%\pyfba.txt" >nul 2>&1
)
if not defined PYTHON (
    echo  [ERROR] No se encontro Python. Instala Anaconda o Python 3.10+ y volve a probar.
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

echo  [3/4] Preparando base de datos...
"!PYTHON!" core\db.py >nul 2>&1

set "OCUPADO="
for /f "tokens=*" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do set "OCUPADO=1"
if defined OCUPADO (
    echo  [4/4] API ya corriendo en el puerto 8000 - no se levanta de nuevo.
) else (
    "!PYTHON!" -c "import fastapi,uvicorn" >nul 2>&1
    if errorlevel 1 (
        echo  [4/4] API omitida: faltan fastapi/uvicorn ^(reintenta con internet^).
    ) else (
        echo  [4/4] Levantando API en http://localhost:8000 ^(ventana minimizada^)...
        start "FBA - API" /min "!PYTHON!" -m uvicorn app:app --host 0.0.0.0 --port 8000
    )
)

echo.
echo  ============================================================
echo    Panel : http://localhost:8501
echo    API   : http://localhost:8000  ^(para n8n / automatizacion^)
echo    DEJA ESTA VENTANA ABIERTA mientras uses el sistema.
echo    Si el navegador no abre solo, copia el link del panel a mano.
echo  ============================================================
echo.
"!PYTHON!" -m streamlit run dashboard_app.py
echo.
echo  (el panel se cerro)
pause
