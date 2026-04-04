@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================
REM GymClaw 启动脚本 (Windows)
REM 后台运行，PID 写入文件，支持 start.bat stop 关闭
REM ============================================================

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

set "PID_DIR=%PROJECT_ROOT%.pids"
set "BACKEND_PID_FILE=%PID_DIR%\backend.pid"
set "FRONTEND_PID_FILE=%PID_DIR%\frontend.pid"
set "BACKEND_LOG=%PROJECT_ROOT%logs\backend.log"
set "FRONTEND_LOG=%PROJECT_ROOT%logs\frontend.log"

if not exist "%PID_DIR%" mkdir "%PID_DIR%"
if not exist "%PROJECT_ROOT%logs" mkdir "%PROJECT_ROOT%logs"

REM 支持 start.bat stop 快捷关闭
if "%1"=="stop" (
    call "%PROJECT_ROOT%stop.bat"
    exit /b 0
)

REM 支持 start.bat status 查看状态
if "%1"=="status" (
    echo === GymClaw Status ===
    if exist "%BACKEND_PID_FILE%" (
        set /p BACKEND_PID=<"%BACKEND_PID_FILE%"
        tasklist /FI "PID eq !BACKEND_PID!" 2>nul | find "!BACKEND_PID!" >nul
        if !errorlevel!==0 (
            echo Backend:  RUNNING ^(PID: !BACKEND_PID!^) on :8000
        ) else (
            echo Backend:  STOPPED
        )
    ) else (
        echo Backend:  STOPPED
    )
    if exist "%FRONTEND_PID_FILE%" (
        set /p FRONTEND_PID=<"%FRONTEND_PID_FILE%"
        tasklist /FI "PID eq !FRONTEND_PID!" 2>nul | find "!FRONTEND_PID!" >nul
        if !errorlevel!==0 (
            echo Frontend: RUNNING ^(PID: !FRONTEND_PID!^) on :3000
        ) else (
            echo Frontend: STOPPED
        )
    ) else (
        echo Frontend: STOPPED
    )
    exit /b 0
)

REM 支持 start.bat restart 重启
if "%1"=="restart" (
    echo Restarting GymClaw...
    call "%PROJECT_ROOT%stop.bat"
    timeout /t 2 /nobreak >nul
)

echo === Starting GymClaw v5.11.0 ===
echo.

REM --- 启动后端 ---
if exist "%BACKEND_PID_FILE%" (
    set /p BACKEND_PID=<"%BACKEND_PID_FILE%"
    tasklist /FI "PID eq !BACKEND_PID!" 2>nul | find "!BACKEND_PID!" >nul
    if !errorlevel!==0 (
        echo [SKIP] Backend is already running ^(PID: !BACKEND_PID!^)
        goto :start_frontend
    ) else (
        del /f "%BACKEND_PID_FILE%" 2>nul
    )
)

echo [START] Starting backend on :8000 ...
start /b "" "%PROJECT_ROOT%venv\Scripts\python.exe" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level info >> "%BACKEND_LOG%" 2>&1
timeout /t 2 /nobreak >nul

REM 查找 uvicorn 进程 PID
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO TABLE /NH 2^>nul ^| find "python.exe"') do (
    set "BACKEND_PID=%%a"
)
if defined BACKEND_PID (
    echo !BACKEND_PID!> "%BACKEND_PID_FILE%"
    echo [OK]    Backend started ^(PID: !BACKEND_PID!^)
) else (
    echo [ERROR] Backend failed to start. Check %BACKEND_LOG%
    type "%BACKEND_LOG%"
    exit /b 1
)

:start_frontend
REM --- 启动前端 ---
if exist "%FRONTEND_PID_FILE%" (
    set /p FRONTEND_PID=<"%FRONTEND_PID_FILE%"
    tasklist /FI "PID eq !FRONTEND_PID!" 2>nul | find "!FRONTEND_PID!" >nul
    if !errorlevel!==0 (
        echo [SKIP] Frontend is already running ^(PID: !FRONTEND_PID!^)
        goto :done
    ) else (
        del /f "%FRONTEND_PID_FILE%" 2>nul
    )
)

echo [START] Starting frontend on :3000 ...
cd /d "%PROJECT_ROOT%frontend"
start /b "" npm run dev >> "%FRONTEND_LOG%" 2>&1
cd /d "%PROJECT_ROOT%"
timeout /t 3 /nobreak >nul

for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq node.exe" /FO TABLE /NH 2^>nul ^| find "node.exe"') do (
    set "FRONTEND_PID=%%a"
)
if defined FRONTEND_PID (
    echo !FRONTEND_PID!> "%FRONTEND_PID_FILE%"
    echo [OK]    Frontend started ^(PID: !FRONTEND_PID!^)
) else (
    echo [ERROR] Frontend failed to start. Check %FRONTEND_LOG%
    type "%FRONTEND_LOG%"
    exit /b 1
)

:done
echo.
echo === GymClaw is running ===
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo Logs:
echo   Backend:  %BACKEND_LOG%
echo   Frontend: %FRONTEND_LOG%
echo.
echo Commands:
echo   start.bat status   - View status
echo   start.bat stop     - Stop services
echo   start.bat restart  - Restart services
echo   stop.bat           - Stop services
