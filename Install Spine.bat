@echo off
title Spine AI — Installer
cd /d "%~dp0"
echo.
echo  ================================================================
echo     S P I N E   —   Installing your personal AI assistant
echo  ================================================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py -3.11 "%~dp0installer\setup.py"
) else (
    python "%~dp0installer\setup.py"
)

if %errorlevel% neq 0 (
    echo.
    echo Installation encountered an error. See messages above.
    pause
    exit /b 1
)

echo.
echo Installation complete. Use "Launch Spine.bat" to start.
pause
