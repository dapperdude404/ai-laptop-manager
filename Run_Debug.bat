@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run Start_Laptop_Manager.bat to set up dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
  echo.
  echo The application stopped with an error. You can copy the details above.
)
pause
