@echo off
echo Starting Event Echo Lite Frontend (Port 3002)...
cd frontend
python -m http.server 3002
pause

