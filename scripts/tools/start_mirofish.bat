@echo off
REM Start MiroFish backend server
cd /d "%~dp0mirofish\backend"
start "MiroFish Backend" /B .venv\Scripts\python.exe run.py
echo MiroFish backend starting...
timeout /t 5 /nobreak >nul
echo Checking health...
powershell -Command "try { $r = Invoke-RestMethod 'http://localhost:5001/health'; Write-Host 'MiroFish: OK ('$r.status')' } catch { Write-Host 'MiroFish: NOT READY YET' }"
echo.
echo To stop: taskkill /f /im python.exe
