; MV_Amazon_FBA_IA.iss — Instalador profesional (Inno Setup) de MV FBA IA.
;
; Como compilar (en Windows, con Inno Setup 6 — gratis, jrsoftware.org/isinfo.php):
;   1. Instala Inno Setup 6.
;   2. Abri este archivo con el editor de Inno Setup (o doble clic).
;   3. Apreta Build > Compile (F9). El instalador queda en installer\Output\.
;   O desde la consola: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" MV_Amazon_FBA_IA.iss
;
; El usuario elige DONDE instalar y si lo hace para todos los usuarios (Archivos
; de programa, pide UAC) o solo para el (sin UAC). Se puede instalar en cualquier
; carpeta porque los datos del usuario (base, .env, CSV) ya NO viven junto al
; programa: van a %LOCALAPPDATA%\MV FBA IA (ver _dir_datos() en config.py).

#define MyAppName "MV FBA IA"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "MV FBA IA"
#define MyAppUrl "https://mvfbaia.com"
#define MyAppExeDescription "Cockpit inteligente para tu negocio Amazon FBA"

[Setup]
AppId={{8F2C1A6E-7B4D-4E1A-9C3F-2D8E5A6B7C90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments={#MyAppExeDescription}
; Estos tres salen en "Aplicaciones instaladas" de Windows, al lado del
; programa. Sin ellos la entrada queda sin soporte ni sitio: se ve amateur.
AppPublisherURL={#MyAppUrl}
AppSupportURL={#MyAppUrl}
AppUpdatesURL={#MyAppUrl}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
; Metadatos del PROPIO .exe del instalador (pestaña Detalles de Propiedades).
; Sin esto el archivo que descarga el cliente aparece sin version, sin empresa
; y sin descripcion -- ademas de verse improvisado, los filtros de reputacion
; de Windows y de los antivirus tratan peor a un .exe sin metadatos.
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador de {#MyAppName}
VersionInfoCopyright=© {#MyAppPublisher}
; La carpeta por defecto se resuelve en [Code]: "Archivos de programa" si
; instala como admin, o la carpeta del usuario si elige "solo para mi".
; NO se usa {autopf}: depende de SHGetKnownFolderPath(FOLDERID_UserProgramFiles),
; que en algunos entornos falla y aborta el instalador con "Failed to expand
; shell folder constant". {commonpf} y {localappdata} son estables.
DefaultDirName={code:CarpetaPorDefecto}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Siempre mostrar la pagina de "elegir carpeta", tambien al actualizar.
DisableDirPage=no
; Ademas, repetir la carpeta elegida en la pagina "Todo listo para instalar":
; asi el usuario CONFIRMA a la vista donde va a quedar el programa antes de
; apretar Instalar, y no hay dudas de que se pudo elegir el destino.
AlwaysShowDirOnReadyPage=yes
; Arranca sin pedir admin, pero deja elegir "para todos los usuarios" en un
; dialogo al inicio (ahi si eleva permisos).
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Se bundlea un runtime de Python embebido x64 + wheels compiladas (pandas,
; pillow, pywebview/pythonnet, uvicorn[standard]) — ya NO es independiente
; de arquitectura, por eso se exige x64compatible. Y como ahora SI puede
; instalarse en "Archivos de programa", hace falta el modo de 64 bits para
; que {commonpf} sea "C:\Program Files" y no "C:\Program Files (x86)".
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=MV_Amazon_FBA_IA_Setup
OutputDir=Output
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\assets\icon.ico
WizardStyle=modern
LicenseFile=EULA.txt
InfoBeforeFile=Bienvenida.txt
Compression=lzma2
SolidCompression=yes
DisableWelcomePage=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"

[Files]
; Lista EXPLICITA de inclusion (no un "todo menos..."): en Inno los patrones de
; Excludes sin barra solo matchean el nombre de archivo y con barra solo el
; final de la ruta — no son recursivos — asi que un exclude de carpetas anidadas
; se cuela silenciosamente. Con la lista explicita, nada que no deba
; distribuirse (installer/, mobile/, android/, .git/, .env, fba.db) puede
; terminar dentro del instalador por accidente.
; El panel LEGACY de Streamlit NO se distribuye. streamlit no se instala en el
; runtime del cliente (ver requirements-desktop.txt), asi que esos archivos
; eran peso muerto que ademas FALLABA si el cliente los tocaba:
;   dashboard_app.py  panel Streamlit viejo (88 KB)
;   styles.py         sistema de diseño de ese panel, solo lo usa el
;   core\i18n.py      "import streamlit as st" DURO -- reventaba al importarse
;   LEGACY_STREAMLIT.bat  lanzador que arrancaba algo que no esta instalado
; Verificado que app.py importa entero con streamlit BLOQUEADO: el programa
; que usa el cliente no lo necesita para nada.
Source: "..\*.py"; DestDir: "{app}"; Excludes: "dashboard_app.py,styles.py"; Flags: ignoreversion
Source: "..\*.bat"; DestDir: "{app}"; Excludes: "LEGACY_STREAMLIT.bat"; Flags: ignoreversion
; Documentacion: SOLO la que es para el cliente. Antes se empaquetaba "..\*.md"
; en bloque, lo que metia en el instalador CLAUDE.md (instrucciones internas de
; desarrollo) y PENDIENTES.md (bloqueadores internos, nombres de secrets, mapa
; de la infraestructura y el endpoint de licencia de dueño). Nada de eso tiene
; por que viajar a una maquina que compro el producto.
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CONEXIONES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\pitch_inversor_fba.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\agents\*"; DestDir: "{app}\agents"; Excludes: "*.pyc"; Flags: recursesubdirs ignoreversion
Source: "..\core\*"; DestDir: "{app}\core"; Excludes: "*.pyc,i18n.py"; Flags: recursesubdirs ignoreversion
Source: "..\data\*"; DestDir: "{app}\data"; Excludes: "*.pyc,*.csv"; Flags: recursesubdirs ignoreversion
Source: "..\n8n\*"; DestDir: "{app}\n8n"; Flags: recursesubdirs ignoreversion
; Panel web SaaS compilado (React -> frontend/dist, generado por `npm run build`
; en CI ANTES de compilar este instalador). Solo dist: ni node_modules ni src.
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend\dist"; Flags: recursesubdirs ignoreversion
; Runtime de Python embebido (descargado + con dependencias instaladas en
; CI, ver .github/workflows/windows-installer.yml). No se commitea al repo.
Source: "..\runtime\*"; DestDir: "{app}\runtime"; Flags: recursesubdirs ignoreversion
Source: "assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
; Licencia del build owner (interno): solo existe cuando CI compila el
; instalador del dueño (workflow_dispatch con owner=true, la escribe desde
; secrets). skipifsourcedoesntexist -> el instalador normal (clientes) se
; compila igual sin este archivo y arranca con la pantalla de activacion.
Source: "..\owner_licencia.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "Iniciar_Silencioso.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "App_Escritorio.vbs"; DestDir: "{app}"; Flags: ignoreversion
; App de escritorio (Electron). Trae su propio Chromium, asi que la ventana
; abre en cualquier Windows sin depender de WebView2. Va a {app}\desktop y
; main.js resuelve la raiz del programa subiendo dos niveles desde el .exe.
Source: "..\electron-dist\MV FBA IA-win32-x64\*"; DestDir: "{app}\desktop"; \
    Flags: recursesubdirs ignoreversion

[Icons]
; Acceso principal: la app de ESCRITORIO (Electron, ventana propia). Apunta al
; .exe directo -- antes iba a un .vbs que lanzaba un .bat oculto, y cuando algo
; fallaba ahi adentro no habia forma de enterarse.
Name: "{group}\{#MyAppName}"; Filename: "{app}\desktop\MV FBA IA.exe"; WorkingDir: "{app}\desktop"; Comment: "{#MyAppExeDescription}"
Name: "{group}\{#MyAppName} (modo navegador)"; Filename: "{app}\Iniciar_Silencioso.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"; Comment: "Abrir en el navegador (alternativa)"
Name: "{group}\Diagnostico"; Filename: "{app}\DIAGNOSTICO.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Verificar conexiones (Keepa, Claude, email)"; Filename: "{app}\CONECTAR.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\desktop\MV FBA IA.exe"; WorkingDir: "{app}\desktop"; Tasks: desktopicon; Comment: "{#MyAppExeDescription}"

[Run]
Filename: "{app}\desktop\MV FBA IA.exe"; WorkingDir: "{app}\desktop"; Description: "Abrir {#MyAppName} ahora"; Flags: postinstall skipifsilent nowait runasoriginaluser

[Code]
const
  DRIVE_FIXED = 3;   // disco interno: ni USB, ni red, ni CD, ni RAM disk

var
  BorrarDatosDelUsuario: Boolean;

// GetDriveType de la API de Windows. Sin esto habria que adivinar el tipo de
// unidad por el espacio libre, y el default podria caer en un pendrive o en
// una unidad de red mapeada -- que al desconectarse dejaria el programa roto.
function GetDriveType(lpRootPathName: String): Cardinal;
  external 'GetDriveTypeW@kernel32.dll stdcall';

// Primer disco INTERNO distinto de C: con espacio de sobra.
//
// POR QUE: el default caia siempre en C:, que es justo el disco que se llena
// -- ahi va tambien %LOCALAPPDATA%, donde el programa guarda la base (ver
// _dir_datos() en config.py). En una maquina con C: chico y D: grande, el
// instalador proponia el peor lugar posible y ya hubo un caso real de
// "database or disk is full" por eso.
//
// Se exigen 5 GB libres y DRIVE_FIXED: alcanza para descartar unidades de
// red, pendrives, lectoras y unidades no listas. Si no aparece ninguna, se
// vuelve al comportamiento de antes (C:). El usuario SIEMPRE puede cambiarlo:
// la pagina de destino se muestra igual (DisableDirPage=no).
function DiscoConEspacio(): String;
var
  i: Integer;
  Raiz: String;
  Libre, Total: Cardinal;
begin
  Result := '';
  for i := Ord('D') to Ord('Z') do
  begin
    Raiz := Chr(i) + ':\';
    if GetDriveType(Raiz) = DRIVE_FIXED then
      // True -> los valores vuelven en MB, asi que 5000 son 5 GB.
      if GetSpaceOnDisk(Raiz, True, Libre, Total) then
        if (Total > 0) and (Libre >= 5000) then
        begin
          Result := Raiz;
          Exit;
        end;
  end;
end;

// Carpeta propuesta al abrir la pagina de destino. Se calcula aca en vez de
// usar la constante autopf, que puede fallar y abortar la instalacion.
function CarpetaPorDefecto(Param: String): String;
var
  Disco: String;
begin
  Disco := DiscoConEspacio();
  if Disco <> '' then
    Result := Disco + 'MV FBA IA'
  else if IsAdminInstallMode then
    Result := ExpandConstant('{commonpf}\MV FBA IA')
  else
    Result := ExpandConstant('{localappdata}\Programs\MV FBA IA');
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  // SuppressibleMsgBox y no MsgBox: en una desinstalacion silenciosa
  // (/VERYSILENT) un MsgBox comun se queda esperando un clic que nunca llega y
  // el desinstalador cuelga. Asi, sin nadie mirando, responde IDNO: se borra el
  // programa pero los datos del usuario NO se tocan.
  BorrarDatosDelUsuario :=
    (SuppressibleMsgBox('¿Tambien queres borrar tu base de datos y tus claves ' +
            'guardadas (.env)? Si tocás "No", se desinstala el programa pero ' +
            'tus datos quedan en la carpeta por si reinstalás mas adelante.',
            mbConfirmation, MB_YESNO, IDNO) = IDYES);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir, DatosDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    // Los .pyc se generan al USAR el programa: el desinstalador de Inno solo
    // conoce los archivos que instalo, asi que sin esto la carpeta queda viva.
    //
    // El caso grave era runtime\: Python escribe __pycache__ adentro de
    // Lib\site-packages\ (pandas, fastapi, uvicorn, pillow...) en cuanto se
    // abre el programa una vez. Nada de eso figura en [Files], asi que
    // quedaban CIENTOS DE MB huerfanos y la carpeta "MV FBA IA" sobrevivia a
    // la desinstalacion. Igual pasaba con frontend\dist.
    //
    // Se borran por subcarpeta EXPLICITA, todas creadas por el instalador --
    // nunca un DelTree total de {app}: el usuario puede elegir cualquier
    // destino, y si eligio una carpeta compartida un borrado en bloque se
    // llevaria puesto lo que no es nuestro.
    DelTree(AppDir + '\desktop', True, True, True);
    DelTree(AppDir + '\runtime', True, True, True);
    DelTree(AppDir + '\frontend', True, True, True);
    DelTree(AppDir + '\agents', True, True, True);
    DelTree(AppDir + '\core', True, True, True);
    DelTree(AppDir + '\data', True, True, True);
    DelTree(AppDir + '\n8n', True, True, True);
    DelTree(AppDir + '\.streamlit', True, True, True);
    DelTree(AppDir + '\assets', True, True, True);
    DelTree(AppDir + '\__pycache__', True, True, True);
    // Recien ahora la carpeta deberia estar vacia: se saca si lo esta (los
    // dos False finales son a proposito -- no borra archivos ajenos).
    DelTree(AppDir, True, False, False);

    if BorrarDatosDelUsuario then
    begin
      // Los datos del usuario ya NO viven junto al programa (asi se puede
      // instalar en "Archivos de programa"): estan en %LOCALAPPDATA%, igual
      // que en _dir_datos() de config.py.
      DatosDir := ExpandConstant('{localappdata}\MV FBA IA');
      DeleteFile(DatosDir + '\fba.db');
      DeleteFile(DatosDir + '\.env');
      DelTree(DatosDir + '\cerebro_exports', True, True, True);
      DelTree(DatosDir, True, False, False);
    end;
  end;
end;
