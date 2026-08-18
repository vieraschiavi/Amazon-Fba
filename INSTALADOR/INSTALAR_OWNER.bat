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
echo  Ahi hay DOS archivos, las dos pre-activadas como Pro:
echo    MV_Amazon_FBA_IA_Owner_Setup.exe   instalador con icono/desinstalador
echo    MV_FBA_IA_Portable_Owner.zip       version sin instalador (descomprimir
echo                                       y correr INICIAR.bat)
echo.
echo  El build owner se republica SOLO en cada push a main, asi que
echo  siempre hay un instalador fresco ahi. Si por algun motivo la
echo  pagina diera 404, se puede lanzar a mano:
echo    GitHub ^> Actions ^> "Windows Installer" ^> Run workflow
echo    ^> tildar "owner" ^> Run
echo.

start "" "%RELEASE%"

echo  Si la descarga ya arranco, cerra esta ventana. Si dio 404,
echo  presiona una tecla para abrir la pagina del workflow y lanzarlo.
pause >nul
start "" "%ACTIONS%"
exit /b 0
