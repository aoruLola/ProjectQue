@echo off
setlocal

cd /d "%~dp0"

set "MODEL_ARG="
if not "%~1"=="" set "MODEL_ARG=--model %~1"
set "INTERACTIVE_FLAG=--interactive"
if /I "%~2"=="--ai-only" set "INTERACTIVE_FLAG="

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Python environment is not initialized.
  echo [ERROR] Please run init_maque.bat first.
  exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

python -c "import openai,rich" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Dependencies are missing in .venv.
  echo [ERROR] Please run init_maque.bat first.
  exit /b 1
)

echo [INFO] Runtime config (.env / env vars) will be loaded by the app.

if not exist "logs" mkdir logs

if "%MODEL_ARG%"=="" (
  echo [INFO] Starting game with model from .env / defaults
) else (
  echo [INFO] Starting game with explicit model: %~1
)
python -m maque play %MODEL_ARG% --log-dir .\logs %INTERACTIVE_FLAG%
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo [INFO] Game exited with code: %EXIT_CODE%
exit /b %EXIT_CODE%

:fail
echo [ERROR] Startup failed.
exit /b 1

