@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA - Diagnostico
echo ============================================================
echo  DIAGNOSTICO
echo ============================================================
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
echo  Python: !PYTHON!
"!PYTHON!" --version
echo.
echo  Modulos instalados:
"!PYTHON!" -c "import streamlit; print('  streamlit', streamlit.__version__)" 2>nul || echo   streamlit: NO INSTALADO
"!PYTHON!" -c "import pandas; print('  pandas', pandas.__version__)" 2>nul || echo   pandas: NO INSTALADO
echo.
echo  Carpeta actual: %CD%
echo  Archivos clave:
if exist dashboard_app.py (echo   dashboard_app.py OK) else (echo   dashboard_app.py FALTA)
if exist config.py (echo   config.py OK) else (echo   config.py FALTA)
if exist core\db.py (echo   core\db.py OK) else (echo   core\db.py FALTA)
if exist agents\pricing.py (echo   agents\pricing.py OK) else (echo   agents\pricing.py FALTA)
if exist data\cerebro.py (echo   data\cerebro.py OK) else (echo   data\cerebro.py FALTA)
if exist .env (echo   .env OK ^(claves configuradas^)) else (echo   .env sin crear ^(el sistema corre igual en modo offline^))
echo.
echo  streamlit: modulo del panel legacy interno, no se usa en la app actual;
echo  "NO INSTALADO" aqui es normal y esperado.
pause
