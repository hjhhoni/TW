@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo    TW 工作流平台  -  一键启动
echo ============================================================
echo.

REM ---------- 1. 检查 Python ----------
where python >nul 2>nul
if errorlevel 1 (
    echo [X] 未找到 python，请先安装 Python 3.10+ 并加入 PATH。
    pause
    exit /b 1
)
for /f "delims=" %%v in ('python -c "import sys;print('%d.%d'%sys.version_info[:2])"') do set PYV=%%v
echo [OK] Python %PYV% 已就绪

REM ---------- 2. 后端依赖 ----------
python -c "import fastapi,uvicorn,playwright,apscheduler,httpx,pydantic_settings" >nul 2>nul
if errorlevel 1 (
    echo [..] 首次运行，安装后端依赖...
    python -m pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo [X] 后端依赖安装失败，请检查网络或 pip 源。
        pause
        exit /b 1
    )
) else (
    echo [OK] 后端依赖已就绪
)

REM ---------- 3. Playwright 浏览器内核（用标记文件避免重复安装）----------
if not exist "backend\data\.chromium_ok" (
    echo [..] 首次运行，下载浏览器内核 chromium（约 150MB，仅一次）...
    python -m playwright install chromium
    if errorlevel 1 (
        echo [X] chromium 下载失败，可稍后手动执行: python -m playwright install chromium
        pause
        exit /b 1
    )
    echo.> "backend\data\.chromium_ok"
) else (
    echo [OK] 浏览器内核已就绪
)

REM ---------- 4. 前端 ----------
where npm >nul 2>nul
if errorlevel 1 (
    echo [!] 未找到 npm，跳过前端构建（仅后端可用，或改用: cd frontend ^&^& npm run dev）
) else (
    if not exist "frontend\node_modules" (
        echo [..] 首次运行，安装前端依赖...
        pushd frontend
        call npm install --no-audit --no-fund
        if errorlevel 1 ( echo [X] 前端依赖安装失败 & popd & pause & exit /b 1 )
        popd
    )
    if not exist "frontend\dist\index.html" (
        echo [..] 首次运行，构建前端...
        pushd frontend
        call npm run build
        if errorlevel 1 ( echo [X] 前端构建失败 & popd & pause & exit /b 1 )
        popd
    )
    echo [OK] 前端已就绪
)

REM ---------- 5. 启动 ----------
echo.
echo ============================================================
echo    全部就绪，正在启动...
echo    地址: http://localhost:8000   （浏览器将自动打开）
echo    停止: 在本窗口按 Ctrl+C
echo ============================================================
echo.

REM 4 秒后自动打开浏览器（独立进程，不阻塞服务器）
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8000"

python backend\run.py

echo.
echo 服务已停止。
pause
endlocal
