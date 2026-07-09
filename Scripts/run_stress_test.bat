@echo off
cd /d "%~dp0.."
call .venv\Scripts\python.exe Scripts\stress_test.py
pause
