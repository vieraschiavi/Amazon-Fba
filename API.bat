@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title FBA - API (n8n)
set "PYTHON="
if exist "C:\ProgramData\Anaconda3\python.exe" set "PYTHON=C:\ProgramData\Anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\anaconda3\python.exe" set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
if not defined PYTHON ( for %%V in (313 312 311 310) do if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" )
if not defined PYTHON ( py -c "import sys;print(sys.executable)" >"%TEMP%\pyapi.txt" 2>nul & set /p PYTHON=<"%TEMP%\pyapi.txt" & del "%TEMP%\pyapi.txt" >nul 2>&1 )
if not defined PYTHON ( echo [ERROR] Python no encontrado & pause & exit /b 1 )
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: ¿el puerto 8000 ya esta ocupado?
set "OCUPADO="
for /f "tokens=*" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do set "OCUPADO=1"
if defined OCUPADO (
    echo.
    echo  La API ya esta corriendo en el puerto 8000. No la levanto de nuevo.
    echo  Si queres reiniciarla: cerra la ventana "FBA - API" anterior y volve a abrir esta.
    echo.
    pause & exit /b 0
)
"!PYTHON!" core\db.py >nul 2>&1
echo  API en http://localhost:8000  (Ctrl+C para cortar)
"!PYTHON!" -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
