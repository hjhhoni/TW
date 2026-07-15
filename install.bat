@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo    TW Workflow Platform  -  First-Time Install
echo    (run this once; afterwards just double-click start.bat)
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [X] python not found. Install Python 3.10+ from https://python.org and re-run.
    pause
    exit /b 1
)
echo [1/4] Installing backend dependencies...
python -m pip install -r backend\requirements.txt
if errorlevel 1 ( echo [X] backend install failed & pause & exit /b 1 )

echo.
echo [2/4] Downloading browser kernel chromium ~150MB...
python -m playwright install chromium
if errorlevel 1 ( echo [!] chromium download failed, will retry on start ) else ( echo.> "backend\data\.chromium_ok" )

echo.
where npm >nul 2>nul
if errorlevel 1 (
    echo [3/4] npm not found, skipping frontend build.
    echo     If frontend\dist is missing, install Node.js from https://nodejs.org and re-run,
    echo     or the backend will serve a "please build frontend" notice.
) else (
    echo [3/4] Installing frontend dependencies and building...
    pushd frontend
    call npm install --no-audit --no-fund
    if errorlevel 1 ( echo [X] npm install failed & popd & pause & exit /b 1 )
    call npm run build
    if errorlevel 1 ( echo [X] frontend build failed & popd & pause & exit /b 1 )
    popd
)

echo.
echo [4/4] Done.
echo ============================================================
echo    Install complete. Now double-click  start.bat  to launch.
echo ============================================================
pause
endlocal
