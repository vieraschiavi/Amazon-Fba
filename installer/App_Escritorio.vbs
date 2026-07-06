' App_Escritorio.vbs — Lanza la app de escritorio (ventana nativa) sin consola.
' Corre APP_ESCRITORIO.bat oculto: detecta Python, instala dependencias la
' primera vez y abre MV FBA IA en su propia ventana (desktop.py).
' Si algo falla, doble clic en APP_ESCRITORIO.bat muestra el detalle.
Set fso = CreateObject("Scripting.FileSystemObject")
carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = carpeta
shell.Run """" & carpeta & "\APP_ESCRITORIO.bat""", 0, False
