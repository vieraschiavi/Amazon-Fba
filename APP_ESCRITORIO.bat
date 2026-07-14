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

set "PYTHON=%~dp0runtime\python.exe"
set "PYTHONW=%~dp0runtime\pythonw.exe"
if not exist "!PYTHON!" (
    echo  [ERROR] Falta el runtime de Python embebido. Reinstala MV FBA IA;
    echo  el runtime esta incompleto o fue borrado.
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
