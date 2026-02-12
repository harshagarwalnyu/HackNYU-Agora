@echo off
echo ===================================================
echo Starting Agora Local Development Environment
echo ===================================================

:: 1. Start Backend in a new window
echo Starting Backend (Port 8000)...
start "Agora Backend" cmd /k "cd backend && set QDRANT_URL=:memory: && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend to initialize
timeout /t 5 >nul

:: 2. Start Frontend in a new window
echo Starting Frontend (Port 3000)...
start "Agora Frontend" cmd /k "cd frontendOther && pnpm dev"

:: Wait for frontend to spin up
timeout /t 5 >nul

:: 3. Open Browser
echo Opening Browser...
start http://localhost:3000

echo ===================================================
echo Agora is running!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo ===================================================
pause
