@echo off
echo Starting frontend...
start /min cmd /k "cd frontend/GlassScore && npm install && npm run dev"

echo Starting backend...
start /min cmd /k "cd backend && uvicorn main:app --port 8001"

echo Both frontend and backend are starting in separate windows.
echo local:     http://localhost:5173/