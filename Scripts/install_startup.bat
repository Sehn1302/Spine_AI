@echo off
title Install Spine Startup
call "%~dp0_common.bat"

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\Spine_AI_Startup.vbs"
set "OLD=%STARTUP%\Spine_AI_Startup.bat"

if exist "%OLD%" del "%OLD%"

(
echo ' Spine AI — hidden startup ^(no command windows^)
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%ROOT%"
echo WshShell.Run "%ROOT%\Scripts\startup_spine.bat", 0, False
) > "%VBS%"

echo.
echo Spine will start silently when you log in.
echo   - No command windows
echo   - Small orb appears after ~30 seconds
echo   - Say "Spine, wake up" to activate
echo.
echo Installed: %VBS%
echo To remove: run Scripts\uninstall_startup.bat
echo.
pause
