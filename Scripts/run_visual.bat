@echo off
call "%~dp0_common.bat"
title Spine AI — Visual
echo Starting Spine (orb + voice)...
"%PYTHON%" "%MAIN%" --visual
pause
