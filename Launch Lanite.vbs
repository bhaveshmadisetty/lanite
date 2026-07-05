' Lanite Silent Launcher
' Runs main.py using pythonw.exe (no console window)
' Path is derived from this script's own location so it works no matter where
' the folder is placed.
Dim oShell, oFS, scriptDir
Set oShell = CreateObject("WScript.Shell")
Set oFS = CreateObject("Scripting.FileSystemObject")

' Folder containing this .vbs, then the "lanite" subfolder that holds main.py
scriptDir = oFS.BuildPath(oFS.GetParentFolderName(WScript.ScriptFullName), "lanite")

' Use pythonw.exe to suppress the black console window.
' Working directory is set to scriptDir so relative paths inside main.py resolve.
oShell.CurrentDirectory = scriptDir
oShell.Run "pythonw.exe """ & scriptDir & "\main.py""", 0, False

Set oShell = Nothing
Set oFS = Nothing
