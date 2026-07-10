@echo off
title Install Spine Startup
cd /d "%~dp0"
call "%~dp0Scripts\_common.bat"

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\Spine_AI_Startup.vbs"
set "LAUNCHER=%ROOT%\Scripts\startup_spine.bat"

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
echo WScript.Sleep 3000
echo launcher = "%LAUNCHER%"
echo WshShell.Run """""" ^& launcher ^& """""", 0, False
) > "%VBS%"

echo.
echo Spine will start automatically when you log in.
echo   %VBS%
echo   Uses: %LAUNCHER%
echo.
pause
