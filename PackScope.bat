@echo off
setlocal
cd /d "%~dp0"

set "VENV=.venv"
set "PY=%VENV%\Scripts\python.exe"

if not exist "%PY%" (
    echo First run: setting up the environment ^(this happens only once^)...
    where py >nul 2>nul && ( py -3 -m venv "%VENV%" ) || ( python -m venv "%VENV%" )
    if not exist "%PY%" (
        echo.
        echo ERROR: could not create the virtual environment.
        echo Make sure Python 3.11+ is installed and on PATH.
        pause
        exit /b 1
    )
    "%PY%" -m pip install --upgrade pip >nul
    "%PY%" -m pip install -r requirements.txt
)

"%PY%" run.py
if errorlevel 1 pause
