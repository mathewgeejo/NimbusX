@echo off
echo ========================================
echo Will It Rain On My Parade? - Frontend Setup
echo ========================================
echo.

echo Installing dependencies...
call npm install
if errorlevel 1 (
    echo Error installing dependencies!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To start the frontend, run: npm start
echo.
echo Make sure the backend is running on port 5000!
echo ========================================
echo.
pause
