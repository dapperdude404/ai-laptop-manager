@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run Start_Laptop_Manager.bat to install dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install "pyinstaller>=6,<8"
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name "AI_Laptop_Manager" app.py
if errorlevel 1 goto :error
echo.
echo Standalone app created at dist\AI_Laptop_Manager.exe
pause
exit /b 0
:error
echo Build failed. No executable was created.
pause
exit /b 1
