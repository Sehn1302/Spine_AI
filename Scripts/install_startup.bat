@echo off
title Install Spine Startup
call "%~dp0_common.bat"

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\Spine_AI_Startup.vbs"
set "OLD=%STARTUP%\Spine_AI_Startup.bat"

if exist "%OLD%" del "%OLD%"

(
echo ' Spine AI — hidden startup
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
echo WshShell.Run """""" ^& py ^& """ """ ^& main ^& """ --visual --startup", 0, False
) > "%VBS%"

echo.
echo Spine startup installed — silent, no command windows.
echo   Orb appears ~30s after login. Say "Spine, wake up".
echo.
echo   %VBS%
echo.
pause
