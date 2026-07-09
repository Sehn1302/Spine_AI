@echo off
set "ROOT=%~dp0.."
cd /d "%ROOT%"
set OLLAMA_NO_GPU=
set OLLAMA_NUM_GPU=1
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "PYTHONW=%ROOT%\.venv\Scripts\pythonw.exe"
set "MAIN=%ROOT%\spine\main.py"
set "CUDA_BIN=%ROOT%\.venv\Lib\site-packages\nvidia\cublas\bin;%ROOT%\.venv\Lib\site-packages\nvidia\cudnn\bin;%ROOT%\.venv\Lib\site-packages\nvidia\cuda_nvrtc\bin"
set "PATH=%CUDA_BIN%;%PATH%"
