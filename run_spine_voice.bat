@echo off
title Spine AI — Voice Mode
cd /d "%~dp0"

rem Override CPU-only flags so Ollama can use the NVIDIA GPU
set OLLAMA_NO_GPU=
set OLLAMA_NUM_GPU=1

echo Starting Spine Voice Mode...
echo.
"%~dp0.venv\Scripts\python.exe" "%~dp0spine\main.py" --voice
pause
