@echo off
rem ===========================================================================
rem  _entorno.bat — Deteccion de Python y de puerto libre, COMPARTIDA por los
rem  lanzadores (INICIAR, APP_ESCRITORIO, API, CONECTAR, DIAGNOSTICO,
rem  LEGACY_STREAMLIT). El prefijo "_" avisa que no se abre a mano.
rem
rem  POR QUE EXISTE: cada .bat tenia su propia copia de la deteccion y se
rem  fueron desincronizando -- dos quedaron con fallback al Python del sistema
rem  y cuatro murian con "[ERROR] Falta el runtime de Python embebido" sin
rem  ofrecer salida. Eso deja tirado a cualquiera que corra el proyecto desde
rem  el codigo (runtime/ NO esta en el repositorio: lo arma el instalador).
rem  Una sola copia, un solo comportamiento.
rem
rem  Uso:
rem     call "%~dp0_entorno.bat" buscar_python
rem        -> deja PYTHON y PYTHONW seteados, o ERRORLEVEL 1 si no hay ninguno.
rem     call "%~dp0_entorno.bat" buscar_puerto 8000
rem        -> deja PUERTO con el primero libre desde el que se pidio.
rem ===========================================================================
if /I "%~1"=="buscar_python" goto :buscar_python
if /I "%~1"=="buscar_puerto" goto :buscar_puerto
echo  [_entorno.bat] accion desconocida: %~1
exit /b 2

rem ---------------------------------------------------------------------------
:buscar_python
rem 1) El runtime embebido que trae el instalador: es el que hay que usar
rem    siempre que este, porque tiene las dependencias ya instaladas.
set "PYTHON="
set "PYTHONW="
if exist "%~dp0runtime\python.exe" (
    set "PYTHON=%~dp0runtime\python.exe"
    set "PYTHONW=%~dp0runtime\pythonw.exe"
    exit /b 0
)
rem 2) Sin runtime (repositorio clonado a mano, o instalacion incompleta):
rem    se busca un Python del sistema en vez de cortar de golpe.
if exist "C:\ProgramData\Anaconda3\python.exe" set "PYTHON=C:\ProgramData\Anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\anaconda3\python.exe" set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
if not defined PYTHON if exist "%USERPROFILE%\miniconda3\python.exe" set "PYTHON=%USERPROFILE%\miniconda3\python.exe"
if not defined PYTHON if exist "C:\ProgramData\miniconda3\python.exe" set "PYTHON=C:\ProgramData\miniconda3\python.exe"
if not defined PYTHON if exist "%LOCALAPPDATA%\anaconda3\python.exe" set "PYTHON=%LOCALAPPDATA%\anaconda3\python.exe"
if not defined PYTHON (
    for %%V in (313 312 311 310) do if not defined PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
)
if not defined PYTHON (
    py -c "import sys;print(sys.executable)" >"%TEMP%\mvfba_py.txt" 2>nul
    if not errorlevel 1 set /p PYTHON=<"%TEMP%\mvfba_py.txt"
    del "%TEMP%\mvfba_py.txt" >nul 2>&1
)
if not defined PYTHON exit /b 1
rem pythonw del sistema: al lado del python.exe encontrado (si no esta, se usa
rem el mismo python.exe -- solo cambia que puede quedar una consola abierta).
for %%P in ("!PYTHON!") do set "PYTHONW=%%~dpPpythonw.exe"
if not exist "!PYTHONW!" set "PYTHONW=!PYTHON!"
exit /b 0

rem ---------------------------------------------------------------------------
:buscar_puerto
rem Devuelve en PUERTO el primer puerto LIBRE desde el pedido. Antes se usaba
rem 8000 fijo: si otra aplicacion ya lo tenia tomado, uvicorn moria con un
rem error de socket que no explicaba nada.
rem
rem La busqueda la hace core/puerto.py y NO este .bat: parsear
rem `netstat | findstr` es fragil (depende del idioma de Windows, y ":8000 "
rem puede matchear dentro de otro puerto) y ademas no prueba lo unico que
rem importa -- si el servidor va a poder TOMAR el puerto. El script intenta el
rem bind real, en el mismo host que usa uvicorn.
set "PUERTO="
if not defined PYTHON call "%~dp0_entorno.bat" buscar_python
if not defined PYTHON exit /b 1
for /f "usebackq tokens=*" %%p in (`""%PYTHON%" "%~dp0core\puerto.py" %~2"`) do set "PUERTO=%%p"
if not defined PUERTO exit /b 1
exit /b 0
