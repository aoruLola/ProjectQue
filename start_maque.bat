@echo off
setlocal

cd /d "%~dp0"

set "DEFAULT_MODEL=gpt-4.1-mini"
if not "%MAQUE_MODEL%"=="" set "DEFAULT_MODEL=%MAQUE_MODEL%"

set "MODEL=%DEFAULT_MODEL%"
if not "%~1"=="" set "MODEL=%~1"
set "INTERACTIVE_FLAG=--interactive"
if /I "%~2"=="--ai-only" set "INTERACTIVE_FLAG="

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

if "%OPENAI_API_KEY%"=="" (
  echo [WARN] OPENAI_API_KEY is not set. LLM agents will fallback to rule-based decisions.
)
if not "%MAQUE_OPENAI_BASE_URL%"=="" (
  echo [INFO] Using MAQUE_OPENAI_BASE_URL=%MAQUE_OPENAI_BASE_URL%
)

if not exist "logs" mkdir logs

echo [INFO] Starting game with model: %MODEL%
python -m maque play --model %MODEL% --log-dir .\logs %INTERACTIVE_FLAG%
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo [INFO] Game exited with code: %EXIT_CODE%
exit /b %EXIT_CODE%

:fail
echo [ERROR] Startup failed.
exit /b 1

