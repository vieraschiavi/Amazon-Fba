@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA - Verificar conexiones
set "PYTHON=%~dp0runtime\python.exe"
if not exist "!PYTHON!" (
    echo  [ERROR] Falta el runtime de Python embebido. Reinstala MV FBA IA;
    echo  el runtime esta incompleto o fue borrado.
    pause
    exit /b 1
)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
if not exist ".env" "!PYTHON!" test_conexiones.py --init-env
echo.
"!PYTHON!" test_conexiones.py %*
echo.
pause
