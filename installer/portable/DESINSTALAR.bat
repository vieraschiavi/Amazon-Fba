@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA - Desinstalar (version portable)

set "CARPETA=%~dp0"
set "CARPETA=%CARPETA:~0,-1%"

echo.
echo  ============================================================
echo    MV FBA IA - Desinstalar (version portable, sin instalador)
echo  ============================================================
echo.
echo  Esto borra el icono del Escritorio y el grupo del Menu Inicio.
echo  La carpeta del programa NO se toca todavia -- se pregunta aparte.
echo.
pause

if exist "%USERPROFILE%\Desktop\MV FBA IA.lnk" del /f /q "%USERPROFILE%\Desktop\MV FBA IA.lnk" >nul 2>&1
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\MV FBA IA" rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\MV FBA IA" >nul 2>&1
echo  Accesos directos borrados.
echo.

set /p BORRAR="Borrar tambien la carpeta del programa y tus datos (%CARPETA%)? [s/N] "
if /I not "%BORRAR%"=="s" (
    echo.
    echo  Listo. La carpeta del programa se dejo intacta.
    echo.
    pause
    exit /b 0
)

echo.
echo  Borrando la carpeta en unos segundos ^(se cierra esta ventana sola^)...
rem No se puede borrar la carpeta mientras este .bat corre desde ADENTRO de
rem ella: el proceso tiene el archivo abierto. Se lanza un cmd aparte con el
rem comando de borrado (no una copia del script), con un timeout que le da
rem tiempo a ESTE proceso de terminar y soltar la carpeta antes de intentarlo.
start "" cmd /c "timeout /t 2 >nul & rmdir /s /q ""%CARPETA%"""
exit /b 0
