; MV_Amazon_FBA_IA.iss — Instalador profesional (Inno Setup) de MV FBA IA.
;
; Como compilar (en Windows, con Inno Setup 6 — gratis, jrsoftware.org/isinfo.php):
;   1. Instala Inno Setup 6.
;   2. Abri este archivo con el editor de Inno Setup (o doble clic).
;   3. Apreta Build > Compile (F9). El instalador queda en installer\Output\.
;   O desde la consola: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" MV_Amazon_FBA_IA.iss
;
; Se instala en el perfil del usuario (sin pedir permisos de administrador) para
; que el panel pueda escribir su base de datos y su .env sin friccion de UAC.

#define MyAppName "MV FBA IA"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "MV FBA IA"
#define MyAppExeDescription "Cockpit inteligente para tu negocio Amazon FBA"

[Setup]
AppId={{8F2C1A6E-7B4D-4E1A-9C3F-2D8E5A6B7C90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments={#MyAppExeDescription}
DefaultDirName={localappdata}\Programs\MV FBA IA
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
; Se bundlea un runtime de Python embebido x64 + wheels compiladas (pandas,
; pillow, pywebview/pythonnet, uvicorn[standard]) — ya NO es independiente
; de arquitectura. No hace falta ArchitecturesInstallIn64BitMode porque se
; instala en {localappdata} (sin tocar Program Files ni el registro de
; 64 bits), pero se exige x64compatible para evitar instalar en un Windows
; de 32 bits donde el runtime embebido no arrancaria.
ArchitecturesAllowed=x64compatible
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
Source: "..\*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\pitch_inversor_fba.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\agents\*"; DestDir: "{app}\agents"; Excludes: "*.pyc"; Flags: recursesubdirs ignoreversion
Source: "..\core\*"; DestDir: "{app}\core"; Excludes: "*.pyc"; Flags: recursesubdirs ignoreversion
Source: "..\data\*"; DestDir: "{app}\data"; Excludes: "*.pyc,*.csv"; Flags: recursesubdirs ignoreversion
Source: "..\n8n\*"; DestDir: "{app}\n8n"; Flags: recursesubdirs ignoreversion
Source: "..\.streamlit\*"; DestDir: "{app}\.streamlit"; Flags: recursesubdirs ignoreversion
; Panel web SaaS compilado (React -> frontend/dist, generado por `npm run build`
; en CI ANTES de compilar este instalador). Solo dist: ni node_modules ni src.
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend\dist"; Flags: recursesubdirs ignoreversion
; Runtime de Python embebido (descargado + con dependencias instaladas en
; CI, ver .github/workflows/windows-installer.yml). No se commitea al repo.
Source: "..\runtime\*"; DestDir: "{app}\runtime"; Flags: recursesubdirs ignoreversion
Source: "assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "Iniciar_Silencioso.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "App_Escritorio.vbs"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Acceso principal: la app de ESCRITORIO (ventana nativa propia, sin navegador).
Name: "{group}\{#MyAppName}"; Filename: "{app}\App_Escritorio.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"; Comment: "{#MyAppExeDescription}"
Name: "{group}\{#MyAppName} (modo navegador)"; Filename: "{app}\Iniciar_Silencioso.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"; Comment: "Abrir en el navegador (alternativa)"
Name: "{group}\Diagnostico"; Filename: "{app}\DIAGNOSTICO.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Verificar conexiones (Keepa, Claude, email)"; Filename: "{app}\CONECTAR.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\App_Escritorio.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon; Comment: "{#MyAppExeDescription}"

[Run]
Filename: "{app}\App_Escritorio.vbs"; Description: "Abrir {#MyAppName} ahora"; Flags: postinstall skipifsilent nowait shellexec runasoriginaluser

[Code]
var
  BorrarDatosDelUsuario: Boolean;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  BorrarDatosDelUsuario :=
    (MsgBox('¿Tambien queres borrar tu base de datos y tus claves guardadas ' +
            '(.env)? Si tocás "No", se desinstala el programa pero tus datos ' +
            'quedan en la carpeta por si reinstalás mas adelante.',
            mbConfirmation, MB_YESNO) = IDYES);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDir: String;
begin
  if (CurUninstallStep = usPostUninstall) and BorrarDatosDelUsuario then
  begin
    AppDir := ExpandConstant('{app}');
    // Solo se borra lo que la instalacion NUNCA gestiono (generado en uso):
    // la base de datos, las claves y los .pyc. El resto del programa ya lo
    // quita el desinstalador automatico de Inno Setup.
    DeleteFile(AppDir + '\fba.db');
    DeleteFile(AppDir + '\.env');
    DelTree(AppDir + '\data\cerebro_exports', False, True, False);
    DelTree(AppDir + '\__pycache__', True, True, True);
    DelTree(AppDir + '\agents\__pycache__', True, True, True);
    DelTree(AppDir + '\core\__pycache__', True, True, True);
    DelTree(AppDir + '\data\__pycache__', True, True, True);
    DelTree(AppDir, True, False, False);
  end;
end;
