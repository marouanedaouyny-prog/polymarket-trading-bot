@echo off
echo Starting MiroFish Intelligence Engine...
docker-compose -f docker-compose.mirofish.yml up -d
echo MiroFish is starting. Check status with 'docker-compose -f docker-compose.mirofish.yml ps'
echo Bot will connect at http://localhost:5001
pause
