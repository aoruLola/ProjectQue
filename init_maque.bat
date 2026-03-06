@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

echo [INFO] Installing dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [OK] Initialization complete.
echo [OK] You can now run start_maque.bat
exit /b 0

:fail
echo [ERROR] Initialization failed.
exit /b 1

