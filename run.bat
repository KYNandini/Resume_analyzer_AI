@echo off
echo Starting Resume Analyzer AI...

:: Start backend in a new command window
echo Launching Express Backend Server...
start "Resume Analyzer Backend" cmd /k "node backend/server.js"

:: Start frontend in a new command window
echo Launching Frontend Server...
start "Resume Analyzer Frontend" cmd /c "python -m http.server 8000"

echo Waiting for servers to start...
timeout /t 3 >nul

echo Opening browser...
start http://localhost:8000/resume-analyzer-login/index.html

echo.
echo ========================================================
echo Resume Analyzer AI is running!
echo.
echo  - Frontend: http://localhost:8000/resume-analyzer-login/index.html
echo  - Backend:  http://localhost:3000
echo ========================================================
echo.
echo To stop the servers, close the command prompt windows that popped up.
echo.
pause
