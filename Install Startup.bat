@echo off
title Install Spine Startup
cd /d "%~dp0"
call "%~dp0Scripts\_common.bat"

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\Spine_AI_Startup.vbs"

(
echo ' Spine — start on Windows login
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo root = "%ROOT%"
echo WshShell.CurrentDirectory = root
echo ollama = CreateObject^("WScript.Shell"^).ExpandEnvironmentStrings^("%%LOCALAPPDATA%%"^) ^& "\Programs\Ollama\Ollama.exe"
echo Set fso = CreateObject^("Scripting.FileSystemObject"^)
echo If fso.FileExists^(ollama^) Then
echo     WshShell.Run """""" ^& ollama ^& """""", 0, False
echo End If
echo py = root ^& "\.venv\Scripts\pythonw.exe"
echo main = root ^& "\spine\main.py"
echo WshShell.Run """""" ^& py ^& """ """ ^& main ^& """ --visual", 0, False
) > "%VBS%"

echo.
echo Spine will start automatically when you log in.
echo   %VBS%
echo.
pause
