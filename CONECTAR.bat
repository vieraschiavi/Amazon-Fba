@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA - Verificar conexiones
set "PYTHON="
if exist "C:\ProgramData\Anaconda3\python.exe"  set "PYTHON=C:\ProgramData\Anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\anaconda3\python.exe" set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
if not defined PYTHON ( for %%V in (313 312 311 310) do if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" )
if not defined PYTHON ( py -c "import sys;print(sys.executable)" >"%TEMP%\pyc.txt" 2>nul & set /p PYTHON=<"%TEMP%\pyc.txt" & del "%TEMP%\pyc.txt" >nul 2>&1 )
if not defined PYTHON ( echo [ERROR] Python no encontrado & pause & exit /b 1 )
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
if not exist ".env" "!PYTHON!" test_conexiones.py --init-env
echo.
"!PYTHON!" test_conexiones.py %*
echo.
pause
