@echo off
REM Stop MiroFish backend server
taskkill /f /im python.exe >nul 2>&1
echo MiroFish backend stopped.
