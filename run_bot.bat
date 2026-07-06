@echo off
setlocal

set "PY_VERSION=3.11"
set "PY_LAUNCHER=py -%PY_VERSION%"
set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

pushd "%~dp0"

where py >nul 2>&1
if errorlevel 1 goto python_missing

%PY_LAUNCHER% -c "import sys" >nul 2>&1
if errorlevel 1 goto install_python

if not exist "config.json" goto config_missing

goto setup_venv

:python_missing
echo Python launcher (py) not found. Please install Python %PY_VERSION% from https://www.python.org/downloads/windows/.
exit /b 1

:install_python
echo Python %PY_VERSION% not found. Please install Python %PY_VERSION% from https://www.python.org/downloads/windows/ and re-run this script.
exit /b 1

:config_missing
echo config.json not found.
echo Copy config.example.json to config.json, edit your Discord IDs and server paths, then re-run this script.
exit /b 1

:setup_venv
if not exist "%VENV_PY%" %PY_LAUNCHER% -m venv "%VENV_DIR%"

"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r requirement.txt

for /f "usebackq delims=" %%S in (`"%VENV_PY%" launcher_check.py`) do (
  echo %%S
  if "%%S"=="SYNC_ENABLED=1" set "SYNC_ENABLED=1"
  if "%%S"=="SYNC_ENABLED=0" set "SYNC_ENABLED=0"
)
if errorlevel 1 (
  echo Configuration validation failed. Fix config.json and re-run this script.
  exit /b 1
)

start "Main Bot" /d "%~dp0" "%VENV_PY%" main.py
start "Death Watcher" /d "%~dp0death_watcher" "%VENV_PY%" new_dayz_death_watcher.py
if "%SYNC_ENABLED%"=="1" start "Syncer" /d "%~dp0" cmd /k ""%VENV_PY%" syncer.py"
start "WebUI" /d "%~dp0" cmd /k ""%VENV_PY%" web_ui.py"

popd
endlocal
