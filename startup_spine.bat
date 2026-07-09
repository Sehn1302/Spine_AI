@echo off
title Spine AI — Startup
cd /d "%~dp0"

set OLLAMA_NO_GPU=
set OLLAMA_NUM_GPU=1

rem Wait for Ollama and audio drivers after boot
timeout /t 15 /nobreak >nul

"%~dp0.venv\Scripts\python.exe" "%~dp0spine\main.py" --visual
