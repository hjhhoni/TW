@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo    TW Workflow Platform  -  One-Click Start
echo ============================================================
echo.

REM ---------- 1. Check Python ----------
where python >nul 2>nul
if errorlevel 1 (
    echo [X] python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)
echo [OK] Python ready

REM ---------- 2. Backend dependencies ----------
python -c "import fastapi,uvicorn,playwright,apscheduler,httpx,pydantic_settings" >nul 2>nul
if errorlevel 1 (
    echo [..] First run: installing backend dependencies...
    python -m pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo [X] Backend install failed. Check network / pip mirror.
        pause
        exit /b 1
    )
) else (
    echo [OK] Backend dependencies ready
)

REM ---------- 3. Playwright chromium (marker avoids re-download) ----------
if not exist "backend\data\.chromium_ok" (
    echo [..] First run: downloading chromium ~150MB, once only...
    python -m playwright install chromium
    if errorlevel 1 (
        echo [X] chromium download failed. Try later: python -m playwright install chromium
        pause
        exit /b 1
    )
    echo.> "backend\data\.chromium_ok"
) else (
    echo [OK] Browser kernel ready
)

REM ---------- 4. Frontend ----------
where npm >nul 2>nul
if errorlevel 1 (
    echo [!] npm not found, skip frontend build. Backend still works.
) else (
    if not exist "frontend\node_modules" (
        echo [..] First run: installing frontend dependencies...
        pushd frontend
        call npm install --no-audit --no-fund
        if errorlevel 1 ( echo [X] Frontend install failed & popd & pause & exit /b 1 )
        popd
    )
    if not exist "frontend\dist\index.html" (
        echo [..] First run: building frontend...
        pushd frontend
        call npm run build
        if errorlevel 1 ( echo [X] Frontend build failed & popd & pause & exit /b 1 )
        popd
    )
    echo [OK] Frontend ready
)

REM ---------- 5. Start ----------
echo.
echo ============================================================
echo    All ready. Starting server...
echo    URL: http://localhost:8000   (browser opens automatically)
echo    Stop: press Ctrl+C in this window
echo ============================================================
echo.

REM open browser after 4s (separate process, won't block server)
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8000"

python backend\run.py

echo.
echo Server stopped.
pause
endlocal
