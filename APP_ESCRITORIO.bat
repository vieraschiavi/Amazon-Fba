@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA

rem ============================================================
rem  MV FBA IA - App de escritorio (ventana nativa).
rem  Detecta Python, instala dependencias la primera vez y abre
rem  la app en su propia ventana (desktop.py, sin navegador).
rem ============================================================

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

echo  Preparando MV FBA IA (la primera vez instala dependencias)...
"!PYTHON!" -c "import streamlit,pandas,webview" >nul 2>&1
if errorlevel 1 "!PYTHON!" -m pip install --user -r requirements.txt
"!PYTHON!" -c "import streamlit,pandas" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] No se pudieron instalar las dependencias. Revisa tu internet y reintenta.
    "!PYTHON!" -m pip install --user -r requirements.txt
    pause
    exit /b 1
)
rem En Python muy nuevo (3.13/3.14), altair viejo revienta los graficos
rem ("TypedDict ... closed"). Si importar altair falla, lo actualizamos.
"!PYTHON!" -c "import altair" >nul 2>&1
if errorlevel 1 "!PYTHON!" -m pip install --user -U typing_extensions "altair>=5.5.0" >nul 2>&1
"!PYTHON!" core\db.py >nul 2>&1

rem pythonw = sin ventana de consola. La app abre en su ventana nativa y este
rem .bat termina; el proceso de la app queda vivo.
set "PYW=!PYTHON:python.exe=pythonw.exe!"
if not exist "!PYW!" set "PYW=!PYTHON!"
start "" "!PYW!" "%~dp0desktop.py"
exit /b 0
