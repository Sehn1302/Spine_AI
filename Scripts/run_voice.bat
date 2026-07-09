@echo off
call "%~dp0_common.bat"
title Spine AI — Voice
echo Starting Spine (voice mode)...
"%PYTHON%" "%MAIN%" --voice
pause
