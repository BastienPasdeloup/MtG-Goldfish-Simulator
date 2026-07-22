@echo off
REM ==========================================================================
REM  MtG Goldfish Simulator - one-click installer for Windows.
REM
REM  Double-click this file to set everything up. It installs the small "uv"
REM  tool (which fetches the right Python and every dependency for you) and
REM  downloads everything the simulator needs. You only need to run this once.
REM
REM  If Windows shows a blue "Windows protected your PC" box, click
REM  "More info" then "Run anyway".
REM ==========================================================================
setlocal

REM Always work from the project folder, wherever this script was launched from.
cd /d "%~dp0"

REM Make sure uv's install location is on PATH for this session.
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo ==================================================
echo   Installing the MtG Goldfish Simulator
echo ==================================================
echo.

REM ---------------------------------------------------------------- step 1: uv
where uv >nul 2>nul
if %errorlevel%==0 (
  echo ==^> uv is already installed. Skipping.
) else (
  echo ==^> Installing uv ^(this fetches Python + dependencies for you^)...
  powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

where uv >nul 2>nul
if not %errorlevel%==0 (
  echo.
  echo [X] Could not find "uv" after installing it.
  echo     Please close this window, open it again, and run this installer once more.
  echo.
  pause
  exit /b 1
)

REM --------------------------------------------- step 2: Python + dependencies
echo.
echo ==^> Downloading Python and all dependencies...
echo     ^(The first time this can take a minute or two - please be patient.^)
echo.
uv sync
if not %errorlevel%==0 (
  echo.
  echo [X] Something went wrong while downloading dependencies.
  echo.
  pause
  exit /b 1
)

echo.
echo ==================================================
echo   [OK]  All done!
echo ==================================================
echo.
echo   To start the simulator, double-click:
echo       launch-windows.bat
echo.
pause
