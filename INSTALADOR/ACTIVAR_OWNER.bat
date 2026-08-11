@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA - Activar edicion OWNER

echo.
echo  ============================================================
echo    MV FBA IA - Pasar esta instalacion a edicion OWNER
echo    (plan Pro, sin limite de dias, sin pantalla de activacion)
echo  ============================================================
echo.
echo  NO recompila nada: le pide la licencia real al servidor y la
echo  deja instalada en la carpeta del programa. Al reabrirlo, se
echo  activa solo.
echo.
echo  USO INTERNO. Si esto llega a un cliente, tiene la version
echo  completa gratis: no lo repartas ni lo dejes en el instalador.
echo.

rem --- Encontrar la carpeta del programa -------------------------------------
rem Primero aca (el caso normal: este .bat se copia al lado del programa).
set "PROG="
if exist "%~dp0app.py" set "PROG=%~dp0"
if not defined PROG if exist "%ProgramFiles%\MV FBA IA\app.py" set "PROG=%ProgramFiles%\MV FBA IA\"
if not defined PROG if exist "%ProgramFiles(x86)%\MV FBA IA\app.py" set "PROG=%ProgramFiles(x86)%\MV FBA IA\"
if not defined PROG if exist "%LOCALAPPDATA%\Programs\MV FBA IA\app.py" set "PROG=%LOCALAPPDATA%\Programs\MV FBA IA\"
if not defined PROG if exist "%USERPROFILE%\Desktop\MV FBA IA\app.py" set "PROG=%USERPROFILE%\Desktop\MV FBA IA\"

if not defined PROG (
    echo  [X] No encontre la instalacion de MV FBA IA.
    echo.
    echo      Copia ESTE archivo y activar_owner.py DENTRO de la carpeta
    echo      del programa ^(la que tiene app.py adentro^) y volve a abrirlo.
    echo.
    pause
    exit /b 1
)
echo  Instalacion encontrada:
echo    !PROG!
echo.

rem --- Python: el runtime que trae el programa; si no, el del sistema --------
set "PYTHON="
if exist "!PROG!runtime\python.exe" set "PYTHON=!PROG!runtime\python.exe"
if not defined PYTHON if exist "%~dp0_entorno.bat" (
    call "%~dp0_entorno.bat" buscar_python
)
if not defined PYTHON if exist "!PROG!_entorno.bat" (
    call "!PROG!_entorno.bat" buscar_python
)
if not defined PYTHON (
    echo  [X] No encontre Python.
    echo      Si instalaste MV FBA IA, la carpeta runtime\ tiene que estar
    echo      adentro. Reinstala el programa y volve a probar.
    echo.
    pause
    exit /b 1
)

rem --- El script hace el trabajo (y se puede leer: no esconde nada) ----------
set "SCRIPT=%~dp0activar_owner.py"
if not exist "!SCRIPT!" set "SCRIPT=!PROG!activar_owner.py"
if not exist "!SCRIPT!" (
    echo  [X] Falta activar_owner.py al lado de este .bat.
    echo      Copia los DOS archivos juntos.
    echo.
    pause
    exit /b 1
)

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"!PYTHON!" "!SCRIPT!" --carpeta "!PROG!."
set "CODIGO=!ERRORLEVEL!"

echo.
if "!CODIGO!"=="0" (
    echo  ============================================================
    echo    Listo. Cerra el programa y volve a abrirlo.
    echo  ============================================================
) else (
    echo  No se pudo activar. El detalle esta arriba.
)
echo.
pause
exit /b !CODIGO!
