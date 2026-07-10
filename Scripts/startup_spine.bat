@echo off
REM Silent startup launcher — used by Windows login VBS (sets GPU/CUDA PATH).
cd /d "%~dp0"
call "%~dp0_common.bat"
"%PYTHONW%" "%MAIN%" --boot --visual
