@echo off

echo Starting Resume Analyzer AI...

:: Start backend (Python Flask) in a new persistent command window
start "Resume Analyzer - Backend (Python)" cmd /k "python backend/server.py"

:: Start frontend (Python HTTP server) in a new persistent command window
start "Resume Analyzer - Frontend (Python)" cmd /k "python -m http.server 8000"

:: Wait for servers to start
ping -n 5 127.0.0.1 >nul

:: Open the login page in default browser
start "" http://localhost:8000/frontend/index.html

:: Inform user
echo =========================================================
echo Resume Analyzer AI is running!
echo.
echo  Frontend : http://localhost:8000/frontend/index.html
echo  Backend  : http://localhost:3000
echo.
echo  NOTE: Keep the backend and frontend windows open.
echo  Close them to stop the servers.
echo =========================================================
