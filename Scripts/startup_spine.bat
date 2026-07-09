@echo off
call "%~dp0_common.bat"
set OLLAMA_NO_GPU=
set OLLAMA_NUM_GPU=1

powershell -WindowStyle Hidden -Command "if (Test-Path \"$env:LOCALAPPDATA\Programs\Ollama\Ollama.exe\") { Start-Process \"$env:LOCALAPPDATA\Programs\Ollama\Ollama.exe\" -WindowStyle Hidden }" 2>nul

"%PYTHONW%" "%MAIN%" --visual --startup
