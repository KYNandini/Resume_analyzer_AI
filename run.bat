@echo off

echo Starting Resume Analyzer AI...

:: Start backend (Node.js) in a new command window
start "" cmd /c "node backend/server.js"

:: Start frontend (Python simple HTTP server) in a new command window
start "" cmd /c "python -m http.server 8000"

:: Wait briefly for servers to start
ping -n 3 127.0.0.1 >nul

:: Open the login page in default browser
start "" http://localhost:8000/resume-analyzer-login/index.html

:: Inform user
echo =========================================================

echo Resume Analyzer AI is running 🚀

echo  - Frontend: http://localhost:8000/resume-analyzer-login/index.html

echo  - Backend: http://localhost:3000

echo =========================================================

exit /b
