@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================
REM GymClaw 停止脚本 (Windows)
REM ============================================================

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

set "PID_DIR=%PROJECT_ROOT%.pids"
set "BACKEND_PID_FILE=%PID_DIR%\backend.pid"
set "FRONTEND_PID_FILE=%PID_DIR%\frontend.pid"

echo Stopping GymClaw...

REM --- 停止后端 ---
if exist "%BACKEND_PID_FILE%" (
    set /p BACKEND_PID=<"%BACKEND_PID_FILE%"
    tasklist /FI "PID eq !BACKEND_PID!" 2>nul | find "!BACKEND_PID!" >nul
    if !errorlevel!==0 (
        taskkill /PID !BACKEND_PID! /F >nul 2>&1
        echo   Backend stopped ^(PID: !BACKEND_PID!^)
    ) else (
        echo   Backend already stopped
    )
    del /f "%BACKEND_PID_FILE%" 2>nul
) else (
    echo   Backend: no PID file
)

REM --- 停止前端 ---
if exist "%FRONTEND_PID_FILE%" (
    set /p FRONTEND_PID=<"%FRONTEND_PID_FILE%"
    tasklist /FI "PID eq !FRONTEND_PID!" 2>nul | find "!FRONTEND_PID!" >nul
    if !errorlevel!==0 (
        taskkill /PID !FRONTEND_PID! /F >nul 2>&1
        echo   Frontend stopped ^(PID: !FRONTEND_PID!^)
    ) else (
        echo   Frontend already stopped
    )
    del /f "%FRONTEND_PID_FILE%" 2>nul
) else (
    echo   Frontend: no PID file
)

REM 额外清理：杀死可能残留的 uvicorn 进程
tasklist /FI "IMAGENAME eq python.exe" /FO TABLE /NH 2>nul | find "uvicorn" >nul
if !errorlevel!==0 (
    echo   Cleaning up remaining uvicorn processes...
    taskkill /FI "WINDOWTITLE eq uvicorn*" /F >nul 2>&1
)

echo Done.
