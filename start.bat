@echo off
title MiroFish Mini
echo ========================================
echo   MIROFISH Mini - Starting...
echo ========================================
echo.

:: Kill any existing instances
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start backend
echo [1/2] Starting backend...
start /B "MiroFish-Backend" cmd /c "cd /d %~dp0backend && python run.py"

:: Wait for backend to be healthy
echo       Waiting for backend...
:wait_backend
timeout /t 1 /nobreak >nul
curl -s http://localhost:8000/api/health 2>nul | findstr "healthy" >nul
if errorlevel 1 goto wait_backend
echo       Backend ready on http://localhost:8000

:: Start frontend
echo [2/2] Starting frontend...
start "MiroFish-Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

:: Wait for frontend
timeout /t 3 /nobreak >nul
echo       Frontend ready on http://localhost:5173
echo.
echo ========================================
echo   MiroFish Mini is running!
echo   Open http://localhost:5173
echo ========================================
echo.

:: Open browser
start http://localhost:5173
