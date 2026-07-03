' Iniciar_Silencioso.vbs — Lanza INICIAR.bat sin ventana de consola visible.
' Usado por el acceso directo del instalador para una experiencia de "app" real
' (doble clic -> el panel abre en el navegador, sin la consola negra de fondo).
' Si algo falla, doble clic en INICIAR.bat directamente muestra el detalle.
Set fso = CreateObject("Scripting.FileSystemObject")
carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = carpeta
shell.Run """" & carpeta & "\INICIAR.bat""", 0, False
