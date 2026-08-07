@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA

rem ============================================================
rem  MV FBA IA - App de escritorio (ventana nativa).
rem  Usa el runtime de Python embebido (bundleado por el instalador,
rem  ver runtime/) y abre la app en su propia ventana (desktop.py).
rem ============================================================

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

echo  Preparando MV FBA IA...
"!PYTHON!" core\db.py >nul 2>&1

rem pythonw = sin ventana de consola. La app abre en su ventana nativa y este
rem .bat termina; el proceso de la app queda vivo.
start "" "!PYTHONW!" "%~dp0desktop.py"
exit /b 0
