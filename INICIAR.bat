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

set "PYTHON=%~dp0runtime\python.exe"
if not exist "!PYTHON!" (
    echo  [ERROR] Falta el runtime de Python embebido. Reinstala MV FBA IA;
    echo  el runtime esta incompleto o fue borrado.
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo  [1/3] Runtime: !PYTHON!
echo  [2/3] Preparando base de datos...
"!PYTHON!" core\db.py >nul 2>&1

echo.
echo  ============================================================
echo    Panel + API : http://localhost:8000
echo    ^(el mismo servidor sirve el panel web y la API para n8n^)
echo    DEJA ESTA VENTANA ABIERTA mientras uses el sistema.
echo  ============================================================
echo.
start "" "http://localhost:8000/"
"!PYTHON!" -m uvicorn app:app --host 0.0.0.0 --port 8000
echo.
echo  (el panel se cerro)
pause
