@echo off
title Spine AI
cd /d "%~dp0"

rem Use CPU if GPU CUDA errors occur (remove next line after GPU driver fix)
set OLLAMA_NUM_GPU=0

echo Starting Spine...
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0spine\main.py"
pause
