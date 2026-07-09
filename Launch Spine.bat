@echo off
title Spine AI
cd /d "%~dp0"

if not exist ".spine_installed" (
    echo Spine is not installed yet. Running installer...
    call "%~dp0Install Spine.bat"
    exit /b
)

:menu
cls
echo.
echo  ================================================================
echo     S P I N E   —   Personal AI Assistant
echo  ================================================================
echo.
echo    1.  Launch assistant  (orb + voice — recommended)
echo    2.  Voice mode only
echo    3.  Text mode
echo    4.  Start on Windows login
echo    5.  Re-run installer
echo    6.  Exit
echo.
set /p choice="  Select [1-6]: "

if "%choice%"=="1" call "%~dp0Scripts\run_visual.bat" & goto menu
if "%choice%"=="2" call "%~dp0Scripts\run_voice.bat" & goto menu
if "%choice%"=="3" call "%~dp0Scripts\run_text.bat" & goto menu
if "%choice%"=="4" call "%~dp0Scripts\install_startup.bat" & goto menu
if "%choice%"=="5" call "%~dp0Install Spine.bat" & goto menu
if "%choice%"=="6" exit /b
goto menu
