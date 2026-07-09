@echo off
title Spine AI — Visual Mode
cd /d "%~dp0"

set OLLAMA_NO_GPU=
set OLLAMA_NUM_GPU=1

echo Starting Spine Visual Mode (orb + voice)...
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0spine\main.py" --visual
pause
