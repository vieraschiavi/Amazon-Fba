@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA - Diagnostico
echo ============================================================
echo  DIAGNOSTICO
echo ============================================================
set "PYTHON="
if exist "C:\ProgramData\Anaconda3\python.exe" set "PYTHON=C:\ProgramData\Anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\anaconda3\python.exe" set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
if not defined PYTHON ( py -c "import sys;print(sys.executable)" >"%TEMP%\pd.txt" 2>nul & set /p PYTHON=<"%TEMP%\pd.txt" & del "%TEMP%\pd.txt" >nul 2>&1 )
if not defined PYTHON ( echo  [ERROR] No hay Python. Instala Anaconda. & pause & exit /b 1 )
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
echo  Si streamlit dice NO INSTALADO, corre INICIAR.bat una vez con internet.
pause
