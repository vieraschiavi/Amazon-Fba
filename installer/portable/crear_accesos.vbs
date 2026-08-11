' crear_accesos.vbs - Icono de Escritorio + grupo del Menu Inicio para la
' version PORTABLE (sin instalador) de MV FBA IA.
'
' POR QUE VBS Y NO POWERSHELL: el motivo de existir de la version portable es
' que hay empresas donde la politica de seguridad bloquea ejecutar .exe
' bajados de internet (SmartScreen/AppLocker), pero SI permiten .bat/.vbs.
' Muchas de esas mismas politicas tambien restringen powershell.exe (o su
' ExecutionPolicy). WScript.Shell crea accesos directos .lnk sin PowerShell y
' sin tocar el registro, con la misma tecnologia que ya usan
' Iniciar_Silencioso.vbs y App_Escritorio.vbs en el instalador de escritorio.
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
icono = carpeta & "\assets\icon.ico"
lanzador = carpeta & "\Iniciar_Silencioso.vbs"

Sub CrearAcceso(ruta, destino, comentario, iconoAcceso)
  Set lnk = shell.CreateShortcut(ruta)
  lnk.TargetPath = destino
  lnk.WorkingDirectory = carpeta
  lnk.IconLocation = iconoAcceso
  lnk.Description = comentario
  lnk.Save
End Sub

If Not fso.FileExists(lanzador) Then
  MsgBox "No encuentro " & lanzador & Chr(10) & _
    "Este script tiene que correr desde adentro de la carpeta MV FBA IA.", 48, "MV FBA IA"
  WScript.Quit 1
End If

escritorio = shell.SpecialFolders("Desktop")
menu = shell.SpecialFolders("Programs") & "\MV FBA IA"
If Not fso.FolderExists(menu) Then fso.CreateFolder(menu)

CrearAcceso escritorio & "\MV FBA IA.lnk", lanzador, "MV FBA IA (version portable, sin instalador)", icono
CrearAcceso menu & "\MV FBA IA.lnk", lanzador, "MV FBA IA (version portable, sin instalador)", icono
CrearAcceso menu & "\Diagnostico.lnk", carpeta & "\DIAGNOSTICO.bat", "Diagnostico de MV FBA IA", icono
CrearAcceso menu & "\Desinstalar MV FBA IA.lnk", carpeta & "\DESINSTALAR.bat", "Quitar los accesos directos de MV FBA IA", icono

MsgBox "Listo:" & Chr(10) & _
  "- Icono en el Escritorio" & Chr(10) & _
  "- Grupo ""MV FBA IA"" en el Menu Inicio" & Chr(10) & Chr(10) & _
  "Ya podes usar cualquiera de los dos para abrir el programa.", 64, "MV FBA IA"
