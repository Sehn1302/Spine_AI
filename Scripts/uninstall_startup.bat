@echo off
title Uninstall Spine Startup
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Spine_AI_Startup.bat"
if exist "%LINK%" (
    del "%LINK%"
    echo Spine startup removed.
) else (
    echo Spine startup was not installed.
)
pause
