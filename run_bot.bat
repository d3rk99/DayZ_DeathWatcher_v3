@echo off
setlocal enabledelayedexpansion

set "PY_VERSION=3.11"

where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher (py) not found. Please install Python %PY_VERSION% from https://www.python.org/downloads/windows/.
  exit /b 1
)

py -%PY_VERSION% -c "import sys" >nul 2>&1
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
  py -%PY_VERSION% -c "import sys" >nul 2>&1
  if errorlevel 1 (
    echo Python %PY_VERSION% still not available. Please install it manually and re-run this script.
    exit /b 1
  )
)

if not exist .venv (
  py -%PY_VERSION% -m venv .venv
)

call .venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirement.txt

start "Main Bot" /b python main.py
python death_watcher\new_dayz_death_watcher.py

endlocal
