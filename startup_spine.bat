@echo off
cd /d "%~dp0"

set OLLAMA_NO_GPU=
set OLLAMA_NUM_GPU=1

rem Wait for Ollama and audio drivers after boot
timeout /t 20 /nobreak >nul

rem Silent boot: orb only, sleeping until "Spine wake up"
"%~dp0.venv\Scripts\pythonw.exe" "%~dp0spine\main.py" --visual --startup
