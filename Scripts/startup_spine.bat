@echo off
call "%~dp0_common.bat"
set OLLAMA_NO_GPU=
set OLLAMA_NUM_GPU=1

rem Kill duplicate Spine instances from previous boot
for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO LIST ^| findstr /I "PID:"') do (
  wmic process where "ProcessId=%%p" get CommandLine 2>nul | findstr /I "spine\\main.py" >nul && taskkill /PID %%p /F >nul 2>&1
)

rem Start Ollama brain
start "" "%LOCALAPPDATA%\Programs\Ollama\Ollama.exe" 2>nul

rem Wait for login + drivers + Ollama
timeout /t 35 /nobreak >nul

rem Launch Spine (venv only — never system python)
"%PYTHONW%" "%MAIN%" --visual --startup
