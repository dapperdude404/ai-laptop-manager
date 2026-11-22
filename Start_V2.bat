@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv || (echo Install Python 3.10+ & pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt || (pause & exit /b 1)
".venv\Scripts\python.exe" ai_laptop_manager_v2.py
if errorlevel 1 pause
