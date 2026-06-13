@echo off
echo Starting Polymarket Trading System...
echo.

:: Start API backend
echo [1/2] Starting API backend...
start "Polymarket API" cmd /c "uvicorn src.api.main:app --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak >nul

:: Start frontend
echo [2/2] Starting frontend...
cd frontend
start "Polymarket Frontend" cmd /c "npm run dev"
cd ..

echo.
echo ==========================================
echo  API:      http://localhost:8000
echo  Docs:     http://localhost:8000/docs
echo  Frontend: http://localhost:3333/dashboard
echo ==========================================
echo.
echo Close the windows or press Ctrl+C to stop.
