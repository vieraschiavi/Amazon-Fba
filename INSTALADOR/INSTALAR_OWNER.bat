@echo off
setlocal
chcp 65001 >nul 2>&1
title MV FBA IA - Instalador (version owner)

set "RELEASE=https://github.com/vieraschiavi/Amazon-Fba/releases/tag/owner-latest"
set "ACTIONS=https://github.com/vieraschiavi/Amazon-Fba/actions/workflows/windows-installer.yml"

echo.
echo  ============================================================
echo    MV AMAZON FBA IA - Instalador para Windows
echo    Version OWNER (arranca ya activada, plan Pro)
echo  ============================================================
echo.
echo  Se abre en el navegador la pagina del Release privado
echo  "owner-latest". Como ya estas logueado en GitHub (por eso
echo  pudiste bajar este ZIP^), la descarga sale sola: no hay que
echo  escribir ninguna clave, ni un token, ni el mail.
echo.
echo  Ahi bajas:  MV_Amazon_FBA_IA_Owner_Setup.exe
echo  y le das doble clic para instalar.
echo.
echo  Si la pagina da 404, el build owner todavia no se corrio:
echo    GitHub ^> Actions ^> "Windows Installer" ^> Run workflow
echo    ^> tildar "owner" ^> Run
echo.

start "" "%RELEASE%"

echo  ¿Dio 404? Presioná una tecla para abrir tambien la pagina del
echo  workflow y lanzarlo. Si la descarga ya arranco, cerrá esta ventana.
pause >nul
start "" "%ACTIONS%"
exit /b 0
