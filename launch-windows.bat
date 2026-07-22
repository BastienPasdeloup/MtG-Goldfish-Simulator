@echo off
REM ==========================================================================
REM  MtG Goldfish Simulator - one-click launcher for Windows.
REM
REM  Double-click this file to start the simulator. It opens in your web
REM  browser automatically. Keep this window open while you use the app;
REM  close it (or press Ctrl+C) to stop the simulator.
REM
REM  If you have not installed it yet, double-click "install-windows.bat" first.
REM ==========================================================================
setlocal

REM Always work from the project folder, wherever this script was launched from.
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

where uv >nul 2>nul
if not %errorlevel%==0 (
  echo [X] uv is not installed yet.
  echo     Please double-click "install-windows.bat" first, then try again.
  echo.
  pause
  exit /b 1
)

set "URL=http://127.0.0.1:8000"

echo ==================================================
echo   Starting the MtG Goldfish Simulator
echo ==================================================
echo.
echo   Your browser will open at %URL% shortly.
echo   Keep this window open while you use the app.
echo   To stop the simulator: close this window or press Ctrl+C.
echo.

REM Open the browser once the server is responding. This waits in the
REM background (up to ~3 minutes) so it also works on the first, slower launch.
start "" /b powershell -ExecutionPolicy Bypass -c "for($i=0;$i -lt 180;$i++){Start-Sleep 1; try{ Invoke-WebRequest -UseBasicParsing '%URL%' -TimeoutSec 2 >$null; Start-Process '%URL%'; break }catch{} }"

uv run mtg-goldfish
