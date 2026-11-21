@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>&1
  if %errorlevel% neq 0 (
    echo Python 3.10 or newer is required for the source version.
    echo Download from https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
  set "PYTHON=python"
)
if not exist ".venv\Scripts\pythonw.exe" (
  echo Creating a local environment and installing required libraries...
  %PYTHON% -m venv .venv
  if errorlevel 1 goto :error
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)
start "AI Laptop Manager" ".venv\Scripts\pythonw.exe" app.py
exit /b 0
:error
echo Setup failed. Check your internet connection and Python installation.
pause
exit /b 1
