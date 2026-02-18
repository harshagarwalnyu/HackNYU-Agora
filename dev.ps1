# dev.ps1 - High-Performance Agora Development Launcher
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting Agora Local Development Environment (SOTA)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Start Backend in a new window using UV
Write-Host "[1/3] Starting Backend (uv) on Port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; `$env:QDRANT_URL=':memory:'; uv run python -m app.main" -WindowStyle Normal

# Wait for backend to initialize (2 seconds is usually enough with uv)
Start-Sleep -Seconds 2

# 2. Start Frontend in a new window
Write-Host "[2/3] Starting Frontend (pnpm) on Port 3000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; pnpm dev" -WindowStyle Normal

# Wait for frontend to spin up
Start-Sleep -Seconds 3

# 3. Open Browser
Write-Host "[3/3] Opening Browser..." -ForegroundColor Green
Start-Process "http://localhost:3000"

Write-Host "===================================================" -ForegroundColor Green
Write-Host "Agora is running!" -ForegroundColor Green
Write-Host "Backend: http://localhost:8000" -ForegroundColor Gray
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Gray
Write-Host "===================================================" -ForegroundColor Green
