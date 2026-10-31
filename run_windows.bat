@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [AETHERIA] Creating a Python virtual environment...
    py -3.11 -m venv .venv 2>nul
    if errorlevel 1 py -3 -m venv .venv
    if errorlevel 1 (
        echo Install Python 3.11 or 3.12 from python.org and rerun.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependencies could not be installed. Check your internet connection.
        pause
        exit /b 1
    )
)
echo [AETHERIA] Launching Aetheria NEXT...
".venv\Scripts\python.exe" aetheria_synth.py
if errorlevel 1 (
    echo Aetheria closed with an error. See logs above.
    pause
)
