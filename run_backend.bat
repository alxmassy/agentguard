@echo off
echo ===================================================
echo Starting AgentGuard Backend API on http://localhost:8000
echo ===================================================
cd /d "%~dp0"
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000 --reload
pause
