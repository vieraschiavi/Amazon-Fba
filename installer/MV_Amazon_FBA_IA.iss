; MV_Amazon_FBA_IA.iss — Instalador profesional (Inno Setup) de MV Amazon FBA IA.
;
; Como compilar (en Windows, con Inno Setup 6 — gratis, jrsoftware.org/isinfo.php):
;   1. Instala Inno Setup 6.
;   2. Abri este archivo con el editor de Inno Setup (o doble clic).
;   3. Apreta Build > Compile (F9). El instalador queda en installer\Output\.
;   O desde la consola: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" MV_Amazon_FBA_IA.iss
;
; Se instala en el perfil del usuario (sin pedir permisos de administrador) para
; que el panel pueda escribir su base de datos y su .env sin friccion de UAC.

#define MyAppName "MV Amazon FBA IA"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MV Amazon FBA IA"
#define MyAppExeDescription "Cockpit inteligente para tu negocio Amazon FBA"

[Setup]
AppId={{8F2C1A6E-7B4D-4E1A-9C3F-2D8E5A6B7C90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments={#MyAppExeDescription}
DefaultDirName={localappdata}\Programs\MV Amazon FBA IA
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
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
Source: "..\*"; DestDir: "{app}"; Excludes: ".git\*,__pycache__\*,*\__pycache__\*,.env,fba.db,installer\*,mobile\*,*.pyc,.pytest_cache\*"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "Iniciar_Silencioso.vbs"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Iniciar_Silencioso.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"; Comment: "{#MyAppExeDescription}"
Name: "{group}\Diagnostico"; Filename: "{app}\DIAGNOSTICO.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Verificar conexiones (Keepa, Claude, email)"; Filename: "{app}\CONECTAR.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Iniciar_Silencioso.vbs"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon; Comment: "{#MyAppExeDescription}"

[Run]
Filename: "{app}\Iniciar_Silencioso.vbs"; Description: "Abrir {#MyAppName} ahora"; Flags: postinstall skipifsilent nowait shellexec runasoriginaluser

[Code]
var
  BorrarDatosDelUsuario: Boolean;
function PythonEncontrado(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/C where python >nul 2>nul', '', SW_HIDE,
                ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
  if not Result then
    Result := Exec('cmd.exe', '/C where py >nul 2>nul', '', SW_HIDE,
                  ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if not PythonEncontrado() then
    begin
      if MsgBox('No se detecto Python en este equipo.' + #13#10 +
                'MV Amazon FBA IA necesita Python 3.10 o superior para funcionar.' + #13#10 + #13#10 +
                'Se recomienda instalarlo ahora (tildá "Add python.exe to PATH" ' +
                'durante su instalacion) y despues abrir MV Amazon FBA IA normalmente.' +
                #13#10 + #13#10 + 'Queres abrir la pagina de descarga de Python?',
                mbConfirmation, MB_YESNO) = IDYES then
        ShellExec('open', 'https://www.python.org/downloads/', '', '', SW_SHOWNORMAL,
                  ewNoWait, ResultCode);
    end;
  end;
end;

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
