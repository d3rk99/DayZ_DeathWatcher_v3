@echo off
setlocal

set "PY_VERSION=3.11"
set "PY_LAUNCHER=py -%PY_VERSION%"
set "VENV_DIR=.venv"

where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher (py) not found. Please install Python %PY_VERSION% from https://www.python.org/downloads/windows/.
  exit /b 1
)

%PY_LAUNCHER% -c "import sys" >nul 2>&1
if errorlevel 1 (
  echo Python %PY_VERSION% not found. Attempting to install via winget...
  where winget >nul 2>&1
  if errorlevel 1 (
    echo winget not available. Please install Python %PY_VERSION% manually and re-run this script.
    exit /b 1
  )
  winget install --id Python.Python.%PY_VERSION% -e --source winget
  if errorlevel 1 (
    echo winget install failed. Please install Python %PY_VERSION% manually and re-run this script.
    exit /b 1
  )
  %PY_LAUNCHER% -c "import sys" >nul 2>&1
  if errorlevel 1 (
    echo Python %PY_VERSION% still not available. Please install it manually and re-run this script.
    exit /b 1
  )
)

if not exist "%VENV_DIR%\\Scripts\\python.exe" (
  %PY_LAUNCHER% -m venv "%VENV_DIR%"
)

set "VENV_PY=%VENV_DIR%\\Scripts\\python.exe"

"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r requirement.txt

start "Main Bot" /b "%VENV_PY%" main.py
"%VENV_PY%" death_watcher\\new_dayz_death_watcher.py

endlocal
