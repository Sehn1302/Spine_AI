@echo off
title Uninstall Spine Startup
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

if exist "%STARTUP%\Spine_AI_Startup.vbs" del "%STARTUP%\Spine_AI_Startup.vbs"
if exist "%STARTUP%\Spine_AI_Startup.bat" del "%STARTUP%\Spine_AI_Startup.bat"

echo Spine startup removed.
pause
