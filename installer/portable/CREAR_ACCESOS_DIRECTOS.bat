@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title MV FBA IA - Crear accesos directos

echo.
echo  ============================================================
echo    MV FBA IA - Crear icono de Escritorio y Menu Inicio
echo  ============================================================
echo.
echo  Esto NO instala nada ni pide permisos de administrador: solo
echo  crea dos accesos directos que apuntan a esta misma carpeta.
echo.

cscript //nologo "%~dp0crear_accesos.vbs"
if errorlevel 1 (
    echo.
    echo  [X] No se pudieron crear los accesos directos.
    echo.
    pause
    exit /b 1
)
exit /b 0
