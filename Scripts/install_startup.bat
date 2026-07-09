@echo off
title Install Spine Startup
call "%~dp0_common.bat"

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LINK=%STARTUP%\Spine_AI_Startup.bat"

(
echo @echo off
echo call "%ROOT%\Scripts\startup_spine.bat"
) > "%LINK%"

echo.
echo Spine will start automatically when you log in.
echo   - Orb appears silently until you say "Spine, wake up"
echo.
echo Installed: %LINK%
echo To remove: run Scripts\uninstall_startup.bat
echo.
pause
