@echo off
echo ===============================================
echo Starting Polymarket Full Stack
echo ===============================================

echo.
echo [1/2] Starting FastAPI Backend...
start "Trading API" python api_server.py

timeout /t 2 /nobreak > nul

echo [2/2] Starting Next.js Frontend...
cd frontend
start "Trading Dashboard" npm run dev
cd ..

echo.
echo ===============================================
echo Services are starting...
echo Frontend: http://localhost:3000/dashboard
echo API:      http://localhost:8000
echo ===============================================
echo.
echo Press any key to stop all services...
pause > nul

taskkill /f /im node.exe 2>nul
taskkill /f /im python.exe 2>nul

echo Done!
