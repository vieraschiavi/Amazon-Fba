@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title FBA - Panel

set "PYTHON="
if exist "C:\ProgramData\Anaconda3\python.exe" set "PYTHON=C:\ProgramData\Anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\anaconda3\python.exe" set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\miniconda3\python.exe" set "PYTHON=%USERPROFILE%\miniconda3\python.exe"
if not defined PYTHON if exist "C:\ProgramData\miniconda3\python.exe" set "PYTHON=C:\ProgramData\miniconda3\python.exe"
if not defined PYTHON if exist "%LOCALAPPDATA%\anaconda3\python.exe" set "PYTHON=%LOCALAPPDATA%\anaconda3\python.exe"
if not defined PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if not defined PYTHON (
    py -c "import sys;print(sys.executable)" >"%TEMP%\pyfba.txt" 2>nul
    if not errorlevel 1 set /p PYTHON=<"%TEMP%\pyfba.txt"
    del "%TEMP%\pyfba.txt" >nul 2>&1
)
if not defined PYTHON (
    echo  [ERROR] No se encontro Python. Instala Anaconda y volve a probar.
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo  Python: !PYTHON!
echo  Verificando Streamlit (instala la primera vez, puede tardar)...
"!PYTHON!" -c "import streamlit" >nul 2>&1
if errorlevel 1 "!PYTHON!" -m pip install --user streamlit==1.45.1 pandas

"!PYTHON!" -c "import streamlit,pandas" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] No se pudo instalar Streamlit/pandas.
    echo  Revisa tu conexion a internet y volve a abrir este archivo.
    echo  Detalle:
    "!PYTHON!" -m pip install --user streamlit==1.45.1 pandas
    pause
    exit /b 1
)

"!PYTHON!" core\db.py >nul 2>&1
echo.
echo  ============================================================
echo   Abriendo el panel:  http://localhost:8501
echo   DEJA ESTA VENTANA ABIERTA mientras uses el panel.
echo   Si el navegador no abre solo, copia ese link a mano.
echo  ============================================================
echo.
"!PYTHON!" -m streamlit run dashboard_app.py
echo.
echo  (el panel se cerro)
pause
