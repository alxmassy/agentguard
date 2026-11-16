@echo off
echo ===================================================
echo Starting AgentGuard Web Dashboard on http://localhost:3000
echo ===================================================
cd /d "%~dp0frontend"
set PATH=C:\Program Files\nodejs;%PATH%
npm.cmd run dev
pause
