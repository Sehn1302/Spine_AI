@echo off
call "%~dp0_common.bat"
set OLLAMA_NO_GPU=
set OLLAMA_NUM_GPU=1
timeout /t 20 /nobreak >nul
"%PYTHONW%" "%MAIN%" --visual --startup
