@echo off
title Spine
cd /d "%~dp0"
call "%~dp0Scripts\_common.bat"
"%PYTHON%" "%MAIN%" --visual
