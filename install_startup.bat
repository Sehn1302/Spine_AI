@echo off
title Install Spine Startup
cd /d "%~dp0"

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set LINK=%STARTUP%\Spine_AI_Startup.bat

(
echo @echo off
echo cd /d "%~dp0"
echo call "%~dp0startup_spine.bat"
) > "%LINK%"

echo.
echo Spine will now start automatically when you log in to Windows.
echo   - Animated orb will appear
echo   - Spine will speak: "Good morning/afternoon/evening, Sir. I am online. How may I assist you?"
echo.
echo Installed to:
echo   %LINK%
echo.
echo To remove: run uninstall_startup.bat
echo.
pause
